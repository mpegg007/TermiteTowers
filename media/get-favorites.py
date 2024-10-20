import os
import logging
import csv
import google.auth
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to authenticate and get the YouTube service
def get_authenticated_service():
    logging.info('Authenticating and getting the YouTube service...')
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            'client_secret.json', SCOPES)
        credentials = flow.run_local_server(port=0)
        logging.info('Authentication successful.')
        return build('youtube', 'v3', credentials=credentials)
    except Exception as e:
        logging.error(f'Error during authentication: {e}')
        raise

# Function to get video details from the Liked Music playlist and save to a CSV file
def get_liked_music_video_details(youtube):
    try:
        liked_music_playlist_id = 'LM'
        logging.info(f'Fetching the videos in the Liked Music playlist (ID: {liked_music_playlist_id})...')

        video_details = []
        next_page_token = None

        while True:
            # Fetch the videos in the Liked Music playlist
            response = youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=liked_music_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()
            logging.debug(f'PlaylistItems response: {response}')

            if 'items' not in response or not response['items']:
                logging.error('No items found in playlistItems response.')
                break

            # Extract video details
            for item in response['items']:
                snippet = item['snippet']
                content_details = item['contentDetails']
                video_details.append({
                    'title': snippet['title'],
                    'description': snippet.get('description', ''),
                    'publishedAt': snippet['publishedAt'],
                    'videoId': content_details['videoId']
                })
                logging.info(f'Video title: {snippet["title"]}')

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        # Save video details to a CSV file
        with open('liked_music_details.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['title', 'description', 'publishedAt', 'videoId'])
            writer.writeheader()
            writer.writerows(video_details)

        logging.info('Video details saved to liked_music_details.csv')

    except HttpError as e:
        logging.error(f'An HTTP error {e.resp.status} occurred: {e.content}')
    except Exception as e:
        logging.error(f'An error occurred: {e}')

# Main function to run the script
if __name__ == '__main__':
    try:
        logging.info('Starting the script...')
        youtube = get_authenticated_service()
        get_liked_music_video_details(youtube)
        logging.info('Script completed successfully.')
    except Exception as e:
        logging.error(f'An error occurred in the main function: {e}')