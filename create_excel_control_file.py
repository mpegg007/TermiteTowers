"""
% ccm_modify_date: 2024-10-05 16:37:40 %
% ccm_author: mpegg %
% ccm_version: 10 %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: main %
% ccm_object_id: create_excel_control_file.py:10 %
% ccm_commit_id: 516b46c33f94a6228a10a0c23c4af07f3c18b61a %
% ccm_commit_count: 10 %
% ccm_last_commit_message: test %
% ccm_last_commit_author: Matthew Pegg %
% ccm_last_commit_date: 2024-10-05 14:19:15 -0400 %
% ccm_file_last_modified: 2024-10-05 16:33:57 %
% ccm_file_name: create_excel_control_file.py %
% ccm_file_type: text/x-python %
% ccm_file_encoding: CRLF %
% ccm_file_eol: CRLF %
"""

# run once code for creating an Excel template for folder backup.

import pandas as pd
import os

# Create DataFrames for the two tabs
drive_map_data = {
    'DriveID': ['Drive1', 'Drive2'],
    'Location': ['D:\\path\\to\\backup\\drive1', 'E:\\path\\to\\backup\\drive2']
}

folders_data = {
    'Folder': ['C:\\path\\to\\source\\folder1', 'C:\\path\\to\\source\\folder2'],
    'DriveID': ['Drive1', 'Drive2']
}

df_drive_map = pd.DataFrame(drive_map_data)
df_folders = pd.DataFrame(folders_data)

# Define the path to save the Excel file
output_path = 'C:\\temp\\folders_list_template.xlsx'

# Ensure the output directory exists
os.makedirs(os.path.dirname(output_path), exist_ok=True)

# Save the DataFrames to an Excel file
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df_drive_map.to_excel(writer, sheet_name='DriveMap', index=False)
    df_folders.to_excel(writer, sheet_name='Folders', index=False)

print(f"Excel template saved to {output_path}")
