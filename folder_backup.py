"""
% ccm_modify_date: 2024-10-05 14:17:38 %
% ccm_author: mpegg %
% ccm_version: 8 %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: main %
% ccm_object_id: folder_backup.py:8 %
% ccm_commit_id: dbaa495ea5fbbb2a2f55cea4e3491bace9eec020 %
% ccm_commit_count: 8 %
% ccm_last_commit_message: exclude update_keywords.py from hook %
% ccm_last_commit_author: Matthew Pegg %
% ccm_last_commit_date: 2024-10-05 13:55:44 -0400 %
% ccm_file_last_modified: 2024-10-05 14:16:49 %
% ccm_file_name: folder_backup.py %
% ccm_file_type: text/x-python %
% ccm_file_encoding: CRLF %
% ccm_file_eol: CRLF %
"""

# t

import os
import shutil
from datetime import datetime
import pandas as pd

def backup_folder(source_dir, dest_dir):
    # Check if source directory exists
    if not os.path.exists(source_dir):
        print(f"Source directory {source_dir} does not exist.")
        return

    # Create a timestamped folder in the destination directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(dest_dir, f"backup_{timestamp}")
    os.makedirs(backup_dir)

    # Copy all files and subdirectories from source to destination
    try:
        shutil.copytree(source_dir, backup_dir)
        print(f"Backup completed successfully. Files are backed up to {backup_dir}")
    except Exception as e:
        print(f"An error occurred during backup: {e}")

def read_folders_from_excel(file_path):
    # Read the Excel file
    df_drive_map = pd.read_excel(file_path, sheet_name='DriveMap')
    df_folders = pd.read_excel(file_path, sheet_name='Folders')

    # Create a dictionary to map drive IDs to actual locations
    drive_map = dict(zip(df_drive_map['DriveID'], df_drive_map['Location']))

    # Create a list of tuples (source_folder, destination_folder)
    folders_to_backup = [(row['Folder'], drive_map[row['DriveID']]) for index, row in df_folders.iterrows()]

    return folders_to_backup

# Example usage
excel_file = 'C:\\path\\to\\folders_list.xlsx'

folders_to_backup = read_folders_from_excel(excel_file)

for source_folder, destination_folder in folders_to_backup:
    backup_folder(source_folder, destination_folder)
