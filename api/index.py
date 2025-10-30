from http.server import BaseHTTPRequestHandler
import json
import yt_dlp
import sys

class handler(BaseHTTPRequestHandler):
    
    def _send_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self._send_response(200, {'status': 'healthy', 'version': '2.0'})
        else:
            self._send_response(404, {'error': 'Not found'})
    
    def do_POST(self):
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_response(400, {'error': 'Empty request body'})
                return
            
            post_data = self.rfile.read(content_length)
            
            # Parse JSON
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError as e:
                self._send_response(400, {'error': f'Invalid JSON: {str(e)}'})
                return
            
            url = data.get('url')
            action = data.get('action', 'info')
            
            if not url:
                self._send_response(400, {'error': 'URL is required'})
                return
            
            print(f"Processing {action} for URL: {url}", file=sys.stderr)
            
            # Process based on action
            if action == 'info':
                result = self._get_video_info(url)
                self._send_response(200, result)
            
            elif action == 'download':
                result = self._get_download_url(url)
                self._send_response(200, result)
            
            else:
                self._send_response(400, {'error': f'Invalid action: {action}'})
        
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            self._send_response(500, {'error': str(e)})
    
    def _get_video_info(self, url):
        """Get video information without downloading"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'description': (info.get('description', '') or '')[:200],
            }
    
    def _get_download_url(self, url):
        """Get direct download URL"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[filesize<50M]/best',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Find direct video URL
            video_url = None
            
            if 'url' in info:
                video_url = info['url']
            elif 'formats' in info:
                for fmt in reversed(info['formats']):
                    if fmt.get('url') and fmt.get('vcodec') != 'none':
                        video_url = fmt['url']
                        break
            
            if not video_url:
                raise Exception("Could not find video URL")
            
            return {
                'download_id': 'direct',
                'download_url': video_url,
                'title': info.get('title', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
            }
