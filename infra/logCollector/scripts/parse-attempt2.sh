#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/logCollector/scripts/parse-attempt2.sh:111 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 8178ce5db3fdeb9e922f5d868cb2a77da06571fe %
#  %ccm_git_commit_id: c95decaaa02c45bee627cd315be8d2b7aefd7fc5 %
#  %ccm_git_commit_count: 111 %
#  %ccm_git_commit_date: 2025-10-29 19:12:44 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: docker updates %
#  %ccm_git_modify_date: 2025-10-29 19:12:45 %
#  %ccm_git_file_last_modified: 2025-10-29 19:12:45 %
#  %ccm_git_file_name: parse-attempt2.sh %
#  %ccm_git_path: infra/logCollector/scripts/parse-attempt2.sh %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 8372 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: dhcp logging % 
"""
Journal DHCP Log Parser (Attempt 2)

Parses journal-dhcpd.txt and stores lease assignment history in PostgreSQL.
Target file: /mnt/ai_storage/logCollector/logs/stargate.tt.omp/pend/journal-dhcpd.txt
Database: ttdb-dev1.dhcp_history schema
"""

import re
import sys
import psycopg2
from datetime import datetime
import logging
import argparse

# Database configuration
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Journal DHCP Log Parser (Attempt 2)")
    parser.add_argument('--start', type=int, default=0, help='Line number to start reading from (default: 0)')
    parser.add_argument('--limit', type=int, default=None, help='Maximum number of lines to process')
    parser.add_argument('--show', action='store_true', help='Show lines that would be inserted but do not update the database')
    parser.add_argument('--debug', action='store_true', help='Print debug info for each line processed')
    return parser.parse_args()

def main():
    args = parse_args()
    logfile = "/mnt/ai_storage/logCollector/logs/stargate.tt.omp/pend/journal-dhcpd.txt"
    start_line = args.start
    limit = args.limit
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    processed = 0
    shown = 0
    with open(logfile, 'r') as infile:
        for idx, line in enumerate(infile):
            if idx < start_line:
                continue
            if limit is not None and processed >= limit:
                break
            line = line.strip()
            if not line:
                if args.debug:
                    print(f"Line {idx}: blank/skipped")
                continue

            # Try Kea patterns first
            ts_match = re.search(KEA_PATTERNS['timestamp'], line)
            alloc_match = re.search(KEA_PATTERNS['lease_alloc'], line)
            reuse_match = re.search(KEA_PATTERNS['lease_reuse'], line)
            offer_match = re.search(KEA_PATTERNS['lease_offer'], line)
            hwaddr_match = re.search(KEA_PATTERNS['hwaddr'], line)
            clientid_match = re.search(KEA_PATTERNS['client_id'], line)
            transactionid_match = re.search(KEA_PATTERNS['transaction_id'], line)
            ip, mac, client_id, transaction_id = None, None, None, None
            timestamp = None
            event_type = None
            lease_duration = None
            if ts_match:
                timestamp = ts_match.group(1)
            if alloc_match:
                event_type = 'ALLOC'
                ip, lease_duration = alloc_match.groups()
            elif reuse_match:
                event_type = 'REUSE'
                ip, lease_duration = reuse_match.groups()
            elif offer_match:
                event_type = 'OFFER'
                ip = offer_match.group(1)
            if hwaddr_match:
                mac = hwaddr_match.group(1)
            if clientid_match:
                client_id = clientid_match.group(1)
            if transactionid_match:
                transaction_id = transactionid_match.group(1)

            # If no Kea event matched, try ISC patterns
            if not event_type:
                isc_ts_match = re.search(ISC_PATTERNS['timestamp'], line)
                isc_offer = re.search(ISC_PATTERNS['offer'], line)
                isc_ack = re.search(ISC_PATTERNS['ack'], line)
                isc_nak = re.search(ISC_PATTERNS['nak'], line)
                isc_release = re.search(ISC_PATTERNS['release'], line)
                isc_discover = re.search(ISC_PATTERNS['discover'], line)
                isc_request = re.search(ISC_PATTERNS['request'], line)
                ip, mac, hostname = None, None, None
                timestamp = None
                event_type = None
                lease_duration = None
                # Try regex timestamp first
                if isc_ts_match:
                    timestamp = isc_ts_match.group(1)
                # If not found, try extracting from CSV field
                else:
                    fields = line.split(',')
                    if len(fields) > 1:
                        timestamp = fields[1]
                if isc_offer:
                    event_type = 'OFFER'
                    ip, mac = isc_offer.groups()
                elif isc_ack:
                    event_type = 'ACK'
                    ip, mac, hostname = isc_ack.groups()
                elif isc_nak:
                    event_type = 'NAK'
                    ip, mac = isc_nak.groups()
                elif isc_release:
                    event_type = 'RELEASE'
                    ip, mac = isc_release.groups()
                elif isc_discover:
                    event_type = 'DISCOVER'
                    mac, hostname = isc_discover.groups()
                elif isc_request:
                    event_type = 'REQUEST'
                    ip, mac, hostname = isc_request.groups()
            if args.debug:
                print(f"Line {idx}: event_type={event_type}, ip={ip}, timestamp={timestamp}, mac={mac}, client_id={client_id}, transaction_id={transaction_id}, lease_duration={lease_duration}")
            if not event_type or not ip or not timestamp:
                if args.debug:
                    print(f"Line {idx}: No event_type/ip/timestamp found, skipping.")
                continue
            # Deduplication: check DB for existing event
            cursor.execute(
                "SELECT 1 FROM dhcp_history.lease_events WHERE timestamp=%s AND ip_address=%s AND mac_address=%s AND event_type=%s",
                (timestamp, ip, mac, event_type)
            )
            if cursor.fetchone():
                if args.debug:
                    print(f"Line {idx}: Duplicate found in DB, skipping.")
                continue
            # Extract host for ISC DHCP format
            host = 'stargate.tt.omp'
            fields = line.split(',')
            if len(fields) > 0 and fields[0]:
                host = fields[0]
            if args.show:
                print(f"Would insert: {timestamp} {event_type} {ip} {mac} {client_id} {transaction_id} {lease_duration} host={host}")
                shown += 1
            else:
                # Insert into DB
                cursor.execute(
                    "INSERT INTO dhcp_history.lease_events (dhcp_server_host, timestamp, event_type, ip_address, mac_address, client_id, transaction_id, lease_duration, dhcp_server_type, raw_log_line) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (host, timestamp, event_type, ip, mac, client_id, transaction_id, int(lease_duration) if lease_duration else None, 'kea', line)
                )
            processed += 1
    if not args.show:
        conn.commit()
    cursor.close()
    conn.close()
    if args.show:
        print(f"Show mode: {shown} entries would be inserted from {logfile}.")
    else:
        print(f"Parsed {processed} entries from {logfile} and loaded to DB.")

if __name__ == "__main__":
    main()
