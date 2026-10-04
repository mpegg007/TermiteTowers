#!/usr/bin/env bash

# TermiteTowers Continuous Code Management Header TEMPLATE
# % ccm_modify_date: 2025-08-29 15:31:33 %
# % ccm_author: mpegg %
# % ccm_author_email: mpegg@hotmail.com %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: dev1 %
# % ccm_object_id: scripts/system/gather-info.sh:0 %
# % ccm_commit_id: unknown %
# % ccm_commit_count: 0 %
# % ccm_commit_message: unknown %
# % ccm_commit_author: unknown %
# % ccm_commit_email: unknown %
# % ccm_commit_date: 1970-01-01 00:00:00 +0000 %
# % ccm_file_last_modified: 2025-08-29 15:31:33 %
# % ccm_file_name: gather-info.sh %
# % ccm_file_type: text/x-shellscript %
# % ccm_file_encoding: utf-8 %
# % ccm_file_eol: CRLF %
# % ccm_path: scripts/system/gather-info.sh %
# % ccm_blob_sha: 27a874fe20d4c05be0ece48f182ac9fe38f764eb %
# % ccm_exec: yes %
# % ccm_size: 1600 %
# % ccm_tag:  %
# tt-ccm.header.end


uname -a                       # kernel name, version, architecture
lsb_release -a                 # distribution name and version (Linux)
sw_vers                        # macOS version (if on macOS)

echo $SHELL                    # path to your login shell
basename $SHELL                # shell name (bash, zsh, fish…)
$SHELL --version              # version info for that shell

which python                   # path to python interpreter
python --version              # Python version

which python3
python3 --version

echo $VIRTUAL_ENV             # full path to active virtualenv
which python

devpi-server --version        # devpi-server version
devpi --version               # devpi client version
