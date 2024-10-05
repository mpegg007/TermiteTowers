import re
import sys
import getpass
import subprocess
from datetime import datetime
import os
import mimetypes

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
    # Skip the script itself
    if os.path.basename(file_path) == "update_keywords.py":
        print(f"Skipping {file_path}")
        return

    # Read the file content
    with open(file_path, 'r') as file:
        content = file.read()

    # Get current datetime
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Get current username
    current_username = getpass.getuser()

    # Get current commit count
    current_commit_count = get_git_commit_count()

    # Get current commit hash
    current_commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip().decode('utf-8')

    # Get current branch name
    current_branch_name = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).strip().decode('utf-8')

    # Get current repo URL
    current_repo_url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url']).strip().decode('utf-8')

    # Get last commit message
    last_commit_message = get_git_last_commit_message()

    # Get last commit author
    last_commit_author = get_git_last_commit_author()

    # Get last commit date
    last_commit_date = get_git_last_commit_date()

    # Get file last modified date
    file_last_modified = get_file_last_modified(file_path)

    # Get the relative file path
    repo_root = get_repo_root()
    if repo_root:
        relative_file_path = os.path.relpath(file_path, repo_root)
    else:
        relative_file_path = file_path

    # Get the file type
    file_type = mimetypes.guess_type(file_path)[0] or 'unknown'

    # Get the EOL marker
    file_eol = get_file_eol(file_path)

    # Get the filename
    file_name = os.path.basename(file_path)

    # Define the patterns and their replacements
    patterns_replacements = {
        r'% ccm_modify_date: .*? %': f'% ccm_modify_date: {current_datetime} %',
        r'% ccm_author: .*? %': f'% ccm_author: {current_username} %',
        r'% ccm_version: .*? %': f'% ccm_version: {current_commit_count} %',
        r'% ccm_commit_id: .*? %': f'% ccm_commit_id: {current_commit_hash} %',
        r'% ccm_branch: .*? %': f'% ccm_branch: {current_branch_name} %',
        r'% ccm_repo: .*? %': f'% ccm_repo: {current_repo_url} %',
        r'% ccm_object_id: .*? %': f'% ccm_object_id: {relative_file_path}:{current_commit_count} %',
        r'% ccm_commit_count: .*? %': f'% ccm_commit_count: {current_commit_count} %',
        r'% ccm_last_commit_message: .*? %': f'% ccm_last_commit_message: {last_commit_message} %',
        r'% ccm_last_commit_author: .*? %': f'% ccm_last_commit_author: {last_commit_author} %',
        r'% ccm_last_commit_date: .*? %': f'% ccm_last_commit_date: {last_commit_date} %',
        r'% ccm_file_last_modified: .*? %': f'% ccm_file_last_modified: {file_last_modified} %',
        r'% ccm_file_type: .*? %': f'% ccm_file_type: {re.escape(file_type)} %',
        r'% ccm_file_eol: .*? %': f'% ccm_file_eol: {re.escape(file_eol)} %',  # Escape the EOL marker
        r'% ccm_file_name: .*? %': f'% ccm_file_name: {file_name} %'
    }

    # Replace the patterns in the content
    for pattern, replacement in patterns_replacements.items():
        content = re.sub(pattern, replacement, content)

    # Write the modified content back to the file
    with open(file_path, 'w') as file:
        file.write(content)

    # Re-add the modified file to the staging area
    subprocess.check_call(['git', 'add', file_path])

if __name__ == "__main__":
    for file_path in sys.argv[1:]:
        print(f"NOT Updating keywords in {file_path}")
        #update_keywords(file_path)
