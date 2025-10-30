from http.server import BaseHTTPRequestHandler
import json
import yt_dlp
import sys
import traceback

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
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            url = data.get('url')
            action = data.get('action', 'info')
            
            if not url:
                self.send_response(400)
                self._set_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'URL is required'}).encode())
                return
            
            # Clean TikTok URLs
            if 'tiktok.com' in url or 'vt.tiktok.com' in url:
                # yt-dlp handles TikTok well, just pass it through
                pass
            
            if action == 'info':
                # Get video info only
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'format': 'best',
                    'extract_flat': False,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    response = {
                        'title': info.get('title', 'Unknown'),
                        'duration': info.get('duration', 0),
                        'thumbnail': info.get('thumbnail', ''),
                        'uploader': info.get('uploader', 'Unknown'),
                        'description': info.get('description', '')[:200] if info.get('description') else '',
                    }
                    
                    self.send_response(200)
                    self._set_cors_headers()
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode())
            
            elif action == 'download':
                # Get direct download URL
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'format': 'best[filesize<50M]/best',
                    'extract_flat': False,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Get the best direct URL
                    video_url = None
                    if 'url' in info:
                        video_url = info['url']
                    elif 'formats' in info and len(info['formats']) > 0:
                        # Get the last format (usually best quality)
                        for fmt in reversed(info['formats']):
                            if fmt.get('url'):
                                video_url = fmt['url']
                                break
                    
                    if not video_url:
                        raise Exception("Could not extract video URL")
                    
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
            
            else:
                self.send_response(400)
                self._set_cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Invalid action'}).encode())
        
        except Exception as e:
            error_details = traceback.format_exc()
            print(f"Error: {str(e)}", file=sys.stderr)
            print(error_details, file=sys.stderr)
            
            self.send_response(500)
            self._set_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': str(e),
                'details': error_details
            }).encode())
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self._set_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'healthy', 'version': '1.0'}).encode())
        else:
            self.send_response(404)
            self._set_cors_headers()
            self.end_headers()
