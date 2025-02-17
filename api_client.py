import os
import streamlit as st
from googleapiclient.discovery import build
from langchain_google_genai import GoogleGenerativeAI

class APIClient:
    def __init__(self):
        self.youtube_api = None
        self.gemini_model = None
        self.initialize_apis()
    
    def initialize_apis(self):
        """Initialize API clients with error handling"""
        youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        google_api_key = os.getenv('GOOGLE_API_KEY')
        
        if not youtube_api_key:
            st.write("⚠️ YouTube API Key not found. Please add YOUTUBE_API_KEY to your .env file")
            return
        
        if not google_api_key:
            st.write("⚠️ Google API Key not found. Please add GOOGLE_API_KEY to your .env file")
            return
        
        try:
            self.youtube_api = build('youtube', 'v3', developerKey=youtube_api_key)
            self.gemini_model = GoogleGenerativeAI(model="gemini-pro", google_api_key=google_api_key)
        except Exception as e:
            st.write(f"⚠️ Error initializing APIs: {str(e)}")
    
    def get_video_comments(self, video_id, max_comments=500):
        """Fetch comments for a video"""
        try:
            comments = []
            request = self.youtube_api.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=max_comments,
                textFormat="plainText"
            )
            
            while request and len(comments) < max_comments:
                try:
                    response = request.execute()
                    for item in response['items']:
                        comment = item['snippet']['topLevelComment']['snippet']
                        comments.append({
                            'text': comment['textDisplay'],
                            'likes': comment['likeCount'],
                            'publishedAt': comment['publishedAt']
                        })
                    
                    if 'nextPageToken' in response:
                        request = self.youtube_api.commentThreads().list(
                            part="snippet",
                            videoId=video_id,
                            maxResults=max_comments - len(comments),
                            pageToken=response['nextPageToken'],
                            textFormat="plainText"
                        )
                    else:
                        break
                except Exception as api_error:
                    if "commentsDisabled" in str(api_error):
                        st.info("💬 Comments are disabled for this video")
                    else:
                        st.warning(f"⚠️ Error fetching comments: {str(api_error)}")
                    break
            
            return comments
        except Exception as e:
            st.warning(f"⚠️ Error initializing comments request: {str(e)}")
            return []
    
    def get_all_comments(self, video_id):
        """Fetch all comments for a video"""
        try:
            comments = []
            request = self.youtube_api.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                textFormat="plainText"
            )
            
            while request:
                try:
                    response = request.execute()
                    for item in response['items']:
                        comment = item['snippet']['topLevelComment']['snippet']
                        comments.append({
                            'text': comment['textDisplay'],
                            'likes': comment['likeCount'],
                            'publishedAt': comment['publishedAt']
                        })
                    
                    if 'nextPageToken' in response:
                        request = self.youtube_api.commentThreads().list(
                            part="snippet",
                            videoId=video_id,
                            maxResults=100,
                            pageToken=response['nextPageToken'],
                            textFormat="plainText"
                        )
                    else:
                        break
                except Exception as api_error:
                    if "commentsDisabled" in str(api_error):
                        st.info("💬 Comments are disabled for this video")
                    else:
                        st.warning(f"⚠️ Error fetching comments: {str(api_error)}")
                    break
            
            return comments
        except Exception as e:
            st.warning(f"⚠️ Error initializing comments request: {str(e)}")
            return []

    def search_videos(self, query, max_results=50):
        """Search for YouTube videos with given query"""
        try:
            search_response = self.youtube_api.search().list(
                q=query,
                part='id,snippet',
                maxResults=max_results,
                type='video',
                order='relevance'
            ).execute()
            
            videos = []
            for item in search_response.get('items', []):
                if item['id']['kind'] == 'youtube#video':
                    video_id = item['id']['videoId']
                    video_details = self.get_video_details(video_id)
                    if video_details:
                        videos.append(video_details)
            return videos
        except Exception as e:
            st.write(f"⚠️ Error searching videos: {str(e)}")
            return []

    def search_channels(self, query: str, max_results: int = 5):
        """Search for YouTube channels with given query"""
        try:
            search_response = self.youtube_api.search().list(
                q=query,
                part='id,snippet',
                maxResults=max_results,
                type='channel'
            ).execute()
            
            channels = []
            for item in search_response.get('items', []):
                if item['id']['kind'] == 'youtube#channel':
                    channel_id = item['id']['channelId']
                    channel_details = self.get_channel_details(channel_id)
                    if channel_details:
                        channels.append(channel_details)
            return channels
        except Exception as e:
            st.error(f"Error searching channels: {str(e)}")
            return []

    def get_channel_details(self, channel_id: str):
        """Get detailed information about a YouTube channel"""
        try:
            channel_response = self.youtube_api.channels().list(
                part='snippet,statistics,brandingSettings',
                id=channel_id
            ).execute()
            
            if not channel_response['items']:
                return None
                
            channel_data = channel_response['items'][0]
            return {
                'channel_id': channel_id,
                'title': channel_data['snippet']['title'],
                'description': channel_data['snippet']['description'],
                'custom_url': channel_data['snippet'].get('customUrl', ''),
                'thumbnail': channel_data['snippet']['thumbnails'].get('high', {}).get('url', ''),
                'subscriber_count': int(channel_data['statistics'].get('subscriberCount', 0)),
                'video_count': int(channel_data['statistics'].get('videoCount', 0)),
                'view_count': int(channel_data['statistics'].get('viewCount', 0)),
                'published_at': channel_data['snippet']['publishedAt']
            }
        except Exception as e:
            st.error(f"Error fetching channel details: {str(e)}")
            return None

    def get_channel_playlists(self, channel_id: str, max_results: int = 50):
        """Get all playlists for a channel"""
        try:
            playlists = []
            request = self.youtube_api.playlists().list(
                part='snippet,contentDetails',
                channelId=channel_id,
                maxResults=max_results
            )
            
            while request:
                response = request.execute()
                for item in response['items']:
                    playlists.append({
                        'id': item['id'],
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'],
                        'video_count': item['contentDetails']['itemCount'],
                        'thumbnail': item['snippet']['thumbnails'].get('high', {}).get('url', ''),
                        'published_at': item['snippet']['publishedAt']
                    })
                    
                request = self.youtube_api.playlists().list_next(request, response)
                
            return playlists
        except Exception as e:
            st.error(f"Error fetching channel playlists: {str(e)}")
            return []

    def get_video_details(self, video_id):
        """Get video details from YouTube API"""
        if not video_id:
            return None
        
        try:
            video_response = self.youtube_api.videos().list(
                part='snippet,statistics,contentDetails',
                id=video_id
            ).execute()

            if not video_response['items']:
                return None

            video_data = video_response['items'][0]
            
            # Check if comments are enabled by attempting to fetch them
            try:
                comments = self.youtube_api.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=1,
                    textFormat="plainText"
                ).execute()
                comments_enabled = True
                all_comments = self.get_all_comments(video_id)
            except Exception as e:
                comments_enabled = "commentsDisabled" not in str(e)
                all_comments = []
            
            return {
                'video_id': video_id,
                'title': video_data['snippet']['title'],
                'description': video_data['snippet']['description'],
                'views': int(video_data['statistics'].get('viewCount', 0)),
                'likes': int(video_data['statistics'].get('likeCount', 0)),
                'dislikes': int(video_data['statistics'].get('dislikeCount', 0)),
                'comments_count': int(video_data['statistics'].get('commentCount', 0)),
                'duration': video_data['contentDetails'].get('duration', 'Unknown'),
                'categoryId': video_data['snippet'].get('categoryId', 'Unknown'),
                'tags': video_data['snippet'].get('tags', []),
                'comments': all_comments,
                'comments_enabled': comments_enabled,
                'publishedAt': video_data['snippet'].get('publishedAt', ''),
                'channelTitle': video_data['snippet'].get('channelTitle', '')
            }
        except Exception as e:
            st.write(f"⚠️ Error fetching video details: {str(e)}")
            return None