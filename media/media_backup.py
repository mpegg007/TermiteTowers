"""
% ccm_modify_date: 2024-10-20 13:15:40 %
% ccm_author: mpegg %
% ccm_version: 32 %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: main %
% ccm_object_id: media/media_backup.py:32 %
% ccm_commit_id: 5ecdf8c40f41881f58a5bde36eba99b142db29fb %
% ccm_commit_count: 32 %
% ccm_last_commit_message: media backup fixes %
% ccm_last_commit_author: Matthew Pegg %
% ccm_last_commit_date: 2024-10-20 12:47:54 -0400 %
% ccm_file_last_modified: 2024-10-20 13:13:20 %
% ccm_file_name: media_backup.py %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
"""

import os
import subprocess
import pandas as pd
import argparse

def backup_folder(src_vol_grp, src_folder, bkup_vol_grp, min_size, max_size, file_extn):
    script_path = os.path.join(os.path.dirname(__file__), 'OneShow.robocopy.cmd')
    print(f"Running backup for {src_vol_grp}, {src_folder}, {bkup_vol_grp} with minSize={min_size}, maxSize={max_size}, fileExtn={file_extn}")
    
    if not os.path.exists(script_path):
        print(f"Error: {script_path} not found.")
        return

    # Convert int to string for the three args
    min_size = str(min_size)
    max_size = str(max_size)
    file_extn = str(file_extn)

    # Set arguments to '-' if they are blank, zero, or 'nan'
    if not min_size or min_size == '0' or min_size.lower() == 'nan':
        min_size = '-'
    if not max_size or max_size == '0' or max_size.lower() == 'nan':
        max_size = '-'
    if not file_extn or file_extn.lower() == 'nan':
        file_extn = '-'

    # Print out the changed arguments
    print(f"Changed arguments: minSize={min_size}, maxSize={max_size}, fileExtn={file_extn}")

    try:
        result = subprocess.run(
            ['cmd.exe', '/c', script_path, src_vol_grp, src_folder, bkup_vol_grp, min_size, max_size, file_extn],
            check=False,  # Do not raise an exception on non-zero exit codes
            capture_output=True,
            text=True
        )
        # Check the exit code
        if result.returncode in [0, 1, 2, 3, 4]:
            print("Backup completed successfully.")
            print(result.stdout)
        else:
            print(f"An error occurred during backup: {result.returncode}")
            print(result.stdout)
            print(result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred during backup: {e}")
        print(e.stdout)
        print(e.stderr)

def read_folders_from_excel(file_path, src_vol_grp_filter=None, bkup_vol_grp_filter=None):
    # Read the Excel file
    df_folders = pd.read_excel(file_path, sheet_name='Media-Folders')
    df_types = pd.read_excel(file_path, sheet_name='Media-Types')

    # Strip any leading/trailing spaces from column names
    df_folders.columns = df_folders.columns.str.strip()
    df_types.columns = df_types.columns.str.strip()
    
    # Print column names for debugging
    print("Media-Folders columns:", df_folders.columns)
    print("Media-Types columns:", df_types.columns)

    # Apply filters if provided
    if src_vol_grp_filter:
        df_folders = df_folders[df_folders['srcVolGrp'] == src_vol_grp_filter]
    if bkup_vol_grp_filter:
        df_folders = df_folders[df_folders['BkupVolGrp'] == bkup_vol_grp_filter]

    # Merge the folders and types dataframes on the corresponding column
    df_merged = pd.merge(df_folders, df_types, on='mediaType')

    # Replace NaN values with '-'
    # df_merged = df_merged.fillna('-')
    
    # Create a list of tuples (src_vol_grp, src_folder, bkup_vol_grp, min_size, max_size, file_extn)
    folders_to_backup = [(row['srcVolGrp'], row['srcFolder'], row['BkupVolGrp'], row['minSize'], row['maxSize'], row['fileExtn']) for index, row in df_merged.iterrows()]

    return folders_to_backup

def main():
    parser = argparse.ArgumentParser(description='Backup media folders.')
    parser.add_argument('--srcVolGrp', type=str, help='Source Volume Group to filter')
    parser.add_argument('--bkupVolGrp', type=str, help='Backup Volume Group to filter')
    args = parser.parse_args()

    excel_file = 'C:\\media.tt.omp\\metadata\\backup_control.xlsx'
    folders_to_backup = read_folders_from_excel(excel_file, args.srcVolGrp, args.bkupVolGrp)

    for src_vol_grp, src_folder, bkup_vol_grp, min_size, max_size, file_extn in folders_to_backup:
        backup_folder(src_vol_grp, src_folder, bkup_vol_grp, min_size, max_size, file_extn)

if __name__ == "__main__":
    print("Starting the backup process...")
    main()
    print("Backup process completed.")