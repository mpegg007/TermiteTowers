"""
% ccm_modify_date: 2024-10-08 21:39:56 %
% ccm_author: mpegg %
% ccm_version: 25 %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: main %
% ccm_object_id: create_excel_control_file.py:25 %
% ccm_commit_id: b2a54cc00d6c06b63485f49b3b311e28586789fa %
% ccm_commit_count: 25 %
% ccm_last_commit_message: confirm latest %
% ccm_last_commit_author: Matthew Pegg %
% ccm_last_commit_date: 2024-10-08 19:34:16 -0400 %
% ccm_file_last_modified: 2024-10-08 21:39:21 %
% ccm_file_name: create_excel_control_file.py %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
"""

# run once code for creating an Excel template for folder backup.

import pandas as pd

def create_excel_control_file(file_path):
    # Define the columns for each sheet
    media_folders_columns = ['srcVolGrp', 'mediaType', 'srcFolder', 'BkupVolGrp']
    media_types_columns = ['mediaType', 'minSize', 'maxSize', 'fileExtn']

    # Create empty DataFrames with the specified columns
    df_media_folders = pd.DataFrame(columns=media_folders_columns)
    df_media_types = pd.DataFrame(columns=media_types_columns)

    # Create a Pandas Excel writer using XlsxWriter as the engine
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        # Write each DataFrame to a different worksheet
        df_media_folders.to_excel(writer, sheet_name='Media-Folders', index=False)
        df_media_types.to_excel(writer, sheet_name='Media-Types', index=False)

    print(f"Excel control file created at {file_path}")

if __name__ == "__main__":
    excel_file_path = 'C:\\media.tt.omp\\metadata\\backup_control.xlsx'
    create_excel_control_file(excel_file_path)
    