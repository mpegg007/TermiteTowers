#!/usr/bin/env python3
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: infra/dhcp/scripts/monitoring/tt-kea-health-http-dev1.py:121 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: a8ab807bdde52ced90e72a3f6dc608b3e6364633 %
#  %ccm_git_commit_id: 4a1cbe1072eb42723822f202e3fcd45247e1aa03 %
#  %ccm_git_commit_count: 121 %
#  %ccm_git_commit_date: 2025-11-30 12:26:01 -0500 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: cleanup %
#  %ccm_git_modify_date: 2025-11-30 12:26:14 %
#  %ccm_git_file_last_modified: 2025-11-30 12:26:14 %
#  %ccm_git_file_name: tt-kea-health-http-dev1.py %
#  %ccm_git_path: infra/dhcp/scripts/monitoring/tt-kea-health-http-dev1.py %
#  %ccm_git_language_mode: python %
#  %ccm_git_file_type: text/x-script.python %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1245 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: november changes % 
"""
Simple HTTP wrapper for Kea health check
Runs on port 9001 for Uptime Kuma to query
"""
import subprocess
from flask import Flask, Response

app = Flask(__name__)

@app.route('/health/kea')
def kea_health():
    """Execute Kea health check and return result"""
    try:
        result = subprocess.run(
            ['/srv/dev1/kea/scripts/monitoring/tt-kea-health-check-dev1.sh'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return Response(
                f"OK - Kea Health Check Passed\n{result.stdout}",
                status=200,
                mimetype='text/plain'
            )
        else:
            return Response(
                f"ERROR - Kea Health Check Failed\n{result.stdout}\n{result.stderr}",
                status=500,
                mimetype='text/plain'
            )
    except subprocess.TimeoutExpired:
        return Response("ERROR - Health check timed out", status=500, mimetype='text/plain')
    except Exception as e:
        return Response(f"ERROR - {str(e)}", status=500, mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=9001, debug=False)
