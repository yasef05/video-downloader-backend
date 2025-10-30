from http.server import BaseHTTPRequestHandler
import json
import yt_dlp
import tempfile
import base64
import os

class handler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        url = data.get('url')
        action = data.get('action', 'info')  # 'info' or 'download'
        
        if not url:
            self.send_response(400)
            self._set_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'URL is required'}).encode())
            return
        
        try:
            if action == 'info':
                # Get video info only
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    response = {
                        'title': info.get('title', 'Unknown'),
                        'duration': info.get('duration', 0),
                        'thumbnail': info.get('thumbnail', ''),
                        'uploader': info.get('uploader', 'Unknown'),
                        'description': info.get('description', '')[:200],
                        'formats': [
                            {
                                'format_id': f.get('format_id'),
                                'ext': f.get('ext'),
                                'quality': f.get('format_note', 'unknown'),
                                'filesize': f.get('filesize', 0)
                            }
                            for f in info.get('formats', [])[:5]  # First 5 formats
                        ]
                    }
                    
                    self.send_response(200)
                    self._set_cors_headers()
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode())
            
            elif action == 'download':
                # Download video and return direct download URL
                # Note: For Vercel, we'll return the video URL from the source
                # because Vercel has 50MB response limit
                
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'format': 'best[filesize<?50M]/best',  # Limit to 50MB for Vercel
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Get direct video URL
                    video_url = info.get('url')
                    
                    response = {
                        'title': info.get('title', 'Unknown'),
                        'thumbnail': info.get('thumbnail', ''),
                        'duration': info.get('duration', 0),
                        'download_url': video_url,
                        'ext': info.get('ext', 'mp4')
                    }
                    
                    self.send_response(200)
                    self._set_cors_headers()
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode())
        
        except Exception as e:
            self.send_response(500)
            self._set_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self._set_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'healthy'}).encode())
        else:
            self.send_response(404)
            self._set_cors_headers()
            self.end_headers()
