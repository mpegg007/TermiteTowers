"""
% ccm_modify_date: 2024-10-05 13:49:54 %
% ccm_author: mpegg %
% ccm_version: 6 %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: main %
% ccm_object_id: create_excel_control_file.py:6 %
% ccm_commit_id: dd435d8a528b7244d00e69ea0a7c4b91b3fe1b73 %
% ccm_commit_count: 6 %
% ccm_last_commit_message: adding comment block %
% ccm_last_commit_author: Matthew Pegg %
% ccm_last_commit_date: 2024-10-05 13:40:58 -0400 %
% ccm_file_last_modified: 2024-10-05 13:46:53 %
% ccm_file_name: create_excel_control_file.py %
% ccm_file_type: text/x-python %
% ccm_file_encoding: unknown %
% ccm_file_eol: CRLF %
"""

#

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
