#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/logCollector/scripts/journal_parse_to_temp.py:110 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 01cf79210cb802acf880460a1615b95389e010e0 %
#  %ccm_git_commit_id: f58291ad575edfb9a551f895005def9b9f831304 %
#  %ccm_git_commit_count: 110 %
#  %ccm_git_commit_date: 2025-10-25 14:11:42 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: dhcp logging %
#  %ccm_git_modify_date: 2025-10-25 14:11:42 %
#  %ccm_git_file_last_modified: 2025-10-25 10:55:54 %
#  %ccm_git_file_name: journal_parse_to_temp.py %
#  %ccm_git_path: infra/logCollector/scripts/journal_parse_to_temp.py %
#  %ccm_git_language_mode: nginx %
#  %ccm_git_file_type: text/plain %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 4154 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
import os
import csv
import re
import sys

# Usage: journal_parse_to_temp.py <server>
if len(sys.argv) < 2:
    print("Usage: journal_parse_to_temp.py <server>")
    sys.exit(1)
server = sys.argv[1]
server_raw = server.split('@')[-1]
parent_dir = f"/mnt/ai_storage/logCollector/logs/{server_raw}"
drop_dir = os.path.join(parent_dir, "drop")
pend_dir = os.path.join(parent_dir, "pend")
INPUT_FILE = os.path.join(drop_dir, "journal.log")
header = ["host", "timestamp", "counter", "process", "pid", "subproc", "message"]
full_journal_path = os.path.join(pend_dir, "full-journal.txt")
line_count = 0
last_timestamp = None
counter = 0
with open(INPUT_FILE, "r") as infile, open(full_journal_path, "w", newline="") as full_journal_file:
    full_journal_writer = csv.writer(full_journal_file)
    full_journal_writer.writerow(header)
    line_count = 0
    for line in infile:
        line_count += 1
        if line_count > 999999999:
            break
        # Debug: Only print for first 4 lines
        debug_this_line = line_count <= 4
        line = line.strip()
        if not line:
            continue
        # Step 1: Extract fields
        if ':' not in line:
            continue
        # Only syslog-style parsing: date host process: message
        # Example: 2025-07-17T22:47:59+00:00 ttdi3-u24-s2501 kernel: vgaarb: loaded
        tokens = line.split()
        tokens = line.split()
        if len(tokens) < 3:
            continue
        timestamp = tokens[0]
        # Only process lines where first token is a valid datetime
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2}$", timestamp):
            continue
        host = tokens[1]
        process_token = tokens[2]
        process = process_token.rstrip(":")
        pid = ''
        # Find first colon after process
        process_end = line.find(process_token) + len(process_token)
        # Write everything after process as message, do not extract subproc
        message = line[process_end:].strip()
        # Simple subproc extraction: up to first colon in message
        subproc = ''
        first_colon_in_msg = message.find(":")
        if first_colon_in_msg != -1:
            subproc = message[:first_colon_in_msg].strip()
        # Blank out subproc if longer than 21 bytes or contains invalid characters
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.- ")
        if len(subproc.encode('utf-8')) > 21 or any(c not in allowed_chars for c in subproc):
            subproc = ''
        # Blank out if not starting with alpha
        elif not subproc or not subproc[0].isalpha():
            subproc = ''
        else:
            # Convert to lowercase
            subproc = subproc.lower()
            # Trim to first blank if still not blank
            first_space = subproc.find(' ')
            if first_space != -1:
                subproc = subproc[:first_space]
        process_clean = process.strip()
        if '][' in process_clean:
            proc_part, pid_part = process_clean.split('][')
            process_clean = proc_part
            pid_match = re.match(r"\[(\d+)\]$", pid_part)
            if pid_match:
                pid = pid_match.group(1)
        elif re.match(r"^.*\[\d+\]$", process_clean):
            pid_match = re.match(r"^(.*)\[(\d+)\]$", process_clean)
            if pid_match:
                process_clean = pid_match.group(1)
                pid = pid_match.group(2)
        process_clean = process_clean.strip()
        process_clean = process_clean.lower()
        # Remove parentheses if process_clean is wrapped with ()
        if process_clean.startswith('(') and process_clean.endswith(')'):
            process_clean = process_clean[1:-1]
    # Only use the custom subproc extraction logic above
        # Only use the custom subproc extraction logic above
        # Step 5: Counter logic
        if timestamp != last_timestamp:
            counter = 1
            last_timestamp = timestamp
        else:
            counter += 1
        row = [host, timestamp, counter, process_clean, pid, subproc, message]
        full_journal_writer.writerow(row)
