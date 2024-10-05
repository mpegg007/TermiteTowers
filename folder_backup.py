"""
% ccm_modify_date: xx2024-10-05 12:38:07 %
% ccm_author: xxmpegg %
% ccm_version: xx2 %
% ccm_repo: xxhttps://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: xxmain %
% ccm_object_id: xxsample.py:2 %
% ccm_commit_id: xx81a1073ed784cee95a9cc17b98f5a6e75dc689f3 %
% ccm_commit_count: xx2 %
% ccm_last_commit_message: xxtest2 %
% ccm_last_commit_author: xxMatthew Pegg %
% ccm_last_commit_date: xx2024-10-05 12:37:42 -0400 %
% ccm_file_last_modified: xx2024-10-05 12:37:26 %
% ccm_file_name: xxsample.py %
% ccm_file_type: xxtext/x-python %
% ccm_file_encoding: xxascii %
% ccm_file_eol: xxCRLF %
"""

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
