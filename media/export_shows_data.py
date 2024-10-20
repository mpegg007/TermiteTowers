"""
% ccm_modify_date: 2024-10-20 12:47:54 %
% ccm_author: mpegg %
% ccm_version: 31 %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: main %
% ccm_object_id: media/export_shows_data.py:31 %
% ccm_commit_id: c55d8e627d7fb98a30796524ce44ae51335ea596 %
% ccm_commit_count: 31 %
% ccm_last_commit_message: handle spaces in /log switch for robocopy %
% ccm_last_commit_author: Matthew Pegg %
% ccm_last_commit_date: 2024-10-20 12:14:32 -0400 %
% ccm_file_last_modified: 2024-10-20 12:04:16 %
% ccm_file_name: export_shows_data.py %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
"""

import os
import logging
from openpyxl import Workbook
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Connect to the Sonarr database
logging.info('Connecting to the Sonarr database...')
conn = sqlite3.connect(r'C:\Users\All Users\Sonarr\sonarr.db')
cursor = conn.cursor()

# Execute a query to get series data along with the total size of episodes
logging.info('Executing query to fetch series data...')
query = """
SELECT 
    Series.Path,
    SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3, INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3), '\\') - 1) as vgName,
    SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + LENGTH(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3, INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3), '\\') - 1)) + 4) as showFolderName,
    Series.Id, 
    Series.Title, 
    Series.Year, 
    Series.FirstAired, 
    Series.LastAired, 
    Series.lastInfoSync, 
    ROUND(SUM(EpisodeFiles.Size) / (1024 * 1024 * 1024.0), 1) as TotalSizeGB,
    SUBSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + LENGTH(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3, INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3), '\\') - 1)) + 4), INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + LENGTH(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3, INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3), '\\') - 1)) + 4), '(') + 1, INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + LENGTH(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3, INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3), '\\') - 1)) + 4), ')') - INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + LENGTH(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3, INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3), '\\') - 1)) + 4), '(') - 1) as showFolderYYYY
FROM Series
LEFT JOIN EpisodeFiles ON Series.Id = EpisodeFiles.SeriesId
GROUP BY 
    Series.Path,
    vgName,
    showFolderName,
    Series.Id, 
    Series.Title, 
    Series.Year, 
    Series.FirstAired, 
    Series.LastAired, 
    Series.lastInfoSync
"""

cursor.execute(query)

# Fetch all results
logging.info('Fetching results...')
rows = cursor.fetchall()

# Define the new column order
column_names = [
    'Path',  # Add Path as the first column
    'showFolderName',  # Add showFolderName as the second column
    'Id', 
    'Title', 
    'Year', 
    'FirstAired', 
    'LastAired', 
    'lastInfoSync', 
    'TotalSizeGB', 
    'vgName', 
    'showFolderYYYY',  # Add showFolderYYYY
    'Backup Check'
]

# Define the Excel file and sheet name
excel_file = r'C:\media.tt.omp\metadata\media-titles.xlsx'
sheet_name = 'sonarr-shows-data'

# Delete the output file if it exists
if os.path.exists(excel_file):
    logging.info(f'Deleting existing Excel file: {excel_file}')
    os.remove(excel_file)

# Create a new workbook
logging.info(f'Creating new workbook: {excel_file}')
workbook = Workbook()

# Create a new sheet
logging.info(f'Creating new sheet: {sheet_name}')
sheet = workbook.active
sheet.title = sheet_name

# Write column names to the sheet
logging.info('Writing column names to the Excel sheet...')
sheet.append(column_names)

# Write data to the sheet and add the formula in the last column
logging.info('Writing data to the Excel sheet...')
for i, row in enumerate(rows, start=2):  # start=2 to account for header row
    reordered_row = [
        row[0],  # Path
        row[2],  # showFolderName
        row[3],  # Id
        row[4],  # Title
        row[5],  # Year
        row[6],  # FirstAired
        row[7],  # LastAired
        row[8],  # lastInfoSync
        row[9],  # TotalSizeGB
        row[1],  # vgName
        row[10], # showFolderYYYY
    ]
    sheet.append(reordered_row)
    formula = f'=IFERROR(VLOOKUP(A{i},\'[backup_control.xlsx]Media-Folders\'!$A:$E,5,FALSE),"-")'
    sheet[f'L{i}'] = formula  # Assuming 'L' is the last column

# Create a summary dataset grouped by vgName
logging.info('Creating summary dataset grouped by vgName...')
summary_data = {}
for row in rows:
    vg_name = row[1]  # Assuming vgName is the 2nd column in the result set
    total_size_gb = float(row[9]) if row[9] is not None else 0.0  # Handle None values and convert to float
    first_aired = row[6] if row[6] is not None else '1900-01-01'  # Handle None values
    last_aired = row[7] if row[7] is not None else '1900-01-01'  # Handle None values
    year = row[5] if row[5] is not None else 1900  # Handle None values
    if vg_name not in summary_data:
        summary_data[vg_name] = {
            'count': 0,
            'sum': 0.0,
            'min_first_aired': first_aired,
            'max_first_aired': first_aired,
            'min_last_aired': last_aired,
            'max_last_aired': last_aired,
            'min_year': year,
            'max_year': year
        }
    summary_data[vg_name]['count'] += 1
    summary_data[vg_name]['sum'] += total_size_gb
    summary_data[vg_name]['min_first_aired'] = min(summary_data[vg_name]['min_first_aired'], first_aired)
    summary_data[vg_name]['max_first_aired'] = max(summary_data[vg_name]['max_first_aired'], first_aired)
    summary_data[vg_name]['min_last_aired'] = min(summary_data[vg_name]['min_last_aired'], last_aired)
    summary_data[vg_name]['max_last_aired'] = max(summary_data[vg_name]['max_last_aired'], last_aired)
    summary_data[vg_name]['min_year'] = min(summary_data[vg_name]['min_year'], year)
    summary_data[vg_name]['max_year'] = max(summary_data[vg_name]['max_year'], year)

# Create a new sheet for the summary data
summary_sheet_name = 'summary-data'
logging.info(f'Creating new sheet: {summary_sheet_name}')
summary_sheet = workbook.create_sheet(title=summary_sheet_name)

# Write summary column names to the sheet
summary_column_names = ['vgName', 'count', 'sum', 'min_first_aired', 'max_first_aired', 'min_last_aired', 'max_last_aired', 'min_year', 'max_year']
logging.info('Writing summary column names to the Excel sheet...')
summary_sheet.append(summary_column_names)

# Write summary data to the sheet
logging.info('Writing summary data to the Excel sheet...')
for vg_name, data in summary_data.items():
    summary_row = [
        vg_name,
        data['count'],
        data['sum'],
        data['min_first_aired'],
        data['max_first_aired'],
        data['min_last_aired'],
        data['max_last_aired'],
        data['min_year'],
        data['max_year']
    ]
    summary_sheet.append(summary_row)

# Save the workbook
logging.info(f'Saving Excel file: {excel_file}')
workbook.save(excel_file)

# Close the connection
logging.info('Closing the database connection...')
conn.close()
logging.info('Script completed successfully.')