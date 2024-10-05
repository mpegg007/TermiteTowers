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

def get_file_encoding(file_path):
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
