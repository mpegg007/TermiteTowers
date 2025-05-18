"""
% ccm_modify_date: 2025-05-18 16:57:22 %
% ccm_author: mpegg %
% ccm_version: 43 %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: main %
% ccm_object_id: media/create_excel_control_file.py:43 %
% ccm_commit_id: 85077287515bd36c372cecb566bd8b590687d30d %
% ccm_commit_count: 43 %
% ccm_last_commit_message: move config read %
% ccm_last_commit_author: Matthew Pegg %
% ccm_last_commit_date: 2025-03-22 17:57:56 -0400 %
% ccm_file_last_modified: 2025-04-24 18:38:03 %
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
    excel_file_path = 'C:\\Users\\mpegg\\OneDrive\\media.tt.omp\\backup_control-sample.xlsx'
    create_excel_control_file(excel_file_path)
    