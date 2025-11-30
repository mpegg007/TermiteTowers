#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dhcp/scripts/monitoring/parse-kea-logs.py:121 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 2f8a7f37cfafd10f6aed3e087e21ef928c6defc6 %
#  %ccm_git_commit_id: 4a1cbe1072eb42723822f202e3fcd45247e1aa03 %
#  %ccm_git_commit_count: 121 %
#  %ccm_git_commit_date: 2025-11-30 12:26:01 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2025-11-30 12:26:12 %
#  %ccm_git_file_last_modified: 2025-11-30 12:26:12 %
#  %ccm_git_file_name: parse-kea-logs.py %
#  %ccm_git_path: infra/dhcp/scripts/monitoring/parse-kea-logs.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 27752 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: november changes % 
# %git_commit_history: dhcp logging % 
#  tt-secrets.skip
"""
Kea DHCP Log Parser and Historical Data Collector

Parses Kea DHCP log files and stores lease assignment history in PostgreSQL.
Provides historical tracking that Kea's native lease tables don't maintain.

Logs parsed:
- /var/log/kea/kea-dhcp4.log
- /var/log/kea/kea-dhcp4.log.* (rotated logs)

Database: ttdb-dev1.dhcp_history schema
"""

import re
import sys
import psycopg2
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
import argparse
import logging

# Configuration
LOG_PATHS = [
    "/var/log/kea/kea-dhcp4.log",
    "/var/log/kea/kea-dhcp4.log.1",
]

# Additional log files for batch import
SYSLOG_PATHS = [
    "/home/mpegg-adm/source/TermiteTowers/infra/dhcp/inventory/dhcp.syslog",      # ISC DHCP from ttdi3
    "/home/mpegg-adm/source/TermiteTowers/infra/dhcp/inventory/dhcp.syslog.mono", # Kea syslog from monolith
]

DB_CONFIG = {
    "host": "localhost",
    "database": "ttdb_dev1",
    "user": "dhcp_history",
    "password": "termitetowers-db"
}

# Regex patterns for Kea log parsing
KEA_PATTERNS = {
    'timestamp': r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)',
    'lease_alloc': r'DHCP4_LEASE_ALLOC.*lease ([\d.]+) has been allocated for (\d+) seconds',
    'lease_reuse': r'DHCP4_LEASE_REUSE.*lease ([\d.]+) has been reused for (\d+) seconds',
    'lease_offer': r'DHCP4_LEASE_OFFER.*lease ([\d.]+) will be offered',
    'hwaddr': r'\[hwtype=\d+ ([\da-f:]+)\]',
    'client_id': r'cid=\[([\da-f:]+)\]',
    'transaction_id': r'tid=(0x[\da-f]+)',
}

# Regex patterns for ISC DHCP syslog parsing
ISC_PATTERNS = {
    'timestamp': r'^syslog[.\d]*:(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[+-]\d{2}:\d{2})',
    'hostname': r'^syslog[.\d]*:\d{4}-\d{2}-\d{2}T[\d:.+-]+ (\S+) dhcpd',
    'discover': r'DHCPDISCOVER from ([\da-f:]+)(?:\s+\(([^)]+)\))? via',
    'offer': r'DHCPOFFER on ([\d.]+) to ([\da-f:]+)',
    'request': r'DHCPREQUEST for ([\d.]+).*from ([\da-f:]+)(?:\s+\(([^)]+)\))?',
    'ack': r'DHCPACK on ([\d.]+) to ([\da-f:]+)(?:\s+\(([^)]+)\))?',
    'nak': r'DHCPNAK on ([\d.]+) to ([\da-f:]+)',
    'release': r'DHCPRELEASE of ([\d.]+) from ([\da-f:]+)',
}

# Regex patterns for Kea syslog format (from monolith syslog)
KEA_SYSLOG_PATTERNS = {
    'timestamp': r'^syslog[.\d]*:(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[+-]\d{2}:\d{2})',
    'hostname': r'^syslog[.\d]*:\d{4}-\d{2}-\d{2}T[\d:.+-]+ (\S+) kea-dhcp4',
    'kea_timestamp': r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)',
    'lease_alloc': r'DHCP4_LEASE_ALLOC.*lease ([\d.]+) has been allocated for (\d+) seconds',
    'lease_reuse': r'DHCP4_LEASE_REUSE.*lease ([\d.]+) has been reused for (\d+) seconds',
    'lease_offer': r'DHCP4_LEASE_OFFER.*lease ([\d.]+) will be offered',
    'hwaddr': r'\[hwtype=\d+ ([\da-f:]+)\]',
    'client_id': r'cid=\[([\da-f:]+)\]',
    'transaction_id': r'tid=(0x[\da-f]+)',
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

 
class KeaLogParser:
    """Parse Kea DHCP logs and extract lease information"""
    
    def __init__(self, server_host='monolith'):
        self.patterns = {k: re.compile(v) for k, v in KEA_PATTERNS.items()}
        self.server_host = server_host
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """Parse a single log line and extract lease event data"""
        
        # Extract timestamp
        ts_match = self.patterns['timestamp'].search(line)
        if not ts_match:
            return None
        
        timestamp = datetime.strptime(ts_match.group(1), '%Y-%m-%d %H:%M:%S.%f')
        
        # Determine event type
        event_type = None
        ip_address = None
        duration = None
        
        if 'DHCP4_LEASE_ALLOC' in line:
            event_type = 'ALLOC'
            match = self.patterns['lease_alloc'].search(line)
            if match:
                ip_address, duration = match.groups()
        
        elif 'DHCP4_LEASE_REUSE' in line:
            event_type = 'REUSE'
            match = self.patterns['lease_reuse'].search(line)
            if match:
                ip_address, duration = match.groups()
        
        elif 'DHCP4_LEASE_OFFER' in line:
            event_type = 'OFFER'
            match = self.patterns['lease_offer'].search(line)
            if match:
                ip_address = match.group(1)
        
        if not event_type or not ip_address:
            return None
        
        # Extract hardware address
        hw_match = self.patterns['hwaddr'].search(line)
        hwaddr = hw_match.group(1) if hw_match else None
        
        # Extract client ID
        cid_match = self.patterns['client_id'].search(line)
        client_id = cid_match.group(1) if cid_match else None
        
        # Extract transaction ID
        tid_match = self.patterns['transaction_id'].search(line)
        transaction_id = tid_match.group(1) if tid_match else None
        
        return {
            'dhcp_server_host': self.server_host,
            'dhcp_server_type': 'kea',
            'timestamp': timestamp,
            'event_type': event_type,
            'ip_address': ip_address,
            'mac_address': hwaddr,
            'client_id': client_id,
            'transaction_id': transaction_id,
            'lease_duration': int(duration) if duration else None,
            'raw_log_line': line.strip()
        }
    
    def parse_file(self, filepath: str, last_position: int = 0) -> tuple[List[Dict], int]:
        """
        Parse log file from last known position
        Returns: (parsed_events, new_file_position)
        """
        events = []
        
        try:
            with open(filepath, 'r') as f:
                # Seek to last position
                f.seek(last_position)
                
                for line in f:
                    event = self.parse_line(line)
                    if event:
                        events.append(event)
                
                # Record new position
                new_position = f.tell()
            
            return events, new_position
        
        except FileNotFoundError:
            logger.warning(f"Log file not found: {filepath}")
            return [], 0
        except PermissionError:
            logger.error(f"Permission denied reading: {filepath}")
            return [], 0


class ISCDHCPLogParser:
    """Parse ISC DHCP syslog and extract lease information"""
    
    def __init__(self):
        self.patterns = {k: re.compile(v) for k, v in ISC_PATTERNS.items()}
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """Parse a single syslog line and extract DHCP event data"""
        
        # Extract timestamp
        ts_match = self.patterns['timestamp'].search(line)
        if not ts_match:
            return None
        
        timestamp_str = ts_match.group(1)
        # Parse ISO 8601 timestamp with timezone
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        
        # Extract server hostname
        host_match = self.patterns['hostname'].search(line)
        server_host = host_match.group(1) if host_match else 'unknown'
        
        # Determine event type and extract data
        event_type = None
        ip_address = None
        mac_address = None
        hostname = None
        
        if 'DHCPDISCOVER' in line:
            event_type = 'DISCOVER'
            match = self.patterns['discover'].search(line)
            if match:
                mac_address = match.group(1)
                hostname = match.group(2) if match.lastindex >= 2 else None
        
        elif 'DHCPOFFER' in line:
            event_type = 'OFFER'
            match = self.patterns['offer'].search(line)
            if match:
                ip_address, mac_address = match.groups()
        
        elif 'DHCPREQUEST' in line:
            event_type = 'REQUEST'
            match = self.patterns['request'].search(line)
            if match:
                ip_address = match.group(1)
                mac_address = match.group(2)
                hostname = match.group(3) if match.lastindex >= 3 else None
        
        elif 'DHCPACK' in line:
            event_type = 'ACK'
            match = self.patterns['ack'].search(line)
            if match:
                ip_address = match.group(1)
                mac_address = match.group(2)
                hostname = match.group(3) if match.lastindex >= 3 else None
        
        elif 'DHCPNAK' in line:
            event_type = 'NAK'
            match = self.patterns['nak'].search(line)
            if match:
                ip_address, mac_address = match.groups()
        
        elif 'DHCPRELEASE' in line:
            event_type = 'RELEASE'
            match = self.patterns['release'].search(line)
            if match:
                ip_address, mac_address = match.groups()
        
        if not event_type or not mac_address:
            return None
        
        return {
            'dhcp_server_host': server_host,
            'dhcp_server_type': 'isc-dhcp',
            'timestamp': timestamp,
            'event_type': event_type,
            'ip_address': ip_address,
            'mac_address': mac_address,
            'hostname': hostname,
            'client_id': None,
            'transaction_id': None,
            'lease_duration': None,
            'raw_log_line': line.strip()
        }
    
    def parse_file(self, filepath: str, last_position: int = 0) -> tuple[List[Dict], int]:
        """
        Parse log file from last known position
        Returns: (parsed_events, new_file_position)
        """
        events = []
        
        try:
            with open(filepath, 'r') as f:
                # Seek to last position
                f.seek(last_position)
                
                for line in f:
                    event = self.parse_line(line)
                    if event:
                        events.append(event)
                
                # Record new position
                new_position = f.tell()
            
            return events, new_position
        
        except FileNotFoundError:
            logger.warning(f"Log file not found: {filepath}")
            return [], 0
        except PermissionError:
            logger.error(f"Permission denied reading: {filepath}")
            return [], 0


class KeaSyslogParser:
    """Parse Kea DHCP messages from syslog format (monolith syslog)"""
    
    def __init__(self):
        self.patterns = {k: re.compile(v) for k, v in KEA_SYSLOG_PATTERNS.items()}
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """Parse a syslog line containing Kea DHCP event"""
        
        # Skip non-Kea lines
        if 'kea-dhcp4' not in line:
            return None
        
        # Extract syslog timestamp
        ts_match = self.patterns['timestamp'].search(line)
        if not ts_match:
            return None
        
        timestamp_str = ts_match.group(1)
        # Parse ISO 8601 timestamp with timezone
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        
        # Extract server hostname
        host_match = self.patterns['hostname'].search(line)
        server_host = host_match.group(1) if host_match else 'unknown'
        
        # Try to use Kea's internal timestamp if available (more precise)
        kea_ts_match = self.patterns['kea_timestamp'].search(line)
        if kea_ts_match:
            try:
                timestamp = datetime.strptime(kea_ts_match.group(1), '%Y-%m-%d %H:%M:%S.%f')
            except:
                pass  # Use syslog timestamp if parsing fails
        
        # Determine event type
        event_type = None
        ip_address = None
        duration = None
        
        if 'DHCP4_LEASE_ALLOC' in line:
            event_type = 'ALLOC'
            match = self.patterns['lease_alloc'].search(line)
            if match:
                ip_address, duration = match.groups()
        
        elif 'DHCP4_LEASE_REUSE' in line:
            event_type = 'REUSE'
            match = self.patterns['lease_reuse'].search(line)
            if match:
                ip_address, duration = match.groups()
        
        elif 'DHCP4_LEASE_OFFER' in line:
            event_type = 'OFFER'
            match = self.patterns['lease_offer'].search(line)
            if match:
                ip_address = match.group(1)
        
        if not event_type or not ip_address:
            return None
        
        # Extract hardware address
        hw_match = self.patterns['hwaddr'].search(line)
        hwaddr = hw_match.group(1) if hw_match else None
        
        # Extract client ID
        cid_match = self.patterns['client_id'].search(line)
        client_id = cid_match.group(1) if cid_match else None
        
        # Extract transaction ID
        tid_match = self.patterns['transaction_id'].search(line)
        transaction_id = tid_match.group(1) if tid_match else None
        
        return {
            'dhcp_server_host': server_host,
            'dhcp_server_type': 'kea',
            'timestamp': timestamp,
            'event_type': event_type,
            'ip_address': ip_address,
            'mac_address': hwaddr,
            'client_id': client_id,
            'transaction_id': transaction_id,
            'lease_duration': int(duration) if duration else None,
            'raw_log_line': line.strip()
        }
    
    def parse_file(self, filepath: str, last_position: int = 0) -> tuple[List[Dict], int]:
        """
        Parse syslog file from last known position
        Returns: (parsed_events, new_file_position)
        """
        events = []
        
        try:
            with open(filepath, 'r') as f:
                # Seek to last position
                f.seek(last_position)
                
                for line in f:
                    event = self.parse_line(line)
                    if event:
                        events.append(event)
                
                # Record new position
                new_position = f.tell()
            
            return events, new_position
        
        except FileNotFoundError:
            logger.warning(f"Log file not found: {filepath}")
            return [], 0
        except PermissionError:
            logger.error(f"Permission denied reading: {filepath}")
            return [], 0


class DHCPHistoryDB:
    """Manage DHCP history database"""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info(f"Connected to database: {self.db_config['database']}")
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def init_schema(self):
        """Create schema and tables if they don't exist"""
        schema_sql = """
        -- Create schema for DHCP history
        CREATE SCHEMA IF NOT EXISTS dhcp_history;
        
        -- Lease events table (historical record)
        CREATE TABLE IF NOT EXISTS dhcp_history.lease_events (
            event_id BIGSERIAL PRIMARY KEY,
            dhcp_server_host VARCHAR(255) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            event_type VARCHAR(20) NOT NULL,
            ip_address INET,
            mac_address MACADDR,
            client_id VARCHAR(255),
            transaction_id VARCHAR(50),
            hostname VARCHAR(255),
            lease_duration INTEGER,
            dhcp_server_type VARCHAR(20) DEFAULT 'kea',
            raw_log_line TEXT,
            processed_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT valid_event_type CHECK (event_type IN ('DISCOVER', 'OFFER', 'REQUEST', 'ACK', 'NAK', 'RELEASE', 'DECLINE', 'INFORM', 'ALLOC', 'REUSE', 'EXPIRE')),
            -- Composite unique constraint to prevent duplicates across log rotations
            CONSTRAINT unique_dhcp_event UNIQUE (dhcp_server_host, timestamp, mac_address, ip_address, event_type)
        );
        
        -- Create indexes for common queries
        CREATE INDEX IF NOT EXISTS idx_lease_events_timestamp 
            ON dhcp_history.lease_events(timestamp DESC);
        
        CREATE INDEX IF NOT EXISTS idx_lease_events_ip 
            ON dhcp_history.lease_events(ip_address);
        
        CREATE INDEX IF NOT EXISTS idx_lease_events_mac 
            ON dhcp_history.lease_events(mac_address);
        
        CREATE INDEX IF NOT EXISTS idx_lease_events_type 
            ON dhcp_history.lease_events(event_type);
        
        CREATE INDEX IF NOT EXISTS idx_lease_events_server 
            ON dhcp_history.lease_events(dhcp_server_host);
        
        CREATE INDEX IF NOT EXISTS idx_lease_events_server_type 
            ON dhcp_history.lease_events(dhcp_server_type);
        
        -- Device assignment summary (current state + history count)
        CREATE TABLE IF NOT EXISTS dhcp_history.device_summary (
            mac_address MACADDR PRIMARY KEY,
            current_ip INET,
            last_seen TIMESTAMP,
            first_seen TIMESTAMP,
            total_assignments INTEGER DEFAULT 0,
            hostnames TEXT[],
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        -- Log file tracking (resume from last position)
        CREATE TABLE IF NOT EXISTS dhcp_history.log_file_state (
            log_file_path VARCHAR(500) PRIMARY KEY,
            last_position BIGINT DEFAULT 0,
            last_parsed TIMESTAMP,
            total_events_parsed BIGINT DEFAULT 0
        );
        
        -- Helper view: Recent assignments
        CREATE OR REPLACE VIEW dhcp_history.recent_assignments AS
        SELECT 
            dhcp_server_host,
            dhcp_server_type,
            timestamp,
            event_type,
            ip_address,
            mac_address,
            hostname,
            client_id,
            lease_duration
        FROM dhcp_history.lease_events
        WHERE event_type IN ('ALLOC', 'REUSE', 'ACK')
        ORDER BY timestamp DESC
        LIMIT 1000;
        
        -- Helper view: Active devices summary
        CREATE OR REPLACE VIEW dhcp_history.active_devices AS
        SELECT 
            mac_address,
            current_ip,
            last_seen,
            first_seen,
            total_assignments,
            EXTRACT(EPOCH FROM (NOW() - last_seen)) / 3600 AS hours_since_seen
        FROM dhcp_history.device_summary
        WHERE last_seen > NOW() - INTERVAL '7 days'
        ORDER BY last_seen DESC;
        """
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(schema_sql)
                self.conn.commit()
                logger.info("Schema initialized successfully")
        except psycopg2.Error as e:
            logger.error(f"Schema initialization failed: {e}")
            self.conn.rollback()
            raise
    
    def get_last_position(self, log_file: str) -> int:
        """Get last parsed position for log file"""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT last_position FROM dhcp_history.log_file_state WHERE log_file_path = %s",
                (log_file,)
            )
            result = cur.fetchone()
            return result[0] if result else 0
    
    def update_log_position(self, log_file: str, position: int, events_count: int):
        """Update log file parsing state"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO dhcp_history.log_file_state 
                    (log_file_path, last_position, last_parsed, total_events_parsed)
                VALUES (%s, %s, NOW(), %s)
                ON CONFLICT (log_file_path) DO UPDATE SET
                    last_position = EXCLUDED.last_position,
                    last_parsed = EXCLUDED.last_parsed,
                    total_events_parsed = dhcp_history.log_file_state.total_events_parsed + EXCLUDED.total_events_parsed
            """, (log_file, position, events_count))
            self.conn.commit()
    
    def insert_events(self, events: List[Dict]):
        """Batch insert lease events"""
        if not events:
            return 0
        
        insert_sql = """
            INSERT INTO dhcp_history.lease_events 
                (dhcp_server_host, timestamp, event_type, ip_address, mac_address, 
                 client_id, transaction_id, hostname, lease_duration, dhcp_server_type, raw_log_line)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (dhcp_server_host, timestamp, mac_address, ip_address, event_type) 
            DO NOTHING
        """
        
        try:
            with self.conn.cursor() as cur:
                # Batch insert events
                inserted_count = 0
                for event in events:
                    cur.execute(insert_sql, (
                        event.get('dhcp_server_host', 'unknown'),
                        event['timestamp'],
                        event['event_type'],
                        event['ip_address'],
                        event['mac_address'],
                        event.get('client_id'),
                        event.get('transaction_id'),
                        event.get('hostname'),
                        event.get('lease_duration'),
                        event.get('dhcp_server_type', 'kea'),
                        event['raw_log_line']
                    ))
                    if cur.rowcount > 0:
                        inserted_count += 1
                
                # Update device summary for assignment events
                for event in events:
                    if event['event_type'] in ('ALLOC', 'REUSE', 'ACK') and event.get('mac_address'):
                        cur.execute("""
                            INSERT INTO dhcp_history.device_summary 
                                (mac_address, current_ip, last_seen, first_seen, total_assignments)
                            VALUES (%s, %s, %s, %s, 1)
                            ON CONFLICT (mac_address) DO UPDATE SET
                                current_ip = EXCLUDED.current_ip,
                                last_seen = EXCLUDED.last_seen,
                                total_assignments = dhcp_history.device_summary.total_assignments + 1,
                                updated_at = NOW()
                        """, (
                            event['mac_address'],
                            event['ip_address'],
                            event['timestamp'],
                            event['timestamp']
                        ))
                
                self.conn.commit()
                logger.info(f"Inserted {inserted_count} new events ({len(events) - inserted_count} duplicates skipped)")
                return inserted_count
        
        except psycopg2.Error as e:
            logger.error(f"Failed to insert events: {e}")
            self.conn.rollback()
            return 0
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


def main():
    parser = argparse.ArgumentParser(
        description='Parse Kea/ISC DHCP logs and store historical data'
    )
    parser.add_argument(
        '--init-schema',
        action='store_true',
        help='Initialize database schema and exit'
    )
    parser.add_argument(
        '--full-parse',
        action='store_true',
        help='Parse entire log files (ignore last position)'
    )
    parser.add_argument(
        '--log-files',
        nargs='+',
        default=LOG_PATHS,
        help='Log files to parse'
    )
    parser.add_argument(
        '--log-type',
        choices=['kea', 'isc', 'kea-syslog', 'auto'],
        default='auto',
        help='DHCP server type: kea (pure Kea logs), isc (ISC DHCP syslog), kea-syslog (Kea from syslog), auto (detect)'
    )
    parser.add_argument(
        '--server-host',
        default='monolith',
        help='DHCP server hostname (for Kea logs)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse logs but do not insert into database'
    )
    
    args = parser.parse_args()
    # Always parse full logs by default unless overridden
    args.full_parse = True
    
    # Auto-detect parser type based on filename or content
    def detect_parser_type(filepath: str) -> str:
        """Auto-detect log format"""
        if 'syslog' in filepath.lower():
            # Check if it's ISC DHCP or Kea in syslog
            try:
                with open(filepath, 'r') as f:
                    first_lines = ''.join([f.readline() for _ in range(10)])
                    if 'kea-dhcp4' in first_lines:
                        return 'kea-syslog'
                    elif 'dhcpd' in first_lines:
                        return 'isc'
            except:
                pass
            return 'isc'  # Default for syslog
        return 'kea'  # Default for regular logs
    
    # Initialize parser based on type
    def get_parser(log_type: str, filepath: str = None):
        """Get appropriate parser for log type"""
        if log_type == 'auto' and filepath:
            log_type = detect_parser_type(filepath)
        
        if log_type == 'kea':
            return KeaLogParser(server_host=args.server_host)
        elif log_type == 'isc':
            return ISCDHCPLogParser()
        elif log_type == 'kea-syslog':
            return KeaSyslogParser()
        else:
            return KeaLogParser(server_host=args.server_host)
    
    db = DHCPHistoryDB(DB_CONFIG)
    
    try:
        db.connect()
        
        # Initialize schema if requested
        if args.init_schema:
            logger.info("Initializing database schema...")
            db.init_schema()
            logger.info("Schema initialization complete")
            return 0
        
        # Parse log files
        total_events = 0
        
        for log_file in args.log_files:
            logger.info(f"Processing: {log_file}")
            
            # Get appropriate parser for this file
            parser_obj = get_parser(args.log_type, log_file)
            
            # Get last position (or 0 if full parse)
            last_pos = 0 if args.full_parse else db.get_last_position(log_file)
            logger.info(f"Starting from position: {last_pos}")
            
            # Parse file
            events, new_pos = parser_obj.parse_file(log_file, last_pos)
            logger.info(f"Parsed {len(events)} events from {log_file}")
            
            # Insert events
            if not args.dry_run and events:
                inserted = db.insert_events(events)
                db.update_log_position(log_file, new_pos, inserted)
                total_events += inserted
            elif args.dry_run:
                logger.info(f"DRY RUN: Would insert {len(events)} events")
                for event in events[:5]:  # Show first 5
                    logger.info(f"  {event['timestamp']} - {event['event_type']} - "
                              f"{event['ip_address']} - {event['mac_address']}")
        
        logger.info(f"Total events processed: {total_events}")
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    finally:
        db.close()


if __name__ == '__main__':
    sys.exit(main())
