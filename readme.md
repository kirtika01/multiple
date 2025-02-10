# Multiple YouTube Video Analyzer

A comprehensive analysis tool for comparing and evaluating YouTube videos using data-driven metrics and AI-powered content analysis.

## Description

The YouTube Video Analyzer is a powerful tool designed to help educators, content creators, and learners analyze and compare educational videos on YouTube. It provides in-depth insights into video performance, content quality, and audience engagement through various metrics and AI-powered analysis.

## Features

- Multiple video comparison (2-10 videos)
- Content analysis including:
  - Subject and subtopic identification
  - Difficulty level assessment
  - Target audience identification
  - Prerequisites detection
  - Key concepts extraction
- Performance metrics:
  - Views, likes, and comments statistics
  - Engagement metrics
- Comment sentiment analysis
- Domain compatibility checking
- Video recommendations based on multiple factors

## Prerequisites

- Python 3.11
- YouTube Data API key
- Google API key (for Gemini AI)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd youtube-educational-video-analyzer
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root directory with your API keys:
```env
YOUTUBE_API_KEY=your_youtube_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

## Project Structure

- `youtube_analyzer.py`: Main application file with Streamlit interface
- `api_client.py`: Handles API interactions with YouTube and Google AI
- `content_analyzer.py`: Processes video content analysis using AI
- `video_analyzer.py`: Core video analysis functionality
- `requirements.txt`: Project dependencies
- `.env`: API configuration (needs to be created)

## How to Use

1. Start the application:
```bash
streamlit run youtube_analyzer.py
```

2. Use the interface to:
   - Select the number of videos to analyze (2-10)
   - Enter YouTube video URLs
   - Click "Analyze Videos" to start the analysis

3. View the results:
   - Content Analysis: Subject matter, difficulty level, prerequisites, etc.
   - Metrics Summary: Views, likes, and comments statistics
   - Sentiment Analysis: Analysis of video comments
   - Video Recommendation: Best video based on multiple factors

## Features in Detail

### Content Analysis
- Identifies the main subject and subtopic of each video
- Assesses difficulty level and target audience
- Lists prerequisites and key concepts covered

### Performance Metrics
- Total views, likes, and comments for each video
- Comparative analysis across videos
- Engagement metrics calculation

### Sentiment Analysis
- Analyzes video comments for sentiment
- Provides positive/negative sentiment distribution
- Calculates overall sentiment score

### Domain Compatibility
- Ensures videos being compared are from related educational domains
- Prevents misleading comparisons across unrelated subjects

### Video Recommendations
- Provides data-driven video recommendations
- Considers multiple factors:
  - Content quality
  - Engagement metrics
  - Audience response
  - Sentiment analysis

## Notes

- The application requires valid API keys to function
- Analysis quality depends on video metadata and comment availability
- For educational videos only; not designed for entertainment content
- Rate limits apply based on your API quota

## Error Handling

The application includes comprehensive error handling for:
- Invalid YouTube URLs
- API failures
- Domain mismatches
- Missing or incorrect API keys

