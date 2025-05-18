"""
% ccm_modify_date: 2025-05-18 16:57:22 %
% ccm_author: mpegg %
% ccm_version: 43 %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: main %
% ccm_object_id: media/export_movie_data.py:43 %
% ccm_commit_id: 85077287515bd36c372cecb566bd8b590687d30d %
% ccm_commit_count: 43 %
% ccm_last_commit_message: move config read %
% ccm_last_commit_author: Matthew Pegg %
% ccm_last_commit_date: 2025-03-22 17:57:56 -0400 %
% ccm_file_last_modified: 2025-05-18 16:52:46 %
% ccm_file_name: export_movie_data.py %
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

# Connect to the Radarr database
logging.info('Connecting to the Radarr database...')
conn = sqlite3.connect(r'C:\Users\All Users\Radarr\radarr.db')
cursor = conn.cursor()

# List all columns in the Movies table to verify the column names
logging.info('Listing all columns in the Movies table...')
cursor.execute("PRAGMA table_info(Movies);")
columns = cursor.fetchall()
logging.info(f'Columns in the Movies table: {columns}')

# movieFiles - id, movieid, size, originalpath
# movieMetaData - id, title, year, releaseDate, addedDate, collectionId, collectionTitle  
# movies - id, path, addeded, moviefileid

# Adjust the query based on the correct column names
logging.info('Executing query to fetch movie data...')
query = """
SELECT 
    movies.path,
    SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + 3, INSTR(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + 3), '\\') - 1) as vgName,
    SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + LENGTH(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + 3, INSTR(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + 3), '\\') - 1)) + 4) as showFolderName,
    movies.id, 
    movieMetaData.title, 
    movieMetaData.year, 
    movieMetaData.PhysicalRelease as FirstAired, 
    movieMetaData.DigitalRelease as LastAired, 
    movieMetaData.lastInfoSync, 
    ROUND(SUM(movieFiles.size) / (1024 * 1024 * 1024.0), 1) as TotalSizeGB,
    SUBSTR(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + LENGTH(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + 3, INSTR(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + 3), '\\') - 1)) + 4), INSTR(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + LENGTH(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + 3, INSTR(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + 3), '\\') - 1)) + 4), '(') + 1, INSTR(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + LENGTH(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + 3, INSTR(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + 3), '\\') - 1)) + 4), ')') - INSTR(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + LENGTH(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + 3, INSTR(SUBSTR(movies.Path, INSTR(movies.Path, 'VG\\') + 3), '\\') - 1)) + 4), '(') - 1) as showFolderYYYY
FROM movies
LEFT JOIN movieMetaData ON movies.MovieMetadataId = movieMetaData.Id
LEFT JOIN movieFiles ON movies.MovieFileId = movieFiles.Id
GROUP BY 
    movies.path,
    movies.id, 
    movieMetaData.title, 
    movieMetaData.year
"""

cursor.execute(query)
movies = cursor.fetchall()

# Create a new Excel workbook and add a worksheet
logging.info('Creating Excel workbook...')
wb = Workbook()
ws = wb.active
ws.title = "Movies"

# Add headers to the worksheet
headers = ["Path", "movieFolderName", "Id", "Title", "Year", "FirstAired", "LastAired", "lastInfoSync", "TotalSizeGB", "vgName", "movieFolderYYYY", "Backup Check"]
ws.append(headers)

# Add movie data to the worksheet
logging.info('Adding movie data to the worksheet...')
for i, movie in enumerate(movies, start=2):  # Start from row 2 since row 1 is headers
    path, vgName, movieFolderName, id, title, year, FirstAired, LastAired, lastInfoSync, totalSizeGB, movieFolderYYYY = movie
    ws.append([path, movieFolderName, id, title, year, FirstAired, LastAired, lastInfoSync, totalSizeGB, vgName, movieFolderYYYY])
    formula = f"=IFERROR(VLOOKUP(A{i},'[backup_control.xlsx]Media-Folders'!$A:$E,5,FALSE),\"-\")"
    ws[f'L{i}'] = formula  # Assuming 'L' is the last column

# Save the workbook to a file
output_file = r'C:\media.tt.omp\metadata\exported_movies_data.xlsx'
logging.info(f'Saving the workbook to {output_file}...')
try:
    wb.save(output_file)
    logging.info('Workbook saved successfully.')
except PermissionError:
    logging.error(f"\033[91mPermission denied: Unable to save the file '{output_file}'. Please close the file if it's open and try again.\033[0m")

# Close the database connection
conn.close()
logging.info('Database connection closed.')