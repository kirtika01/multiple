import streamlit as st
from typing import Dict, List
import json
import re

class ChannelAnalyzer:
    def __init__(self, api_client):
        self.api_client = api_client

    def _clean_json_response(self, response: str, title: str, video_count: int) -> dict:
        """Clean and parse JSON response from the model with improved error handling"""
        try:
            json_str = response
            if '```' in response:
                
                blocks = response.split('```')
                for block in blocks:
                    if '{' in block and '}' in block:
                        json_str = block.strip()
                        break

            
            match = re.search(r'\{[^}]+\}', json_str)
            if match:
                json_str = match.group(0)

           
            json_str = json_str.replace('\n', ' ').replace('\\n', ' ')
            json_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
            json_str = json_str.replace("'", '"')
            json_str = re.sub(r'None|null|undefined', 'null', json_str, flags=re.IGNORECASE)
            json_str = re.sub(r'True|true|False|false', lambda m: m.group(0).lower(), json_str)
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                
                json_str = re.sub(r'[^\[\]{}",:\-\d\w\s]', '', json_str)
                json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
                json_str = re.sub(r'([{\[]),\s*([}\]])', r'\1\2', json_str)
                json_str = re.sub(r':\s*([]},])', r':null\1', json_str)
                
                try:
                    return json.loads(json_str)
                except:
                    
                    return {
                        "summary": f"A collection of {video_count} videos about {title}",
                        "target_audience": "General audience",
                        "key_topics": [title]
                    }

        except Exception as e:
            st.warning(f"Error cleaning JSON: {str(e)}")
            return {
                "summary": f"A collection of {video_count} videos about {title}",
                "target_audience": "General audience",
                "key_topics": [title]
            }

    def analyze_channel_playlists(self, playlists: List[Dict]) -> Dict:
        """Analyze channel playlists and return structured information with content analysis"""
        playlist_info = []
        
        for playlist in playlists:
            
            description = playlist.get("description", "").strip()
            title = playlist["title"].strip()
            
            
            summary_prompt = f"""Analyze this YouTube playlist and create a brief, informative description:
            
            PLAYLIST DETAILS
            Title: {title}
            Description: {description}
            Video Count: {playlist['video_count']}
            
            REQUIRED FORMAT
            You must return ONLY a valid JSON object with NO additional text, comments, or formatting:
            {{
                "summary": "A clear, concise 2-3 sentence description of what this playlist teaches",
                "target_audience": "A specific description of who would benefit most from this content",
                "key_topics": ["3-5 main topics", "covered in", "this playlist"]
            }}
            
            RULES:
            1. Response must be valid JSON
            2. No text outside the JSON object
            3. No code blocks or markdown
            4. Use double quotes for strings
            5. No trailing commas
            """
          
            try:
                if hasattr(self.api_client, 'gemini_model'):
                    response = self.api_client.gemini_model.predict(summary_prompt)
                  
                    summary_data = self._clean_json_response(response, title, playlist['video_count'])
                    
                 
                    if not all(key in summary_data for key in ["summary", "target_audience", "key_topics"]):
                        raise ValueError("Missing required fields in response")
                else:
                    summary_data = {
                        "summary": f"A collection of {playlist['video_count']} videos about {title}",
                        "target_audience": "General audience",
                        "key_topics": [title]
                    }
            except Exception as e:
                st.warning(f"Error generating summary: {str(e)}")
                summary_data = {
                    "summary": f"A collection of {playlist['video_count']} videos about {title}",
                    "target_audience": "General audience",
                    "key_topics": [title]
                }
            
        
            info = {
                "title": title,
                "original_description": description if description else "No description available",
                "generated_description": summary_data["summary"],
                "target_audience": summary_data["target_audience"],
                "key_topics": summary_data["key_topics"],
                "video_count": playlist["video_count"],
                "url": f"https://www.youtube.com/playlist?list={playlist['id']}",
                "thumbnail": playlist.get("thumbnail", ""),
                "published_at": playlist.get("published_at", "")
            }
            
            # Analyze description content
            if description and description != "No description available":
                try:
                    # Extract key information from description
                    topics = []
                    prerequisites = []
                    learning_outcomes = []
                    highlights = []
                    
                    # Generate a concise summary
                    desc_lines = description.lower().split('\n')
                    for line in desc_lines:
                        line = line.strip()
                        # Look for educational keywords
                        if any(keyword in line for keyword in ['learn', 'cover', 'master', 'understand', 'practice']):
                            clean_line = line.strip('•-[]()').strip()
                            if clean_line and len(clean_line) > 10:  # Avoid very short lines
                                highlights.append(clean_line)
                    
                    # Create a focused summary
                    if highlights:
                        focused_summary = " ".join(highlights[:3])  # Take top 3 highlights
                    else:
                        focused_summary = description[:200] + "..." if len(description) > 200 else description
                    
                    # Look for common patterns in educational content
                    lines = description.split('\n')
                    current_section = None
                    
                    for line in lines:
                        line = line.strip()
                        lower_line = line.lower()
                        
                        # Detect section headers
                        if any(keyword in lower_line for keyword in ['topics:', 'cover:', 'learn:']):
                            current_section = 'topics'
                            continue
                        elif any(keyword in lower_line for keyword in ['prerequisite:', 'requirements:', 'before:']):
                            current_section = 'prerequisites'
                            continue
                        elif any(keyword in lower_line for keyword in ['outcome:', 'will learn:', 'takeaway:']):
                            current_section = 'outcomes'
                            continue
                        
                        # Add content to appropriate section if line is not empty
                        if line and not line.startswith('http'):
                            if current_section == 'topics' and line.strip('-•⚫').strip():
                                topics.append(line.strip('-•⚫').strip())
                            elif current_section == 'prerequisites' and line.strip('-•⚫').strip():
                                prerequisites.append(line.strip('-•⚫').strip())
                            elif current_section == 'outcomes' and line.strip('-•⚫').strip():
                                learning_outcomes.append(line.strip('-•⚫').strip())
                    
                    # Add analysis to info
                    info["content_analysis"] = {
                        "topics": topics or ["General " + playlist["title"]],
                        "prerequisites": prerequisites,
                        "learning_outcomes": learning_outcomes,
                        "focused_summary": focused_summary,
                        "estimated_duration": f"{playlist['video_count'] * 10} minutes",  # Rough estimate
                        "difficulty_level": self._estimate_difficulty(description)
                    }
                except Exception as e:
                    st.warning(f"Error analyzing playlist description: {str(e)}")
                    info["content_analysis"] = None
            else:
                info["content_analysis"] = None
            
            playlist_info.append(info)
            
        return {
            "total_playlists": len(playlists),
            "playlists": playlist_info
        }

    def _estimate_difficulty(self, description: str) -> str:
        """Estimate difficulty level based on description content"""
        description = description.lower()
        
        # Define keyword sets for different levels
        beginner_keywords = {'basic', 'beginner', 'introduction', 'fundamental', 'start', 'first step'}
        advanced_keywords = {'advanced', 'expert', 'complex', 'deep dive', 'professional', 'optimization'}
        
        # Count keyword occurrences
        beginner_count = sum(1 for word in beginner_keywords if word in description)
        advanced_count = sum(1 for word in advanced_keywords if word in description)
        
        # Determine difficulty level
        if advanced_count > beginner_count:
            return "Advanced"
        elif beginner_count > 0:
            return "Beginner"
        else:
            return "Intermediate"

    def display_channel_info(self, channel_data: Dict):
        """Display channel information in a structured format"""
        st.header(f"📺 {channel_data['title']}")
        
        # Channel statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Subscribers", f"{channel_data['subscriber_count']:,}")
        with col2:
            st.metric("Total Videos", f"{channel_data['video_count']:,}")
        with col3:
            st.metric("Total Views", f"{channel_data['view_count']:,}")
            
        # Channel description
        st.subheader("About Channel")
        st.markdown(f"*{channel_data.get('description', 'No description available')}*")
        
        # Display custom URL if available
        if custom_url := channel_data.get('custom_url'):
            st.markdown(f"**Channel URL**: https://youtube.com/{custom_url}")

    def display_playlists(self, playlists_data: Dict):
        """Display channel playlists in an organized format"""
        st.header(f"📑 Playlists ({playlists_data['total_playlists']})")
        
        # Create tabs for different playlist views
        list_view, grid_view = st.tabs(["📋 List View", "🔲 Grid View"])
        
        with list_view:
            for playlist in playlists_data["playlists"]:
                with st.expander(f"🎬 {playlist['title']} ({playlist['video_count']} videos)", expanded=False):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown("### 📝 About This Playlist")
                        
                        # Display generated description and key information
                        st.markdown("**📚 Overview**")
                        st.markdown(f"*{playlist['generated_description']}*")
                        
                        # Show target audience
                        st.markdown("\n**👥 Intended For**")
                        st.markdown(f"*{playlist['target_audience']}*")
                        
                        # Show key topics
                        st.markdown("\n**🎯 Main Topics**")
                        for topic in playlist['key_topics']:
                            st.markdown(f"• {topic}")
                        
                        # Show metadata and original description together
                        st.markdown("\n**ℹ️ Details**")
                        st.markdown(f"• **Videos**: {playlist['video_count']}")
                        st.markdown(f"• **Published**: {playlist['published_at']}")
                        st.markdown(f"• **URL**: {playlist['url']}")
                        st.markdown("\n**📝 Original Description**")
                        st.markdown(f"```\n{playlist['original_description']}\n```")
                    
                    with col2:
                        if playlist['thumbnail']:
                            st.image(playlist['thumbnail'], use_container_width=True)
                    
                    # Display content analysis if available
                    if playlist.get('content_analysis'):
                        st.markdown("### 📊 Content Analysis")
                        
                        # Create three columns for analysis display
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown("**🎯 Main Topics**")
                            for topic in playlist['content_analysis']['topics']:
                                st.markdown(f"- {topic}")
                        
                        with col2:
                            st.markdown("**📚 Prerequisites**")
                            if playlist['content_analysis']['prerequisites']:
                                for prereq in playlist['content_analysis']['prerequisites']:
                                    st.markdown(f"- {prereq}")
                            else:
                                st.markdown("- No specific prerequisites mentioned")
                        
                        with col3:
                            st.markdown("**🎓 Learning Outcomes**")
                            if playlist['content_analysis']['learning_outcomes']:
                                for outcome in playlist['content_analysis']['learning_outcomes']:
                                    st.markdown(f"- {outcome}")
                            else:
                                st.markdown("- Learning outcomes not specified")
                        
                        # Display additional metadata
                        st.markdown(f"""
                        **📊 Course Details**
                        - Difficulty Level: {playlist['content_analysis']['difficulty_level']}
                        - Estimated Duration: {playlist['content_analysis']['estimated_duration']}
                        """)
        
        with grid_view:
            cols = st.columns(2)
            for i, playlist in enumerate(playlists_data["playlists"]):
                with cols[i % 2]:
                    st.markdown(f"### {playlist['title']}")
                    if playlist['thumbnail']:
                        st.image(playlist['thumbnail'], use_container_width=True)
                    
                    # Show generated description
                    st.markdown("**📚 Overview**")
                    summary = playlist['generated_description']
                    st.markdown(f"*{summary[:150]}...*" if len(summary) > 150 else f"*{summary}*")
                    
                    # Show target audience and basic stats
                    stats_md = [
                        f"👥 **For**: {playlist['target_audience']}",
                        f"📊 **Videos**: {playlist['video_count']}"
                    ]
                    
                    # Add content analysis if available
                    if playlist.get('content_analysis'):
                        stats_md.extend([
                            f"📚 **Level**: {playlist['content_analysis']['difficulty_level']}",
                            f"⏱️ **Duration**: {playlist['content_analysis']['estimated_duration']}",
                        ])
                        # Add up to 2 topics if available
                        if topics := playlist['content_analysis']['topics'][:2]:
                            stats_md.append(f"🎯 **Topics**: {', '.join(topics)}")
                    
                    # Display all stats
                    st.markdown('\n'.join(stats_md))
                    st.markdown(f"[View Playlist]({playlist['url']})")
                    st.markdown("---")  # Add separator between playlists