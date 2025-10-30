from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse

COBALT_API = "https://api.cobalt.tools/api/json"

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
            self._send_response(200, {'status': 'healthy', 'version': 'cobalt-1.0'})
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
            
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError as e:
                self._send_response(400, {'error': f'Invalid JSON: {str(e)}'})
                return
            
            url = data.get('url')
            action = data.get('action', 'download')
            
            if not url:
                self._send_response(400, {'error': 'URL is required'})
                return
            
            # Call Cobalt API
            result = self._get_video_from_cobalt(url)
            
            if action == 'info':
                # Return basic info
                self._send_response(200, {
                    'title': result.get('title', 'Video'),
                    'duration': 0,
                    'thumbnail': result.get('thumbnail', ''),
                    'uploader': 'Unknown',
                    'description': ''
                })
            else:
                # Return download URL
                self._send_response(200, result)
        
        except Exception as e:
            self._send_response(500, {'error': str(e)})
    
    def _get_video_from_cobalt(self, url):
        """Get video download URL from Cobalt API"""
        
        # Prepare request to Cobalt
        cobalt_payload = {
            "url": url,
            "vCodec": "h264",
            "vQuality": "720",
            "aFormat": "mp3",
            "filenamePattern": "basic",
            "isAudioOnly": False
        }
        
        # Make request to Cobalt API
        req = urllib.request.Request(
            COBALT_API,
            data=json.dumps(cobalt_payload).encode('utf-8'),
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            cobalt_response = json.loads(response.read().decode('utf-8'))
        
        # Parse Cobalt response
        if cobalt_response.get('status') == 'error':
            raise Exception(cobalt_response.get('text', 'Download failed'))
        
        # Get download URL
        download_url = cobalt_response.get('url')
        if not download_url:
            raise Exception('No download URL returned')
        
        return {
            'download_id': 'cobalt',
            'download_url': download_url,
            'title': 'Video',
            'thumbnail': '',
            'duration': 0
        }
