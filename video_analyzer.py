from urllib.parse import urlparse, parse_qs

class VideoAnalyzer:
    @staticmethod
    def extract_video_id(url):
        """Extract video ID from YouTube URL"""
        if not url:
            return None
        
        try:
            parsed_url = urlparse(url)
            if parsed_url.hostname == 'youtu.be':
                return parsed_url.path[1:]
            if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
                
                if parsed_url.path == '/watch':
                    return parse_qs(parsed_url.query)['v'][0]
                
                elif parsed_url.path.startswith('/shorts/'):
                    return parsed_url.path.split('/shorts/')[1].split('?')[0]
        except Exception:
            return None
        return None
    
    @staticmethod
    def is_duplicate_url(url, existing_urls):
        """Check if a URL is duplicate by comparing video IDs"""
        if not url:
            return False
        
        new_video_id = VideoAnalyzer.extract_video_id(url)
        if not new_video_id:
            return False
        
        existing_video_ids = [VideoAnalyzer.extract_video_id(existing_url) for existing_url in existing_urls]
        return new_video_id in existing_video_ids