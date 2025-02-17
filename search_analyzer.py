import numpy as np
from sentence_transformers import SentenceTransformer
from datetime import datetime
import streamlit as st

class SearchAnalyzer:
    def __init__(self):
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the sentence transformer model"""
        try:
            with st.spinner("Loading language model..."):
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            st.error(f"Error initializing language model: {str(e)}")
    
    def _get_video_embedding(self, video):
        """Generate embedding for video content"""
        if not self.model:
            self._initialize_model()
            
        # Combine title, description, and tags for richer context
        content = f"{video['title']} {video['description']} {' '.join(video['tags'])}"
        return self.model.encode(content)
    
    def _find_relevant_segments(self, transcript: str, query: str) -> list:
        """Find transcript segments most relevant to the search query with timestamps"""
        if not transcript or not query:
            return []
            
        # Skip if transcript is None or empty string
        if transcript is None or not isinstance(transcript, str) or not transcript.strip():
            return []
            
        try:
            # Split transcript into segments with timestamps
            segments = []
            current_timestamp = 0
            current_text = []
            
            for line in transcript.split('\n'):
                if not line.strip():
                    continue
                    
                # Extract timestamp and text
                if '[' in line and ']' in line:
                    # If we have collected text, add it as a segment
                    if current_text:
                        segments.append({
                            'timestamp': current_timestamp,
                            'text': ' '.join(current_text),
                            'seconds': self._timestamp_to_seconds(current_timestamp)
                        })
                        current_text = []
                    
                    # Get new timestamp and text
                    parts = line.split(']', 1)
                    timestamp = parts[0].strip('[')
                    text = parts[1].strip() if len(parts) > 1 else ""
                    
                    current_timestamp = timestamp
                    if text:
                        current_text.append(text)
                else:
                    current_text.append(line.strip())
            
            # Add final segment if there's remaining text
            if current_text:
                segments.append({
                    'timestamp': current_timestamp,
                    'text': ' '.join(current_text),
                    'seconds': self._timestamp_to_seconds(current_timestamp)
                })
            
            # Find segments most relevant to query
            relevant_segments = []
            query_embedding = self.model.encode(query)
            
            for segment in segments:
                segment_embedding = self.model.encode(segment['text'])
                similarity = np.dot(query_embedding, segment_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(segment_embedding)
                )
                
                if similarity > 0.5:  # Only include highly relevant segments
                    relevant_segments.append({
                        'timestamp': segment['timestamp'],
                        'text': segment['text'],
                        'similarity': similarity,
                        'seconds': segment['seconds']
                    })
            
            # Sort by similarity and return top 3
            relevant_segments.sort(key=lambda x: x['similarity'], reverse=True)
            return relevant_segments[:3]
            
        except Exception as e:
            st.warning(f"Error finding relevant segments: {str(e)}")
            return []
    
    def _timestamp_to_seconds(self, timestamp: str) -> int:
        """Convert MM:SS format timestamp to seconds"""
        try:
            parts = timestamp.split(':')
            if len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            return 0
        except:
            return 0
            
    def _calculate_engagement_score(self, video):
        """Calculate engagement score giving higher weight to recency"""
        try:
            views = video['views']
            likes = video['likes']
            
            # Calculate base engagement (likes/views ratio)
            engagement = (likes / views) if views > 0 else 0
            
            # Strong recency boost for newer videos
            published_date = datetime.strptime(video['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
            days_since_published = (datetime.now() - published_date).days
            recency_boost = 2 / (1 + np.log1p(days_since_published))  # Doubled recency impact
            
            # Combine metrics with higher weight on recency
            return 0.4 * engagement + 0.6 * recency_boost
            
        except Exception:
            return 0
    
    def rank_videos(self, query, videos, top_k=None):
        """Rank and return top 3 most relevant and recent videos"""
        if not videos:
            return []
            
        try:
            # Get query embedding
            query_embedding = self.model.encode(query)
            
            # Calculate scores for each video
            ranked_videos = []
            for video in videos:
                # Calculate semantic similarity
                video_embedding = self._get_video_embedding(video)
                similarity = np.dot(query_embedding, video_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(video_embedding)
                )
                
                # Calculate engagement score (includes recency)
                engagement_score = self._calculate_engagement_score(video)
                
                # Published date for reference
                published_date = datetime.strptime(video['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
                
                # Combined score (50% similarity, 50% engagement+recency)
                final_score = 0.5 * similarity + 0.5 * engagement_score
                
                ranked_videos.append({
                    'video': video,
                    'similarity': similarity,
                    'engagement_score': engagement_score,
                    'final_score': final_score,
                    'published_date': published_date.strftime("%Y-%m-%d"),
                    'relevant_segments': self._find_relevant_segments(video.get('transcript', ''), query)
                })
            
            # Always return top 3 videos
            ranked_videos.sort(key=lambda x: x['final_score'], reverse=True)
            return ranked_videos[:3]
            
        except Exception as e:
            st.error(f"Error ranking videos: {str(e)}")
            return []