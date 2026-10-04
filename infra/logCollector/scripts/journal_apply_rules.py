#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/logCollector/scripts/journal_apply_rules.py:111 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: e3a0e0c7c2deb91d73cc512ad2fddb8abeb2c67b %
#  %ccm_git_commit_id: c95decaaa02c45bee627cd315be8d2b7aefd7fc5 %
#  %ccm_git_commit_count: 111 %
#  %ccm_git_commit_date: 2025-10-29 19:12:44 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: docker updates %
#  %ccm_git_modify_date: 2025-10-29 19:12:45 %
#  %ccm_git_file_last_modified: 2025-10-29 19:12:45 %
#  %ccm_git_file_name: journal_apply_rules.py %
#  %ccm_git_path: infra/logCollector/scripts/journal_apply_rules.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 3256 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: dhcp logging % 
import os
import csv
import re
import sys

# Usage: journal_apply_rules.py <server>
if len(sys.argv) < 2:
    print("Usage: journal_apply_rules.py <server>")
    sys.exit(1)
server = sys.argv[1]
server_raw = server.split('@')[-1]
root = f"/mnt/ai_storage/logCollector/logs"
parent_dir = f"{root}/{server_raw}"
drop_dir = os.path.join(parent_dir, "drop")
pend_dir = os.path.join(parent_dir, "pend")
OUTPUT_FILE = os.path.join(drop_dir, "journal_useful.csv")
header = ["host", "timestamp", "counter", "process", "pid", "subproc", "message"]
writers = {}
output_files = {}

# Load distribution rules from JSON file
import json
with open('distribution_rules.json') as f:
    DISTRIBUTION_RULES = json.load(f)

full_journal_path = os.path.join(pend_dir, "full-journal.txt")

with open(full_journal_path, "r") as full_journal_file, open(OUTPUT_FILE, "w", newline="") as outfile:
    writers["default"] = csv.writer(outfile)
    writers["default"].writerow(header)
    output_files["default"] = outfile

    full_journal_reader = csv.reader(full_journal_file)
    header_row = next(full_journal_reader)
    for row in full_journal_reader:
        host, timestamp, counter, process_clean, pid, subproc, message = row
        action = None
        handled_by_filename = False
        for idx, rule in enumerate(DISTRIBUTION_RULES):
            proc_match = False
            if "process_regex" in rule:
                proc_match = re.match(rule["process_regex"], process_clean) is not None
            else:
                proc_match = (rule["process"] == "*" or process_clean.lower() == rule["process"].lower())
            subproc_match = False
            if "subproc_regex" in rule:
                subproc_match = re.match(rule["subproc_regex"], subproc) is not None
            else:
                subproc_match = (rule["subproc"] == "*" or subproc.lower() == rule["subproc"].lower())
            if proc_match and subproc_match:
                debug_rule_matched = rule
                action = rule["action"]
                if action == "drop":
                    break
                elif action == "filename":
                    def clean_filename(val):
                        return re.sub(r'[^A-Za-z0-9]', '', val).lower()
                    filename = rule["filename"]
                    filename = filename.replace("{root}", root)
                    filename = filename.replace("{server}", server_raw)
                    filename = filename.replace("{proc}", clean_filename(process_clean))
                    if "{subproc}" in filename:
                        filename = filename.replace("{subproc}", clean_filename(subproc))
                    if filename not in writers:
                        f = open(filename, "w", newline="")
                        writers[filename] = csv.writer(f)
                        writers[filename].writerow(header)
                        output_files[filename] = f
                    writers[filename].writerow(row)
                    handled_by_filename = True
                    break
        if not handled_by_filename:
            writers["default"].writerow(row)
    # Close additional output files
    for key, f in output_files.items():
        if key != "default":
            f.close()
