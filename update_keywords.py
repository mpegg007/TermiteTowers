import re
import sys
import getpass
import subprocess
from datetime import datetime
import os
import mimetypes

def get_git_commit_hash():
    try:
        commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip().decode('utf-8')
        return commit_hash
    except subprocess.CalledProcessError:
        return 'unknown'

def get_git_branch_name():
    try:
        branch_name = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).strip().decode('utf-8')
        return branch_name
    except subprocess.CalledProcessError:
        return 'unknown'

def get_git_repo_url():
    try:
        repo_url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url']).strip().decode('utf-8')
        return repo_url
    except subprocess.CalledProcessError:
        return 'unknown'

def get_git_commit_count():
    try:
        commit_count = subprocess.check_output(['git', 'rev-list', '--count', 'HEAD']).strip().decode('utf-8')
        return commit_count
    except subprocess.CalledProcessError:
        return 'unknown'

def get_git_last_commit_message():
    try:
        commit_message = subprocess.check_output(['git', 'log', '-1', '--pretty=%B']).strip().decode('utf-8')
        return commit_message
    except subprocess.CalledProcessError:
        return 'unknown'

def get_git_last_commit_author():
    try:
        commit_author = subprocess.check_output(['git', 'log', '-1', '--pretty=%an']).strip().decode('utf-8')
        return commit_author
    except subprocess.CalledProcessError:
        return 'unknown'

def get_git_last_commit_date():
    try:
        commit_date = subprocess.check_output(['git', 'log', '-1', '--pretty=%ad', '--date=iso']).strip().decode('utf-8')
        return commit_date
    except subprocess.CalledProcessError:
        return 'unknown'

def get_file_last_modified(file_path):
    try:
        last_modified_date = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
        return last_modified_date
    except Exception:
        return 'unknown'

def get_repo_root():
    try:
        repo_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel']).strip().decode('utf-8')
        return repo_root
    except subprocess.CalledProcessError:
        return None

def get_relative_path(file_path, repo_root):
    return os.path.relpath(file_path, repo_root)

def get_file_type(file_path):
    file_type, _ = mimetypes.guess_type(file_path)
    return file_type if file_type else 'unknown'

def get_file_encoding(file_path):
    try:
        with open(file_path, 'rb') as file:
            raw_data = file.read()
            result = chardet.detect(raw_data)
            return result['encoding']
    except Exception:
        return 'unknown'

def get_file_eol(file_path):
    try:
        with open(file_path, 'rb') as file:
            raw_data = file.read()
            if b'\r\n' in raw_data:
                return 'CRLF'
            elif b'\n' in raw_data:
                return 'LF'
            elif b'\r' in raw_data:
                return 'CR'
            else:
                return 'unknown'
    except Exception:
        return 'unknown'

def update_keywords(file_path):
    with open(file_path, 'r') as file:
        content = file.read()

    # Get the current date and time
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Get the current username
    current_username = getpass.getuser()

    # Get the current Git commit hash
    current_commit_hash = get_git_commit_hash()

    # Get the current Git branch name
    current_branch_name = get_git_branch_name()

    # Get the Git repository URL
    current_repo_url = get_git_repo_url()

    # Get the Git commit count
    current_commit_count = get_git_commit_count()

    # Get the last commit message
    last_commit_message = get_git_last_commit_message()

    # Get the last commit author
    last_commit_author = get_git_last_commit_author()

    # Get the last commit date
    last_commit_date = get_git_last_commit_date()

    # Get the file last modified date
    file_last_modified = get_file_last_modified(file_path)

    # Get the repository root
    repo_root = get_repo_root()
    if repo_root:
        relative_file_path = get_relative_path(file_path, repo_root)
    else:
        relative_file_path = file_path

    # Get the file type
    file_type = get_file_type(file_path)

    # Get the file encoding
    file_encoding = get_file_encoding(file_path)

    # Get the EOL marker
    file_eol = get_file_eol(file_path)

    # Get the filename
    file_name = os.path.basename(file_path)

    # Define the patterns and their replacements
    patterns_replacements = {
        r'% ccm_modify_date: 2024-10-05 13:49:55 %': f'% ccm_modify_date: 2024-10-05 13:49:55 %',
        r'% ccm_author: mpegg %': f'% ccm_author: mpegg %',
        r'% ccm_version: 6 %': f'% ccm_version: 6 %',
        r'% ccm_commit_id: dd435d8a528b7244d00e69ea0a7c4b91b3fe1b73 %': f'% ccm_commit_id: dd435d8a528b7244d00e69ea0a7c4b91b3fe1b73 %',
        r'% ccm_branch: main %': f'% ccm_branch: main %',
        r'% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %': f'% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %',
        r'% ccm_object_id: update_keywords.py:6 %': f'% ccm_object_id: update_keywords.py:6 %',
        r'% ccm_commit_count: 6 %': f'% ccm_commit_count: 6 %',
        r'% ccm_last_commit_message: adding comment block %': f'% ccm_last_commit_message: adding comment block %',
        r'% ccm_last_commit_author: Matthew Pegg %': f'% ccm_last_commit_author: Matthew Pegg %',
        r'% ccm_last_commit_date: 2024-10-05 13:40:58 -0400 %': f'% ccm_last_commit_date: 2024-10-05 13:40:58 -0400 %',
        r'% ccm_file_last_modified: 2024-10-05 13:49:50 %': f'% ccm_file_last_modified: 2024-10-05 13:49:50 %',
        r'% ccm_file_type: text/x-python %': f'% ccm_file_type: text/x-python %',
        r'% ccm_file_encoding: unknown %': f'% ccm_file_encoding: unknown %',
        r'% ccm_file_eol: CRLF %': f'% ccm_file_eol: CRLF %',
        r'% ccm_file_name: update_keywords.py %': f'% ccm_file_name: update_keywords.py %'
    }

    # Replace the patterns in the content
    for pattern, replacement in patterns_replacements.items():
        content = re.sub(pattern, replacement, content)

    with open(file_path, 'w') as file:
        file.write(content)

if __name__ == "__main__":
    for file_path in sys.argv[1:]:
        update_keywords(file_path)
