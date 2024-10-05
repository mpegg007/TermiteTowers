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
