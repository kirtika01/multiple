import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from api_client import APIClient
from content_analyzer import ContentAnalyzer
from video_analyzer import VideoAnalyzer
from channel_analyzer import ChannelAnalyzer
from search_analyzer import SearchAnalyzer

load_dotenv()

def analyze_single_video(url, video_id, video_data, content_analyzer, summary_option, keywords_option, sentiment_option, qa_option, task_option):
    try:
        content_analysis = content_analyzer.analyze_video_content(
            video_data["title"], video_data["description"]
        ) or {
            "subject": "Unknown",
            "subtopic": "Unknown",
            "concepts": [],
            "difficulty_level": "Unknown",
            "prerequisites": [],
            "target_audience": "Unknown",
        }

        st.header("Video Analysis Results")

        # Get and display transcript with language selection
        st.subheader("📝 Video Transcript")
        # Language selection is handled within get_video_transcript
        transcript = content_analyzer.get_video_transcript(video_id, language=None)
        if transcript:
            # Clean transcript by removing timestamps and formatting as paragraphs
            clean_transcript = " ".join(
                line.split("] ")[1] if "] " in line else line
                for line in transcript.split("\n")
                if line.strip()
            )
            
            # Split into paragraphs (every ~5 sentences)
            sentences = clean_transcript.split(". ")
            paragraphs = []
            current_para = []
            
            for i, sentence in enumerate(sentences):
                current_para.append(sentence)
                if (i + 1) % 5 == 0 or i == len(sentences) - 1:
                    paragraphs.append(". ".join(current_para) + ".")
                    current_para = []
            
            with st.expander("View Full Transcript", expanded=True):
                for paragraph in paragraphs:
                    st.write(paragraph)
                    st.write("")  # Add space between paragraphs
            
            if summary_option:
                st.subheader("📝 Summary Analysis")
                transcript_analysis = content_analyzer.analyze_transcript(transcript)
                if transcript_analysis:
                    st.markdown("#### Summary")
                    st.write(transcript_analysis["summary"])
                    st.markdown("#### Key Points")
                    for point in transcript_analysis["key_points"]:
                        st.markdown(f"• {point}")

        if keywords_option:
            st.subheader("🔑 Key Concepts")
            if content_analysis["concepts"]:
                for concept in content_analysis["concepts"]:
                    st.markdown(f"- {concept}")

        if sentiment_option:
            st.subheader("😊 Sentiment Analysis")
            content_analyzer.display_sentiment_analysis(video_data)

        if qa_option:
            st.subheader("❓ Question & Answer")
            st.info("This feature allows you to ask questions about the video content")
            user_question = st.text_input("Ask a question about the video content")
            if user_question:
                # Placeholder for QA functionality
                st.write("This feature will be implemented soon!")

        if task_option:
            st.subheader("🔄 Task Automation")
            st.info("This feature helps automate tasks based on video content")
            # Placeholder for task automation functionality
            st.write("Task automation features coming soon!")

        return content_analysis

    except Exception as e:
        st.write(f"⚠️ Error analyzing video content: {str(e)}")
        return None

def main():
    st.title("Multiple YouTube Video Analyzer")

    api_client = APIClient()
    search_analyzer = SearchAnalyzer()
    channel_analyzer = ChannelAnalyzer(api_client)
    content_analyzer = ContentAnalyzer(api_client)
    
    # Create tabs for different functionalities
    search_tab, analyze_tab, channel_tab = st.tabs(["🔍 Search Videos", "📊 Analyze Videos", "📺 Channel Analysis"])
    
    with search_tab:
        st.subheader("Search Educational Videos")
        search_query = st.text_input("Enter your search query")
        
        if st.button("Search") and search_query:
            with st.spinner("Searching videos..."):
                videos = api_client.search_videos(search_query)
                
                if not videos:
                    st.warning("No videos found for your query.")
                else:
                    ranked_results = search_analyzer.rank_videos(search_query, videos)
                    
                    if ranked_results:
                        st.subheader("Top Relevant Videos")
                        for rank, result in enumerate(ranked_results, 1):
                            video = result['video']
                            with st.expander(f"{rank}. {video['title']}", expanded=rank == 1):
                                col1, col2 = st.columns([2, 1])
                                with col1:
                                    st.markdown(f"**Description**: {video['description'][:200]}...")
                                    st.markdown(f"**Channel**: {video['channelTitle']}")
                                with col2:
                                    st.markdown(f"**Views**: {video['views']:,}")
                                    st.markdown(f"**Likes**: {video['likes']:,}")
                                    engagement = (video['likes'] / video['views'] * 100) if video['views'] > 0 else 0
                                    st.markdown(f"**Engagement Rate**: {engagement:.2f}%")
                                    st.markdown(f"**Similarity Score**: {result['similarity']:.2f}")
                                # Get transcript for finding relevant segments
                                if not video.get('transcript'):
                                    video['transcript'] = content_analyzer.get_video_transcript(video['video_id'])
                                
                                # Show relevant segments with timestamps
                                if result.get('relevant_segments'):
                                    st.markdown("**🎯 Jump to Relevant Sections:**")
                                    for segment in result['relevant_segments']:
                                        timestamp_link = f"https://youtube.com/watch?v={video['video_id']}&t={segment['seconds']}s"
                                        st.markdown(f"""
                                        🕐 [{segment['timestamp']}]({timestamp_link})
                                        > {segment['text'][:150]}...
                                        """)
                                
                                st.markdown(f"**🎥 Watch Full Video**: https://youtube.com/watch?v={video['video_id']}")
    
    with analyze_tab:
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

        num_videos = st.slider(
            "Select number of videos to analyze",
            min_value=1,
            max_value=10,
            value=1,
            help="Choose how many videos you want to analyze (between 1 and 10)",
        )

        if num_videos == 1:
            st.write("Select analysis options for this video:")
            col1, col2, col3 = st.columns(3)
            with col1:
                summary_option = st.checkbox("Generate Summary", value=True)
                keywords_option = st.checkbox("Extract Keywords", value=True)
            with col2:
                sentiment_option = st.checkbox("Sentiment Analysis", value=True)
                qa_option = st.checkbox("Question Answering", value=True)
            with col3:
                task_option = st.checkbox("Task Automation", value=True)
        else:
            summary_option = keywords_option = sentiment_option = qa_option = task_option = False

        st.write(f"Enter {num_videos} YouTube video URL{'' if num_videos == 1 else 's'} of {'educational content' if num_videos == 1 else 'similar educational content'}")

        new_urls = []
        for i in range(num_videos):
            url = st.text_input(f"Video URL {i+1}", key=f"url_{i}")
            if url:
                if VideoAnalyzer.is_duplicate_url(url, new_urls):
                    st.write(f"⚠️ Video {i+1}: This video has already been added. Please enter a different URL.")
                    continue
                new_urls.append(url)

        videos_data = []
        videos_content_analysis = []
        all_sentiments = []

        if st.button("Analyze Videos") and len(new_urls) == num_videos:
            with st.spinner("Collecting video information..."):
                # Handle single video analysis
                if num_videos == 1:
                    url = new_urls[0]
                    video_id = VideoAnalyzer.extract_video_id(url)
                    if not video_id:
                        st.write(f"⚠️ Invalid YouTube URL: {url}")
                        return

                    video_data = api_client.get_video_details(video_id)
                    if not video_data:
                        st.write(f"⚠️ Could not fetch video details for: {url}")
                        return

                    content_analysis = analyze_single_video(
                        url, video_id, video_data, content_analyzer,
                        summary_option, keywords_option, sentiment_option,
                        qa_option, task_option
                    )
                    if content_analysis:
                        videos_content_analysis.append(content_analysis)
                        videos_data.append(video_data)
                    return

                # Handle multiple video analysis
                st.header("Multiple Video Analysis")
                for url in new_urls:
                    video_id = VideoAnalyzer.extract_video_id(url)
                    if not video_id:
                        st.write(f"⚠️ Invalid YouTube URL: {url}")
                        return

                    video_data = api_client.get_video_details(video_id)
                    if not video_data:
                        st.write(f"⚠️ Could not fetch video details for: {url}")
                        return

                    try:
                        content_analysis = content_analyzer.analyze_video_content(
                            video_data["title"], video_data["description"]
                        ) or {
                            "subject": "Unknown",
                            "subtopic": "Unknown",
                            "concepts": [],
                            "difficulty_level": "Unknown",
                            "prerequisites": [],
                            "target_audience": "Unknown",
                        }
                        videos_content_analysis.append(content_analysis)
                        videos_data.append(video_data)
                    except Exception as e:
                        st.write(f"⚠️ Error analyzing video content: {str(e)}")
                        return

                # Display multiple video analysis results
                if videos_data:
                    st.header("Video Content Analysis")
                    content_comparison = pd.DataFrame(
                        [
                            {
                                "Title": data["title"],
                                "Subject": analysis["subject"],
                                "Subtopic": analysis["subtopic"],
                                "Difficulty": analysis["difficulty_level"],
                                "Target Audience": analysis["target_audience"],
                                "Prerequisites": ", ".join(analysis["prerequisites"]),
                            }
                            for data, analysis in zip(videos_data, videos_content_analysis)
                        ]
                    )
                    st.dataframe(content_comparison)

                    # Detailed analysis for each video
                    st.header("Detailed Video Analysis")
                    tabs = st.tabs([f"Video {i+1}: {data['title'][:30]}..." for i, data in enumerate(videos_data)])
                    
                    for idx, (tab, video_data) in enumerate(zip(tabs, videos_data)):
                        with tab:
                            st.write(f"### {video_data['title']}")
                            
                            # Get and display transcript
                            st.subheader("📝 Video Transcript")
                            # Language selection is handled within get_video_transcript
                            transcript = content_analyzer.get_video_transcript(video_data['video_id'], language=None)
                            if transcript:
                                # Clean transcript and format paragraphs
                                clean_transcript = " ".join(
                                    line.split("] ")[1] if "] " in line else line
                                    for line in transcript.split("\n")
                                    if line.strip()
                                )
                                
                                # Split into paragraphs
                                sentences = clean_transcript.split(". ")
                                paragraphs = []
                                current_para = []
                                
                                for i, sentence in enumerate(sentences):
                                    current_para.append(sentence)
                                    if (i + 1) % 5 == 0 or i == len(sentences) - 1:
                                        paragraphs.append(". ".join(current_para) + ".")
                                        current_para = []
                                
                                # Display transcript and analysis
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    with st.expander("View Full Transcript", expanded=False):
                                        for paragraph in paragraphs:
                                            st.write(paragraph)
                                            st.write("")
                                    
                                    # Generate and display summary
                                    transcript_analysis = content_analyzer.analyze_transcript(transcript)
                                    if transcript_analysis:
                                        st.subheader("📝 Summary")
                                        st.write(transcript_analysis["summary"])
                                        
                                        st.subheader("🎯 Key Points")
                                        for point in transcript_analysis["key_points"]:
                                            st.markdown(f"• {point}")
                                        
                                        # Display chapter breakdown
                                        if transcript_analysis.get("chapter_breakdown"):
                                            with st.expander("📖 Chapter Breakdown", expanded=True):
                                                for chapter in transcript_analysis["chapter_breakdown"]:
                                                    st.markdown(f"**{chapter['title']}**")
                                                    st.markdown(f"{chapter['content']}")
                                                    st.divider()
                                
                                with col2:
                                    st.markdown(f"""
                                    **Video Stats**
                                    - Views: {video_data['views']:,}
                                    - Likes: {video_data['likes']:,}
                                    - Comments: {video_data['comments_count']:,}
                                    """)
                                    
                                    # Display concepts
                                    if videos_content_analysis[idx]["concepts"]:
                                        st.subheader("🔑 Key Concepts")
                                        for concept in videos_content_analysis[idx]["concepts"]:
                                            st.markdown(f"- {concept}")
                            else:
                                st.warning("📝 Transcript not available for this video")
                                st.markdown("""
                                **Possible reasons:**
                                - Subtitles are disabled by the creator
                                - Auto-generated captions are not ready
                                - Video is too recent
                                """)

                    # Add metrics summary section
                    st.header("Video Metrics Summary")
                    metrics_summary = pd.DataFrame(
                        {
                            "Video": [data["title"] for data in videos_data],
                            "Total Views": [f"{data['views']:,}" for data in videos_data],
                            "Total Likes": [f"{data['likes']:,}" for data in videos_data],
                            "Total Comments": [f"{data['comments_count']:,}" for data in videos_data],
                        }
                    )
                    st.dataframe(metrics_summary)

                    # Sentiment analysis for multiple videos
                    st.header("Comments Analysis")
                    for i, video_data in enumerate(videos_data):
                        with st.expander(f"Video {i+1}: {video_data['title']}", expanded=True):
                            if video_data.get('comments_enabled', False):
                                sentiments = content_analyzer.display_sentiment_analysis(video_data)
                                if sentiments:
                                    all_sentiments.append({
                                        "title": video_data["title"],
                                        "sentiments": {
                                            "positive": sentiments.get("positive", 0),
                                            "negative": sentiments.get("negative", 0),
                                        }
                                    })
                            else:
                                st.info("Comments are disabled for this video")

                    # Display sentiment comparison if we have sentiments
                    if all_sentiments:
                        st.header("Sentiment Comparison")
                        sentiment_data = []
                        for data in all_sentiments:
                            total = sum(data["sentiments"].values())
                            pos_pct = round((data["sentiments"]["positive"] / total * 100), 2) if total > 0 else 0
                            neg_pct = round((data["sentiments"]["negative"] / total * 100), 2) if total > 0 else 0

                            sentiment_data.append({
                                "Video": data["title"],
                                "Total Comments": total,
                                "Positive %": pos_pct,
                                "Negative %": neg_pct,
                                "Net Sentiment": pos_pct - neg_pct,
                            })

                        sentiment_df = pd.DataFrame(sentiment_data)
                        
                        # Create sentiment visualization
                        fig_sentiment = go.Figure()

                        fig_sentiment.add_trace(
                            go.Bar(
                                name="Positive",
                                x=sentiment_df["Positive %"],
                                y=sentiment_df["Video"],
                                orientation="h",
                                text=[f"{x:.1f}%" for x in sentiment_df["Positive %"]],
                                textposition="auto",
                                marker_color="green",
                            )
                        )

                        fig_sentiment.add_trace(
                            go.Bar(
                                name="Negative",
                                x=sentiment_df["Negative %"],
                                y=sentiment_df["Video"],
                                orientation="h",
                                text=[f"{x:.1f}%" for x in sentiment_df["Negative %"]],
                                textposition="auto",
                                marker_color="red",
                            )
                        )

                        fig_sentiment.update_layout(
                            barmode="stack",
                            title="Sentiment Distribution by Video",
                            xaxis_title="Percentage of Comments",
                            yaxis_title="Videos",
                            height=400,
                            showlegend=True,
                            yaxis={"categoryorder": "total ascending"},
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            ),
                        )

                        st.plotly_chart(fig_sentiment, use_container_width=True)

                    # Add video recommendation section
                    if len(videos_data) > 1:
                        st.header("🏆 Best Video Recommendation")
                        
                        # Calculate scores for each video
                        video_scores = []
                        for idx, (video, analysis, sentiment) in enumerate(zip(videos_data, videos_content_analysis, all_sentiments)):
                            # Engagement score (normalized by view count to not unfairly favor older videos)
                            engagement_rate = (video['likes'] + video['comments_count']) / video['views'] if video['views'] > 0 else 0
                            
                            # Sentiment score
                            total_comments = sentiment["sentiments"]["positive"] + sentiment["sentiments"]["negative"]
                            sentiment_score = sentiment["sentiments"]["positive"] / total_comments if total_comments > 0 else 0
                            
                            # Content quality score (based on having clear concepts and prerequisites)
                            content_score = (
                                (len(analysis.get("concepts", [])) > 0) * 0.5 +  # Has clear concepts
                                (len(analysis.get("prerequisites", [])) > 0) * 0.3 +  # Has prerequisites defined
                                (analysis.get("difficulty_level", "Unknown") != "Unknown") * 0.2  # Has difficulty level
                            )
                            
                            # Calculate final score (weighted average)
                            final_score = (
                                engagement_rate * 0.4 +
                                sentiment_score * 0.3 +
                                content_score * 0.3
                            )
                            
                            video_scores.append({
                                "title": video["title"],
                                "score": final_score,
                                "engagement_rate": engagement_rate,
                                "sentiment_score": sentiment_score,
                                "content_score": content_score,
                                "url": f"https://youtube.com/watch?v={video['video_id']}"
                            })
                        
                        # Sort videos by score
                        video_scores.sort(key=lambda x: x["score"], reverse=True)
                        best_video = video_scores[0]
                        
                        # Display recommendation
                        st.success(f"📽️ Recommended Video: **{best_video['title']}**")
                        st.markdown(f"""
                        Based on our analysis, this video stands out because:
                        - Engagement Score: {best_video['engagement_rate']:.2%}
                        - Sentiment Score: {best_video['sentiment_score']:.2%}
                        - Content Quality Score: {best_video['content_score']:.2%}
                        
                        **Overall Score:** {best_video['score']:.2%}
                        
                        [Watch Video]({best_video['url']})
                        """)
                        
                        # Display all video scores in a table
                        scores_df = pd.DataFrame([
                            {
                                "Video": score["title"],
                                "Overall Score": f"{score['score']:.2%}",
                                "Engagement": f"{score['engagement_rate']:.2%}",
                                "Sentiment": f"{score['sentiment_score']:.2%}",
                                "Content Quality": f"{score['content_score']:.2%}"
                            }
                            for score in video_scores
                        ])
                        st.dataframe(scores_df)

    with channel_tab:
        st.title("YouTube Channel Analysis")
        if not api_client.youtube_api:
            st.write("⚠️ YouTube API Key not found. Please add YOUTUBE_API_KEY to your .env file")
            return
            
        channel_query = st.text_input("Enter channel name to search")
        
        if st.button("Search Channel") and channel_query:
            with st.spinner("Searching for channel..."):
                channels = api_client.search_channels(channel_query)
                
                if not channels:
                    st.warning("No channels found for your query.")
                else:
                    st.subheader("Select a Channel")
                    channel_options = {f"{ch['title']} ({ch.get('subscriber_count', 0):,} subscribers)": ch 
                                    for ch in channels}
                    selected_channel_title = st.radio(
                        "Available channels:",
                        options=list(channel_options.keys()),
                        index=0
                    )
                    
                    selected_channel = channel_options[selected_channel_title]
                    
                    # Display channel information
                    channel_analyzer.display_channel_info(selected_channel)
                    
                    # Fetch and display playlists
                    with st.spinner("Fetching channel playlists..."):
                        playlists = api_client.get_channel_playlists(selected_channel['channel_id'])
                        if playlists:
                            playlists_analysis = channel_analyzer.analyze_channel_playlists(playlists)
                            channel_analyzer.display_playlists(playlists_analysis)
                        else:
                            st.info("No public playlists found for this channel.")

if __name__ == "__main__":
    main()
