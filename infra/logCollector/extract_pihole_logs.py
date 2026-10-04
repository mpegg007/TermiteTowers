#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/logCollector/extract_pihole_logs.py:139 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 6436eb7ecd47e06f41441ccf834af8b9f86b9b97 %
#  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
#  %ccm_git_commit_count: 139 %
#  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: march updates %
#  %ccm_git_modify_date: 2026-03-22 09:03:21 %
#  %ccm_git_file_last_modified: 2026-03-22 09:03:21 %
#  %ccm_git_file_name: extract_pihole_logs.py %
#  %ccm_git_path: infra/logCollector/extract_pihole_logs.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 4199 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: unknown  unknown  unknown  % 
import sqlite3
import csv
import datetime
import os

# Configuration
DB_PATH = '/mnt/ai_storage/pihole/config/pihole-FTL.db'
OUTPUT_FILE = 'pihole_query_logs.csv'

# Pi-hole Query Status Codes (for readability)
# Ref: https://docs.pi-hole.net/database/ftl/#query-types
STATUS_MAP = {
    0: "Unknown",
    1: "Blocked (Gravity)",
    2: "Forwarded",
    3: "Cached",
    4: "Blocked (Regex)",
    5: "Blocked (Blacklist)",
    6: "Blocked (External)",
    7: "Blocked (Gravity + CNAME)",
    8: "Blocked (Regex + CNAME)",
    9: "Blocked (Blacklist + CNAME)",
    10: "Blocked (External + CNAME)",
    11: "Blocked (Gravity + IP)",
    12: "Blocked (Regex + IP)",
    13: "Blocked (Blacklist + IP)",
    14: "Blocked (External + IP)",
}

# DNS Query Types (Common ones)
# Ref: https://en.wikipedia.org/wiki/List_of_DNS_record_types
QUERY_TYPE_MAP = {
    1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 12: "PTR", 15: "MX",
    16: "TXT", 28: "AAAA", 33: "SRV", 41: "OPT", 46: "RRSIG",
    47: "NSEC", 48: "DNSKEY", 50: "NSEC3", 51: "NSEC3PARAM", 
    65: "HTTPS", 255: "ANY"
}

# Reply Types
REPLY_TYPE_MAP = {
    0: "Unknown/None", 1: "NODATA", 2: "NXDOMAIN", 3: "CNAME", 
    4: "IP", 5: "DOMAIN", 6: "RRNAME", 7: "SERVFAIL", 
    8: "REFUSED", 9: "NOTIMP", 10: "OTHER", 11: "DNSSEC", 12: "NONE", 13: "BLOB"
}

def main():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    print(f"Connecting to database: {DB_PATH}")
    
    try:
        # Connect in read-only mode to prevent locking issues
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        
        # FIX: Handle invalid UTF-8 characters in domain names gracefully
        # This replaces bytes that fail to decode with a replacement character (?)
        conn.text_factory = lambda b: b.decode(errors="replace")
        
        cursor = conn.cursor()

        # Query relevant data
        query = """
        SELECT 
            id,
            timestamp,
            type,
            status,
            domain,
            client,
            forward,
            additional_info,
            reply_type,
            reply_time,
            dnssec,
            list_id
        FROM queries 
        ORDER BY timestamp DESC
        """
        
        print("Executing query... (this might take a moment if the DB is huge)")
        cursor.execute(query)
        
        rows = cursor.fetchall()
        print(f"Retrieved {len(rows)} records.")
        
        print(f"Writing to {OUTPUT_FILE}...")
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            
            # Header
            csv_writer.writerow([
                'ID', 'Timestamp', 'Time (Readable)', 'Query Type', 'Status', 
                'Domain', 'Client IP', 'Upstream Server', 'Additional Info', 
                'Reply Type', 'Reply Time (ms)', 'DNSSEC Status', 'Blocklist ID'
            ])
            
            for row in rows:
                (rec_id, ts, q_type, status, domain, client, forward, 
                 add_info, r_type, r_time, dnssec, list_id) = row
                
                # Convert data for readability
                time_readable = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                status_text = STATUS_MAP.get(status, f"Unknown ({status})")
                query_type_text = QUERY_TYPE_MAP.get(q_type, f"TYPE{q_type}")
                reply_type_text = REPLY_TYPE_MAP.get(r_type, str(r_type))
                
                # Convert seconds to milliseconds
                reply_time_ms = r_time * 1000 if r_time is not None else 0.0
                
                csv_writer.writerow([
                    rec_id, ts, time_readable, query_type_text, status_text, 
                    domain, client, forward, add_info, 
                    reply_type_text, f"{reply_time_ms:.4f}", dnssec, list_id
                ])

        print("Done! Data export complete.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
