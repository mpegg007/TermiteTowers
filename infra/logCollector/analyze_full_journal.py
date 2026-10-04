#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/logCollector/analyze_full_journal.py:139 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: d46f0e2cd7b7b24bf31af196b4496a1e5a760d9d %
#  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
#  %ccm_git_commit_count: 139 %
#  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: march updates %
#  %ccm_git_modify_date: 2026-03-22 09:03:21 %
#  %ccm_git_file_last_modified: 2026-03-22 09:03:21 %
#  %ccm_git_file_name: analyze_full_journal.py %
#  %ccm_git_path: infra/logCollector/analyze_full_journal.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1384 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: unknown  unknown  unknown  % 
total_rows = 0
import os, csv, sys
from collections import defaultdict
if len(sys.argv) < 2:
    sys.exit(1)
server = sys.argv[1]
server_raw = server.split('@')[-1]
parent_dir = f"/mnt/ai_storage/logCollector/logs/{server_raw}"
pend_dir = os.path.join(parent_dir, "pend")
full_journal_path = os.path.join(pend_dir, "full-journal.txt")
process_counts = defaultdict(int)
subproc_counts = defaultdict(lambda: defaultdict(int))
total_rows = 0
with open(full_journal_path, "r") as infile:
    reader = csv.DictReader(infile)
    for row in reader:
        process = row.get("process", "")
        subproc = row.get("subproc", "")
        process_counts[process] += 1
        subproc_counts[process][subproc] += 1
        total_rows += 1
report_path = os.path.join(os.path.dirname(full_journal_path), "full_journal_report.csv")
with open(report_path, "w", newline="") as outfile:
    writer = csv.writer(outfile)
    writer.writerow(["proc", "subproc", "count"])
    for proc, subprocs in subproc_counts.items():
        for sub, subcount in sorted(subprocs.items(), key=lambda x: -x[1]):
            writer.writerow([proc, sub, subcount])
    writer.writerow([])
    writer.writerow(["proc", "count"])
    for proc, count in sorted(process_counts.items(), key=lambda x: -x[1]):
        writer.writerow([proc, count])
    writer.writerow([])
    writer.writerow(["total_rows", total_rows])
