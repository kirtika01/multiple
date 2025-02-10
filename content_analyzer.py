import streamlit as st
import re
import json
import pandas as pd
from typing import List, Dict
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

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
]}}"""
}

BATCH_SIZE = 20  

class ContentAnalyzer:
    def __init__(self, api_client):
        self.api_client = api_client
    
    def clean_json_response(self, response):
        """Clean and extract JSON from Gemini response"""
        try:
            response = response.strip()
            if '```json' in response:
                response = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                response = response.split('```')[1].split('```')[0]
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)
            
            return json.loads(response)
        except Exception:
            return None

    def analyze_comment_batch(self, comments: List[Dict]) -> List[Dict]:
        """Analyze a batch of comments"""
        try:
            comments_text = "\n".join([f"- {comment['text']}" for comment in comments])
            prompt = PROMPTS['batch_sentiment'].format(comments_text=comments_text)
            response = self.api_client.gemini_model.predict(prompt)
            analysis = self.clean_json_response(response)
            
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
        except Exception:
            return []

    def analyze_video_content(self, title, description):
        """Analyze video content with separate focused prompts"""
        try:
            
            subject_prompt = PROMPTS['content_subject'].format(title=title, description=description)
            subject_response = self.api_client.gemini_model.predict(subject_prompt)
            subject_analysis = self.clean_json_response(subject_response) or {"subject": "Unknown", "subtopic": "Unknown"}

            difficulty_prompt = PROMPTS['content_difficulty'].format(title=title, description=description)
            difficulty_response = self.api_client.gemini_model.predict(difficulty_prompt)
            difficulty_analysis = self.clean_json_response(difficulty_response) or {
                "difficulty_level": "Unknown",
                "target_audience": "Unknown",
                "prerequisites": []
            }

            concepts_prompt = PROMPTS['content_concepts'].format(title=title, description=description)
            concepts_response = self.api_client.gemini_model.predict(concepts_prompt)
            concepts_analysis = self.clean_json_response(concepts_response) or {"concepts": []}

            return {
                "subject": str(subject_analysis.get("subject", "Unknown")),
                "subtopic": str(subject_analysis.get("subtopic", "Unknown")),
                "difficulty_level": str(difficulty_analysis.get("difficulty_level", "Unknown")),
                "target_audience": str(difficulty_analysis.get("target_audience", "Unknown")),
                "prerequisites": [str(p) for p in difficulty_analysis.get("prerequisites", [])],
                "concepts": [str(c) for c in concepts_analysis.get("concepts", [])]
            }
        except Exception as e:
            st.write(f"⚠️ Error in content analysis: {str(e)}")
            return None

    def display_sentiment_analysis(self, video_data):
        """Display sentiment analysis results in a user-friendly format"""
        if not video_data.get('comments'):
            st.write("No comments available for analysis")
            return {'positive': 0, 'negative': 0}

        top_comments = sorted(video_data['comments'], key=lambda x: x['likes'], reverse=True)[:100]
  
        all_analyses = []
        sentiments = {'positive': 0, 'negative': 0}
        
        with st.spinner(f"Analyzing top {len(top_comments)} most liked comments..."):
            for i in range(0, len(top_comments), BATCH_SIZE):
                batch = top_comments[i:i + BATCH_SIZE]
                batch_analyses = self.analyze_comment_batch(batch)
                all_analyses.extend(batch_analyses)
              
                for analysis in batch_analyses:
                    sent = analysis['sentiment']
                    if sent not in ['positive', 'negative']:
                        sent = 'negative'
                    sentiments[sent] += 1
      
        st.subheader("Comment Sentiment Analysis")

        video_key = "_".join(video_data['title'].lower().split()[:3])

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
            title=f"Sentiment Distribution - {video_data['title'][:50]}..."
        )
 
        fig.update_traces(
            textposition='outside',
            textfont=dict(size=14),
            width=0.6,  
        )
        fig.update_layout(
            yaxis_title="Number of Comments",
            showlegend=False,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"sentiment_chart_{video_key}")

        st.subheader("Most Impactful Comments")
  
        grouped_comments = {
            'positive': sorted(
                [c for c in all_analyses if c['sentiment'] == 'positive'],
                key=lambda x: x['likes'],
                reverse=True
            )[:5],  
            'negative': sorted(
                [c for c in all_analyses if c['sentiment'] == 'negative'],
                key=lambda x: x['likes'],
                reverse=True
            )[:5]
        }
 
        tabs = st.tabs(["Most Liked Positive", "Most Liked Negative"])
        
        for tab, (sentiment, comments) in zip(tabs, grouped_comments.items()):
            with tab:
                if comments:
                   
                    video_key = "_".join(video_data['title'].lower().split()[:3]) 
                    for i, comment in enumerate(comments, 1):
                        st.markdown(f"**Comment #{i}** ({comment['likes']:,} likes)")
                        st.text_area("", comment['text'], height=100,
                                   key=f"{video_key}_{sentiment}_{i}")
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.caption(f"Confidence: {comment['confidence']}",
                                     help="Model's confidence in sentiment classification")
                        with col2:
                            if comment['key_phrases']:
                                st.caption(f"Key points: {', '.join(comment['key_phrases'])}")
                        st.divider()
                else:
                    st.info(f"No {sentiment} comments found")
        
        return sentiments