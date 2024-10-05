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
