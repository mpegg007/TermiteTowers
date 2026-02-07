#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 2392a58cc321df0301c6320d9efad8faa2f70899 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2026-02-07 15:39:18 %
#  %ccm_git_file_last_modified: 2026-02-07 15:39:18 %
#  %ccm_git_file_name: test-dns.sh %
#  %ccm_git_path: infra/dns/scripts/monitoring/test-dns.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 875 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2025-11-30 mpegg  november changes  % 
# DNS Resolution Test Script

echo "=== DNS Resolution Tests ==="
echo ""

echo "1. Testing .local domain:"
dig @localhost test.local +short
echo "Status: $?"
echo ""

echo "2. Testing google.com:"
dig @localhost google.com +short
echo "Status: $?"
echo ""

echo "3. Testing tt.omp domain:"
dig @localhost test.tt.omp +short
echo "Status: $?"
echo ""

echo "4. Testing aa.omp domain:"
dig @localhost test.aa.omp +short
echo "Status: $?"
echo ""

echo "=== Summary ==="
echo ".local works: $(dig @localhost test.local +short > /dev/null 2>&1 && echo YES || echo NO)"
echo "google.com works: $(dig @localhost google.com +short > /dev/null 2>&1 && echo YES || echo NO)"
echo "tt.omp works: $(dig @localhost test.tt.omp +short > /dev/null 2>&1 && echo YES || echo NO)"
echo "aa.omp works: $(dig @localhost test.aa.omp +short > /dev/null 2>&1 && echo YES || echo NO)"
