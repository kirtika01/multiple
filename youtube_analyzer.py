import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
from api_client import APIClient
from content_analyzer import ContentAnalyzer
from video_analyzer import VideoAnalyzer

# Load environment variables
load_dotenv()

# Subject relationships configuration
RELATED_SUBJECTS = {
    "machine learning": ["computer science", "artificial intelligence", "data science"],
    "computer science": ["machine learning", "artificial intelligence", "data science"],
    "artificial intelligence": ["machine learning", "computer science", "data science"],
    "data science": ["machine learning", "computer science", "artificial intelligence"],
    "mathematics": ["statistics", "algebra", "calculus", "linear algebra"],
    "statistics": ["mathematics", "data science", "probability"],
    "physics": ["mathematics", "engineering"],
    "chemistry": ["biochemistry", "chemical engineering"],
}

def check_domain_compatibility(videos_content):
    """Check if all videos are from compatible domains"""
    if not videos_content:
        return True, []
    
    domains = []
    mismatched = []
    main_subject = videos_content[0]['subject'].lower()
    
    for i, content in enumerate(videos_content):
        current_subject = content['subject'].lower()
        domains.append(current_subject)
        
        # Check if current subject is related to main subject
        if not (current_subject == main_subject or
                current_subject in RELATED_SUBJECTS.get(main_subject, []) or
                main_subject in RELATED_SUBJECTS.get(current_subject, [])):
            mismatched.append({
                'index': i,
                'subject': current_subject,
                'main_subject': main_subject
            })
    
    return len(mismatched) == 0, mismatched

def calculate_comparative_scores(video_data, all_videos_data):
    """Calculate comparative scores against other videos"""
    # Calculate averages with proper handling of zero values
    total_videos = len(all_videos_data)
    avg_views = sum(v['views'] for v in all_videos_data) / total_videos if total_videos > 0 else 1
    avg_likes = sum(v['likes'] for v in all_videos_data) / total_videos if total_videos > 0 else 1
    avg_comments = sum(v['comments_count'] for v in all_videos_data) / total_videos if total_videos > 0 else 1
    
    # Calculate ratios with proper rounding
    return {
        'view_ratio': round(video_data['views'] / avg_views, 2) if avg_views > 0 else 0,
        'likes_ratio': round(video_data['likes'] / avg_likes, 2) if avg_likes > 0 else 0,
        'comments_ratio': round(video_data['comments_count'] / avg_comments, 2) if avg_comments > 0 else 0
    }

def calculate_engagement_score(video_data):
    """Calculate engagement score based on likes and comments relative to views"""
    views = video_data['views'] if video_data['views'] > 0 else 1
    # Calculate individual ratios with proper rounding
    likes_ratio = round((video_data['likes'] / views) * 100, 2)
    comments_ratio = round((video_data['comments_count'] / views) * 100, 2)
    # Return average score rounded to 2 decimal places
    return round((likes_ratio + comments_ratio) / 2, 2)

def main():
    st.title("YouTube Educational Video Analyzer")

    # Initialize API client
    api_client = APIClient()
    if not api_client.youtube_api or not api_client.gemini_model:
        st.write("""
        To get started:
        1. Create a .env file in the same directory as this script
        2. Add your API keys:
           ```
           YOUTUBE_API_KEY=your_youtube_api_key_here
           GOOGLE_API_KEY=your_google_api_key_here
           ```
        3. Restart the application
        """)
        return

    # Initialize analyzers
    content_analyzer = ContentAnalyzer(api_client)

    # Let user select number of videos to analyze
    num_videos = st.slider("Select number of videos to analyze", min_value=2, max_value=10, value=3,
                          help="Choose how many videos you want to compare (between 2 and 10)")
    
    st.write(f"Enter {num_videos} YouTube video URLs of similar educational content")

    # Create dynamic input fields based on user selection
    new_urls = []
    for i in range(num_videos):
        url = st.text_input(f"Video URL {i+1}", key=f"url_{i}")
        if url:
            # Check for duplicates
            if VideoAnalyzer.is_duplicate_url(url, new_urls):
                st.write(f"⚠️ Video {i+1}: This video has already been added. Please enter a different URL.")
                continue
            new_urls.append(url)

    if st.button("Analyze Videos") and len(new_urls) == num_videos:
        with st.spinner("Collecting video information..."):
            videos_data = []
            videos_content_analysis = []
            all_sentiments = []

            # Collect video details and analyze content
            for url in new_urls:
                video_id = VideoAnalyzer.extract_video_id(url)
                if not video_id:
                    st.write(f"⚠️ Invalid YouTube URL: {url}")
                    return

                video_data = api_client.get_video_details(video_id)
                if not video_data:
                    st.write(f"⚠️ Could not fetch video details for: {url}")
                    return

                # Add content analysis with error handling
                try:
                    content_analysis = content_analyzer.analyze_video_content(
                        video_data['title'],
                        video_data['description']
                    ) or {
                        "subject": "Unknown",
                        "subtopic": "Unknown",
                        "concepts": [],
                        "difficulty_level": "Unknown",
                        "prerequisites": [],
                        "target_audience": "Unknown"
                    }
                    videos_content_analysis.append(content_analysis)
                    videos_data.append(video_data)
                except Exception as e:
                    st.write(f"⚠️ Error analyzing video content: {str(e)}")
                    return

            # Check domain compatibility first
            domains_compatible, mismatched = check_domain_compatibility(videos_content_analysis)
            if not domains_compatible:
                st.error("⚠️ Domain Mismatch Detected!")
                for mismatch in mismatched:
                    st.warning(f"Video {mismatch['index'] + 1} ({mismatch['subject']}) appears to be from a different domain than the main subject ({mismatch['main_subject']})")
                st.error("Analysis cannot proceed with videos from different domains. Please select videos from similar or related subjects.")
                return

            # Display content analysis comparison
            st.header("Video Content Analysis")
            content_comparison = pd.DataFrame([{
                'Title': data['title'],
                'Subject': analysis['subject'],
                'Subtopic': analysis['subtopic'],
                'Difficulty': analysis['difficulty_level'],
                'Target Audience': analysis['target_audience'],
                'Prerequisites': ', '.join(analysis['prerequisites'])
            } for data, analysis in zip(videos_data, videos_content_analysis)])

            st.dataframe(content_comparison)

            # Create separate view count visualization
            st.header("View Count Analysis")
            fig_views = go.Figure(data=[
                go.Bar(
                    x=[data['title'] for data in videos_data],
                    y=[data['views'] for data in videos_data],
                    text=[f"{data['views']:,}" for data in videos_data],
                    textposition='auto',
                )
            ])
            
            fig_views.update_layout(
                title="Total Views per Video",
                xaxis_title="Videos",
                yaxis_title="Views",
                height=400,
                showlegend=False
            )
            
            st.plotly_chart(fig_views, use_container_width=True)

            # Create engagement metrics visualization
            st.header("Engagement Analysis")
            engagement_metrics = pd.DataFrame({
                'Video': [data['title'] for data in videos_data],
                'Likes': [data['likes'] for data in videos_data],
                'Comments': [data['comments_count'] for data in videos_data]
            })

            fig_engagement = px.bar(
                engagement_metrics,
                x='Video',
                y=['Likes', 'Comments'],
                barmode='group',
                title="Likes and Comments Comparison",
                labels={'value': 'Count', 'variable': 'Metric'}
            )

            st.plotly_chart(fig_engagement, use_container_width=True)

            # Add engagement ratio visualization with proper formatting
            ratios = []
            for data in videos_data:
                views = data['views'] if data['views'] > 0 else 1
                engagement_metrics = {
                    'Video': data['title'],
                    'Likes/Views %': round((data['likes'] / views) * 100, 2),
                    'Comments/Views %': round((data['comments_count'] / views) * 100, 2)
                }
                
                # Format numbers with proper rounding
                for key in ['Likes/Views %', 'Comments/Views %']:
                    engagement_metrics[key] = float(f"{engagement_metrics[key]:.2f}")
                
                ratios.append(engagement_metrics)

            ratio_df = pd.DataFrame(ratios)
            fig_ratios = px.bar(
                ratio_df,
                x='Video',
                y=['Likes/Views %', 'Comments/Views %'],
                barmode='group',
                title="Engagement Ratios (% of Views)",
                labels={'value': 'Percentage', 'variable': 'Metric'}
            )

            st.plotly_chart(fig_ratios, use_container_width=True)

            # Display sentiment analysis
            st.header("Comments Analysis")
            for i, video_data in enumerate(videos_data):
                with st.expander(f"Video {i+1}: {video_data['title']}", expanded=True):
                    sentiments = content_analyzer.display_sentiment_analysis(video_data)
                    if sentiments:
                        all_sentiments.append({
                            'title': video_data['title'],
                            'sentiments': {
                                'positive': sentiments.get('positive', 0),
                                'negative': sentiments.get('negative', 0)
                            }
                        })

            # Create sentiment comparison
            if all_sentiments:
                st.header("Sentiment Comparison")
                sentiment_data = []
                for data in all_sentiments:
                    total = sum(data['sentiments'].values())
                    pos_pct = round((data['sentiments']['positive'] / total * 100), 2) if total > 0 else 0
                    neg_pct = round((data['sentiments']['negative'] / total * 100), 2) if total > 0 else 0
                    
                    sentiment_data.append({
                        'Video': data['title'],
                        'Total Comments': total,
                        'Positive %': pos_pct,
                        'Negative %': neg_pct,
                        'Net Sentiment': pos_pct - neg_pct
                    })

                sentiment_df = pd.DataFrame(sentiment_data)
                
                # Horizontal stacked bar chart for sentiment distribution
                fig_sentiment = go.Figure()
                
                fig_sentiment.add_trace(go.Bar(
                    name='Positive',
                    x=sentiment_df['Positive %'],
                    y=sentiment_df['Video'],
                    orientation='h',
                    text=[f"{x:.1f}%" for x in sentiment_df['Positive %']],
                    textposition='auto',
                    marker_color='green'
                ))
                
                fig_sentiment.add_trace(go.Bar(
                    name='Negative',
                    x=sentiment_df['Negative %'],
                    y=sentiment_df['Video'],
                    orientation='h',
                    text=[f"{x:.1f}%" for x in sentiment_df['Negative %']],
                    textposition='auto',
                    marker_color='red'
                ))

                fig_sentiment.update_layout(
                    barmode='stack',
                    title="Sentiment Distribution by Video",
                    xaxis_title="Percentage of Comments",
                    yaxis_title="Videos",
                    height=400,
                    showlegend=True,
                    yaxis={'categoryorder': 'total ascending'},
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                st.plotly_chart(fig_sentiment, use_container_width=True)

            # Video recommendation with detailed comparison
            st.header("Video Recommendation")
            video_scores = []
            
            for i, (data, analysis) in enumerate(zip(videos_data, videos_content_analysis)):
                # Calculate scores
                engagement = calculate_engagement_score(data)
                comparative = calculate_comparative_scores(data, videos_data)
                sentiment_score = sentiment_df.iloc[i]['Net Sentiment'] if len(sentiment_df) > i else 0
                
                # Calculate weighted scores with proper rounding
                engagement_subscore = round(engagement * 0.3, 2)
                sentiment_subscore = round(max(0, sentiment_score) * 0.4, 2)
                
                # Calculate comparative subscores individually for clarity
                view_subscore = round(comparative['view_ratio'] * 0.1, 2)
                likes_subscore = round(comparative['likes_ratio'] * 0.1, 2)
                comments_subscore = round(comparative['comments_ratio'] * 0.1, 2)
                
                comparative_subscore = view_subscore + likes_subscore + comments_subscore
                
                # Calculate final score with proper rounding
                total_score = round(engagement_subscore + sentiment_subscore + comparative_subscore, 2)
                
                video_scores.append({
                    'title': data['title'],
                    'total_score': total_score,
                    'content': analysis,
                    'metrics': {
                        'engagement': engagement,
                        'sentiment': sentiment_score,
                        'comparative': comparative
                    }
                })
            
            # Sort videos by total score
            video_scores.sort(key=lambda x: x['total_score'], reverse=True)
            best_video = video_scores[0] if video_scores else None
            
            if best_video:
                st.subheader(f"📚 Recommended Video: {best_video['title']}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Engagement Score", f"{best_video['metrics']['engagement']:.2f}%")
                with col2:
                    st.metric("Sentiment Score", f"{best_video['metrics']['sentiment']:.2f}")
                with col3:
                    st.metric("Difficulty", best_video['content']['difficulty_level'])

                st.markdown("### Why This Video Is Recommended")
                
                # Content Analysis
                st.markdown("#### Content Quality")
                st.markdown(f"""
                - **Subject Area**: {best_video['content']['subject']}
                - **Difficulty Level**: {best_video['content']['difficulty_level']}
                - **Target Audience**: {best_video['content']['target_audience']}
                - **Prerequisites**: {', '.join(best_video['content']['prerequisites']) if best_video['content']['prerequisites'] else 'None'}
                - **Key Concepts**: {', '.join(best_video['content']['concepts']) if best_video['content']['concepts'] else 'None'}
                """)

                # Performance Metrics
                st.markdown("#### Performance Analysis")
                comparative = best_video['metrics']['comparative']
                st.markdown(f"""
                - **Views**: {comparative['view_ratio']:.2f}x the average
                - **Likes**: {comparative['likes_ratio']:.2f}x the average
                - **Comments**: {comparative['comments_ratio']:.2f}x the average
                - **Engagement Score**: {best_video['metrics']['engagement']:.2f}%
                - **Sentiment Score**: {best_video['metrics']['sentiment']:.2f}
                """)

    elif len(new_urls) > 0 and len(new_urls) < num_videos:
        st.write(f"⚠️ Please enter all {num_videos} video URLs for analysis")

if __name__ == "__main__":
    main()
