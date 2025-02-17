import streamlit as st
import re
import json
import pandas as pd
from typing import List, Dict
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import os
import whisper
import time

PROMPTS = {
    'content_subject': """Analyze this educational video's title and description. Focus only on the subject area:
Title: {title}
Description: {description}
Return ONLY a JSON object in this format (no other text):
{{"subject": "main subject area", "subtopic": "specific subtopic or branch"}}""",

    'content_difficulty': """For an educational video, analyze:
Title: {title}
Description: {description}
Return ONLY a JSON object in this format (no other text):
{{"difficulty_level": "beginner/intermediate/advanced", "target_audience": "intended audience", "prerequisites": ["required", "background", "knowledge"]}}""",

    'content_concepts': """From this educational video's content:
Title: {title}
Description: {description}
Return ONLY a JSON object in this format (no other text):
{{"concepts": ["list", "of", "key", "concepts"]}}""",

    'batch_sentiment': """Analyze these YouTube comments and classify each as strictly positive or negative (no neutral):
Comments:
{comments_text}

Return ONLY a JSON object in this format (no other text):
{{"results": [
    {{"text": "comment text here", "sentiment": "positive/negative", "confidence": "high/medium/low", "key_phrases": ["key", "phrases"]}},
    ...
]}}""",

    'transcript_summary': """You are analyzing a video transcript to create an educational summary. Focus on explaining concepts clearly and organizing information logically.

Context: This is a transcript from an educational video.

Transcript:
{transcript_text}

Create a comprehensive analysis that includes:
1. A summary of the main content
2. Key points and concepts covered
3. How the content is structured
4. What learners will gain

Return ONLY a JSON object in this format (no other text):
{{
    "summary": "Write a clear, detailed summary in 2-3 paragraphs. Focus on explaining the main concepts and how they connect. Make it easy to understand for someone new to the topic.",
    "key_points": [
        "List 5-7 most important concepts or ideas",
        "Make each point specific and actionable",
        "Focus on what learners need to understand"
    ],
    "chapter_breakdown": [
        {{"title": "Topic Name", "content": "Explain what this section covers and why it's important"}},
        {{"title": "Next Topic", "content": "Continue for each major section..."}}
    ],
    "learning_outcomes": [
        "List 3-5 specific things learners will understand after watching",
        "Make these practical and measurable"
    ]
}}

Your response should be clear, educational, and well-structured."""
}

BATCH_SIZE = 20

class ContentAnalyzer:
    def __init__(self, api_client):
        self.api_client = api_client
        self.whisper_model = None
        self._initialize_whisper()

    def _safe_api_call(self, prompt: str, max_retries: int = 3, initial_delay: int = 3) -> dict:
        """Make API calls with retry logic and enhanced error handling"""
        last_error = None
        delay = initial_delay
        response = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    st.warning(f"Attempt {attempt + 1}/{max_retries}: Retrying after {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                
                # Make the API call with progress indication
                with st.spinner("Making API request..."):
                    response = self.api_client.gemini_model.predict(prompt)
                    
                if not response:
                    raise Exception("Empty response from API")
                
                # Show parsing attempt
                with st.spinner("Parsing response..."):
                    st.text("Attempting to clean and parse JSON response...")
                    result = self.clean_json_response(response)
                    
                    if result:
                        if attempt > 0:
                            st.success("✅ Successfully parsed response after retry")
                        return result
                    
                    # If we get here, clean_json_response returned None
                    raise Exception("Failed to extract valid JSON structure")
                
            except Exception as e:
                last_error = str(e)
                if attempt == max_retries - 1:
                    st.error(f"❌ All attempts failed. Last error: {last_error}")
                    # Return a safe fallback response with error context
                    return {
                        "subject": "Analysis Error",
                        "subtopic": "API Processing Failed",
                        "difficulty_level": "Unavailable",
                        "target_audience": "Not available",
                        "prerequisites": [],
                        "concepts": [f"Error: {last_error}", "Please try again later"],
                        "summary": f"Analysis failed: {last_error}",
                        "key_points": ["Unable to process content"],
                        "chapter_breakdown": [],
                        "learning_outcomes": []
                    }

    def clean_json_response(self, response):
        """Clean and extract JSON from Gemini response with advanced error handling"""
        if not response:
            st.warning("Empty response received")
            return None

        try:
            # Find the most promising JSON object in the response
            def extract_json_candidate(text):
                # First try to find JSON in code blocks
                if '```' in text:
                    blocks = text.split('```')
                    for block in blocks:
                        if '{' in block and '}' in block:
                            text = block
                            break
                
                # Find the outermost JSON object
                start = text.find('{')
                end = text.rfind('}')
                if start >= 0 and end > start:
                    return text[start:end + 1]
                return None

            json_str = extract_json_candidate(response)
            if not json_str:
                st.warning("No JSON object found in response")
                return None

            # Advanced JSON cleaning
            def clean_json_string(s):
                # Remove control characters and normalize whitespace
                s = "".join(char for char in s if ord(char) >= 32 or char in "\n\r\t")
                s = re.sub(r'\s+', ' ', s)
                
                # Fix common JSON formatting issues
                s = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', s)  # Quote unquoted keys
                s = s.replace("'", '"')  # Replace single quotes with double quotes
                s = s.replace('None', 'null').replace('True', 'true').replace('False', 'false')
                
                # Fix trailing commas
                s = re.sub(r',\s*([}\]])', r'\1', s)
                
                # Fix newlines in strings
                s = re.sub(r'(?<!\\)\\n', ' ', s)  # Replace \n with space
                s = re.sub(r'[\n\r]+', ' ', s)     # Replace actual newlines with space
                
                # Fix missing commas between elements
                s = re.sub(r'}\s*{', '},{', s)
                s = re.sub(r']\s*{', '],{', s)
                s = re.sub(r'}\s*\[', '},\[', s)
                s = re.sub(r']\s*\[', '],\[', s)
                
                # Remove any remaining invalid escape sequences
                s = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', '', s)
                
                return s.strip()

            # Clean the JSON string
            json_str = clean_json_string(json_str)

            try:
                # Try to parse the cleaned JSON
                result = json.loads(json_str)
                if not isinstance(result, dict):
                    st.warning("Parsed JSON is not an object")
                    return None
                    
                # Basic validation that we have a non-empty dict
                if result and isinstance(result, dict) and len(result) > 0:
                    return result
                else:
                    st.warning("Invalid JSON structure: empty or not an object")
                    return None
                    
            except json.JSONDecodeError as e:
                st.warning(f"JSON parsing error: {str(e)}\nAttempted to parse: {json_str[:100]}...")
                return None
                
        except Exception as e:
            st.warning(f"Error processing response: {str(e)}")
            return None

    def _initialize_whisper(self):
        """Initialize Whisper model"""
        try:
            with st.spinner("Loading Whisper model..."):
                self.whisper_model = whisper.load_model("base")
        except Exception as e:
            st.error(f"Error initializing Whisper model: {str(e)}")

    def _download_audio(self, video_id: str) -> str:
        """Download audio from YouTube video"""
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                }],
                'outtmpl': f'temp_{video_id}.%(ext)s'
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f'https://www.youtube.com/watch?v={video_id}'])
                return f'temp_{video_id}.wav'
        except Exception as e:
            st.error(f"Error downloading audio: {str(e)}")
            return None

    def _transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio using Whisper"""
        try:
            if not self.whisper_model:
                self._initialize_whisper()
            
            with st.spinner("Transcribing audio with Whisper..."):
               
                initial_result = self.whisper_model.transcribe(
                    audio_path,
                    verbose=False
                )
                
                detected_lang = initial_result.get('language', '')
                
                
                if detected_lang not in ['hi', 'en']:
                    st.info("Transcribing in English as default language")
                    result = self.whisper_model.transcribe(
                        audio_path,
                        language='en',
                        verbose=False
                    )
                else:
                    
                    result = initial_result
                
                if not result or 'segments' not in result:
                    return None

                text_segments = []
                for segment in result['segments']:
                    minutes = int(segment['start'] // 60)
                    seconds = int(segment['start'] % 60)
                    timestamp = f"{minutes:02d}:{seconds:02d}"
                    text_segments.append(f"[{timestamp}] {segment['text'].strip()}")

                return "\n".join(text_segments)
        except Exception as e:
            st.error(f"Error transcribing audio: {str(e)}")
            return None
        finally:
            try:
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except:
                pass

    def get_video_transcript(self, video_id: str, language: str = None) -> str:
        """Get transcript for a YouTube video with language selection"""
        try:
            # Let user select language if not specified
            if language is None:
                language = st.selectbox(
                    "Select transcript language",
                    options=['en', 'hi'],
                    format_func=lambda x: "English" if x == 'en' else "Hindi",
                    key=f"lang_select_{video_id}"
                )

            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                transcript = None
                
                try:
                    # Try to get transcript in selected language
                    transcript = transcript_list.find_transcript([language])
                except:
                    # Fall back to other language if selected one isn't available
                    fallback_lang = 'en' if language == 'hi' else 'hi'
                    try:
                        transcript = transcript_list.find_transcript([fallback_lang])
                        st.warning(f"Transcript not available in {language}. Falling back to {fallback_lang}")
                    except:
                        raise Exception("No Hindi or English transcript found")
                
                transcript_list = transcript.fetch()
                transcript_text = "\n".join(
                    f"[{int(entry['start']//60):02d}:{int(entry['start']%60):02d}] {entry['text']}"
                    for entry in transcript_list
                )
                return transcript_text
            except:
                
                st.info("Using Whisper for audio transcription...")
                audio_path = self._download_audio(video_id)
                if audio_path:
                    transcript_text = self._transcribe_audio(audio_path)
                    if transcript_text:
                        return transcript_text
                return None
        except Exception as e:
            st.error(f"Could not fetch transcript: {str(e)}")
            return None

    def analyze_transcript(self, transcript_text: str) -> Dict:
        """Analyze video transcript and generate summary"""
        try:
            
            clean_text = " ".join(
                line.split("] ")[1] if "] " in line else line
                for line in transcript_text.split("\n")
                if line.strip()
            )

           
            prompt = PROMPTS['transcript_summary'].format(transcript_text=clean_text)
            analysis = self._safe_api_call(prompt)

            if not analysis:
                return {
                    "summary": "Could not generate summary",
                    "key_points": [],
                    "chapter_breakdown": [],
                    "learning_outcomes": []
                }

            return {
                "summary": analysis.get("summary", "No summary available"),
                "key_points": analysis.get("key_points", [])[:7],
                "chapter_breakdown": analysis.get("chapter_breakdown", [])[:4],
                "learning_outcomes": analysis.get("learning_outcomes", [])[:5]
            }
        except Exception as e:
            st.error(f"Error analyzing transcript: {str(e)}")
            return None

    def analyze_video_content(self, title, description):
        """Analyze video content with retries and enhanced error handling"""
        try:
            with st.spinner("Analyzing video content..."):
                # Track progress for each analysis step
                progress_text = st.empty()
                
                progress_text.text("📚 Starting content analysis...")
                
                # Analyze subject area with proper delay
                progress_text.text("🎯 Analyzing subject area...")
                subject_prompt = PROMPTS['content_subject'].format(title=title, description=description)
                subject_analysis = self._safe_api_call(subject_prompt)
                
                # Check first analysis result
                if subject_analysis.get("subject") == "Analysis Unavailable":
                    st.warning("⚠️ Initial analysis failed. Attempting to continue with remaining components...")
                
                # Continue with difficulty analysis
                progress_text.text("📊 Determining difficulty level...")
                difficulty_prompt = PROMPTS['content_difficulty'].format(title=title, description=description)
                difficulty_analysis = self._safe_api_call(difficulty_prompt)
                
                # Extract key concepts
                progress_text.text("🔑 Identifying key concepts...")
                concepts_prompt = PROMPTS['content_concepts'].format(title=title, description=description)
                concepts_analysis = self._safe_api_call(concepts_prompt)
                
                # Clear the progress indicator
                progress_text.empty()
                
                # Check overall analysis success
                failed_components = sum(
                    1 for x in [subject_analysis, difficulty_analysis, concepts_analysis]
                    if x.get("subject") == "Analysis Unavailable"
                )
                
                if failed_components > 0:
                    st.warning(f"⚠️ {failed_components} analysis components failed. Results may be incomplete.")

            return {
                "subject": str(subject_analysis.get("subject", "Unknown")),
                "subtopic": str(subject_analysis.get("subtopic", "Unknown")),
                "difficulty_level": str(difficulty_analysis.get("difficulty_level", "Unknown")),
                "target_audience": str(difficulty_analysis.get("target_audience", "Unknown")),
                "prerequisites": [str(p) for p in difficulty_analysis.get("prerequisites", [])],
                "concepts": [str(c) for c in concepts_analysis.get("concepts", [])]
            }
        except Exception as e:
            st.error(f"Error in content analysis: {str(e)}")
            return None

    def analyze_comment_batch(self, comments: List[Dict]) -> List[Dict]:
        """Analyze a batch of comments with retries"""
        try:
            comments_text = "\n".join([f"- {comment['text']}" for comment in comments])
            prompt = PROMPTS['batch_sentiment'].format(comments_text=comments_text)
            analysis = self._safe_api_call(prompt)

            if not analysis or 'results' not in analysis:
                return []

            results = []
            for comment, result in zip(comments, analysis['results']):
                results.append({
                    'text': comment['text'],
                    'sentiment': result.get('sentiment', 'negative'),
                    'confidence': result.get('confidence', 'low'),
                    'key_phrases': result.get('key_phrases', []),
                    'likes': comment['likes']
                })
            return results
        except Exception as e:
            st.error(f"Error analyzing comments: {str(e)}")
            return []

    def display_sentiment_analysis(self, video_data):
        """Display sentiment analysis results"""
        if not video_data.get('comments'):
            st.write("No comments available for analysis")
            return {'positive': 0, 'negative': 0}

        top_comments = sorted(video_data['comments'], key=lambda x: x['likes'], reverse=True)[:100]
        all_analyses = []
        sentiments = {'positive': 0, 'negative': 0}
        
        with st.spinner(f"Analyzing comments..."):
            for i in range(0, len(top_comments), BATCH_SIZE):
                batch = top_comments[i:i + BATCH_SIZE]
                batch_analyses = self.analyze_comment_batch(batch)
                all_analyses.extend(batch_analyses)
                
                for analysis in batch_analyses:
                    sent = analysis['sentiment']
                    if sent not in ['positive', 'negative']:
                        sent = 'negative'
                    sentiments[sent] += 1

        # Create a unique key using video ID and timestamp to ensure uniqueness even for same video
        video_key = f"{video_data.get('video_id', '')}_{int(time.time())}"
        sentiment_df = pd.DataFrame({
            'Sentiment': ['Positive', 'Negative'],
            'Count': [sentiments['positive'], sentiments['negative']],
            'Percentage': [
                f"{(sentiments['positive']/len(all_analyses)*100):.1f}%" if all_analyses else "0%",
                f"{(sentiments['negative']/len(all_analyses)*100):.1f}%" if all_analyses else "0%"
            ]
        })

        fig = px.bar(
            sentiment_df,
            x='Sentiment',
            y='Count',
            text='Percentage',
            title=f"Sentiment Distribution"
        )

        fig.update_traces(
            textposition='outside',
            textfont=dict(size=14),
            width=0.6
        )
        fig.update_layout(
            yaxis_title="Number of Comments",
            showlegend=False,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"sentiment_chart_{video_key}")

        return sentiments