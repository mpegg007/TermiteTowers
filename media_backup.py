"""
% ccm_modify_date: 2024-10-08 19:34:17 %
% ccm_author: mpegg %
% ccm_version: 24 %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: main %
% ccm_object_id: media_backup.py:24 %
% ccm_commit_id: 16c7536b7f720b4fa8a6ef398ce2f9af9d9087a0 %
% ccm_commit_count: 24 %
% ccm_last_commit_message: test %
% ccm_last_commit_author: Matthew Pegg %
% ccm_last_commit_date: 2024-10-07 20:42:24 -0400 %
% ccm_file_last_modified: 2024-10-08 19:33:42 %
% ccm_file_name: media_backup.py %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
"""

# primary script

import os
import subprocess
from datetime import datetime
import pandas as pd

def backup_folder(src_vol_grp, src_folder, bkup_vol_grp):
    script_path = os.path.join(os.path.dirname(__file__), 'media', 'OneShow.robocopy.cmd')
    
    if not os.path.exists(script_path):
        print(f"Error: {script_path} not found.")
        return

    try:
        result = subprocess.run(
            ['cmd.exe', '/c', script_path, src_vol_grp, src_folder, bkup_vol_grp],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print(result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred during backup: {e}")
        print(e.stdout)
        print(e.stderr)

def read_folders_from_excel(file_path):
    # Read the Excel file
    df_folders = pd.read_excel(file_path, sheet_name='Media-Folders')

    # Create a list of tuples (src_vol_grp, src_folder, bkup_vol_grp)
    folders_to_backup = [(row['srcVolGrp'], row['srcFolder'], row['BkupVolGrp']) for index, row in df_folders.iterrows()]

    return folders_to_backup

# Example usage
excel_file = 'C:\\media.tt.omp\\metadata\\backup_control.xlsx'

folders_to_backup = read_folders_from_excel(excel_file)

for src_vol_grp, src_folder, bkup_vol_grp in folders_to_backup:
    print(f"Working on file: {src_folder}")
    backup_folder(src_vol_grp, src_folder, bkup_vol_grp)