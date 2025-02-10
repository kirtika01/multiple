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
            
            return comments
        except Exception as e:
            st.write(f"⚠️ Error fetching comments: {str(e)}")
            return []
    
    def get_all_comments(self, video_id):
        """Fetch all comments for a video"""
        try:
            comments = []
            request = self.youtube_api.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,  # Max allowed by API
                textFormat="plainText"
            )
            
            # Keep fetching until no more comments or rate limit
            while request:
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
            
            return comments
        except Exception as e:
            st.write(f"⚠️ Error fetching comments: {str(e)}")
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
            comments = self.get_all_comments(video_id)
            
            return {
                'title': video_data['snippet']['title'],
                'description': video_data['snippet']['description'],
                'views': int(video_data['statistics'].get('viewCount', 0)),
                'likes': int(video_data['statistics'].get('likeCount', 0)),
                'dislikes': int(video_data['statistics'].get('dislikeCount', 0)),
                'comments_count': int(video_data['statistics'].get('commentCount', 0)),
                'duration': video_data['contentDetails'].get('duration', 'Unknown'),
                'categoryId': video_data['snippet'].get('categoryId', 'Unknown'),
                'tags': video_data['snippet'].get('tags', []),
                'comments': comments
            }
        except Exception as e:
            st.write(f"⚠️ Error fetching video details: {str(e)}")
            return None