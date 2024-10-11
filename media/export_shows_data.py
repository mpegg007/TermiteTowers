"""
% ccm_modify_date: 2024-10-11 19:47:46 %
% ccm_author: mpegg %
% ccm_version: 27 %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: main %
% ccm_object_id: media/export_shows_data.py:27 %
% ccm_commit_id: 542f8ca3b50cda6e0d388ba5e53528f2e12e77f6 %
% ccm_commit_count: 27 %
% ccm_last_commit_message: x %
% ccm_last_commit_author: Matthew Pegg %
% ccm_last_commit_date: 2024-10-08 21:53:15 -0400 %
% ccm_file_last_modified: 2024-10-11 19:45:30 %
% ccm_file_name: export_shows_data.py %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
"""

import sqlite3
import csv
import logging
from openpyxl import Workbook, load_workbook

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
    Series.Id, 
    Series.Title, 
    Series.Year, 
    Series.FirstAired, 
    Series.LastAired, 
    Series.Path, 
    Series.lastInfoSync, 
    ROUND(SUM(EpisodeFiles.Size) / (1024 * 1024 * 1024.0), 1) as TotalSizeGB,
    SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3, INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3), '\\') - 1) as vgName,
    SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + LENGTH(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3, INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3), '\\') - 1)) + 4) as showFolderName,
    SUBSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + LENGTH(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3, INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3), '\\') - 1)) + 4), INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + LENGTH(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3, INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3), '\\') - 1)) + 4), '(') + 1, INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + LENGTH(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3, INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3), '\\') - 1)) + 4), ')') - INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + LENGTH(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3, INSTR(SUBSTR(Series.Path, INSTR(Series.Path, 'VG\\') + 3), '\\') - 1)) + 4), '(') - 1) as showFolderYYYY
FROM Series
LEFT JOIN EpisodeFiles ON Series.Id = EpisodeFiles.SeriesId
GROUP BY 
    Series.Id, 
    Series.Title, 
    Series.Year, 
    Series.FirstAired, 
    Series.LastAired, 
    Series.Path, 
    Series.lastInfoSync
"""

cursor.execute(query)

# Fetch all results
logging.info('Fetching results...')
rows = cursor.fetchall()

# Get column names
column_names = [description[0] for description in cursor.description]

# Write to CSV with utf-8 encoding
csv_file = 'series.csv'
logging.info(f'Writing data to CSV file: {csv_file}')
with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(column_names)  # Write header
    csvwriter.writerows(rows)         # Write data

# Define the Excel file and sheet name
excel_file = r'C:\media.tt.omp\metadata\media-titles.xlsx'
sheet_name = 'sonarr-shows-data'

try:
    # Try to load the existing workbook
    logging.info(f'Loading Excel file: {excel_file}')
    workbook = load_workbook(excel_file)
    if sheet_name in workbook.sheetnames:
        # If the sheet exists, remove it
        logging.info(f'Removing existing sheet: {sheet_name}')
        workbook.remove(workbook[sheet_name])
    # Create a new sheet
    logging.info(f'Creating new sheet: {sheet_name}')
    sheet = workbook.create_sheet(sheet_name)
except FileNotFoundError:
    # If the file does not exist, create a new workbook and sheet
    logging.info(f'Excel file not found. Creating new file: {excel_file}')
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name

# Write column names to the sheet
logging.info('Writing column names to the Excel sheet...')
sheet.append(column_names)

# Write data to the sheet
logging.info('Writing data to the Excel sheet...')
for row in rows:
    sheet.append(row)

# Save the workbook
logging.info(f'Saving Excel file: {excel_file}')
workbook.save(excel_file)

# Close the connection
logging.info('Closing the database connection...')
conn.close()
logging.info('Script completed successfully.')
