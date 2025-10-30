from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
import threading
import time
from pathlib import Path

app = Flask(__name__)
CORS(app)

# Directory to store downloaded videos
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Store download status
downloads = {}

def cleanup_old_files():
    """Remove files older than 1 hour"""
    while True:
        time.sleep(3600)  # Run every hour
        current_time = time.time()
        for file in DOWNLOAD_DIR.glob("*"):
            if current_time - file.stat().st_mtime > 3600:
                file.unlink()

# Start cleanup thread
threading.Thread(target=cleanup_old_files, daemon=True).start()

def download_video(url, download_id):
    """Download video using yt-dlp"""
    try:
        downloads[download_id]['status'] = 'downloading'
        
        output_path = DOWNLOAD_DIR / f"{download_id}.%(ext)s"
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': str(output_path),
            'progress_hooks': [lambda d: progress_hook(d, download_id)],
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            downloads[download_id]['status'] = 'completed'
            downloads[download_id]['filename'] = Path(filename).name
            downloads[download_id]['title'] = info.get('title', 'Unknown')
            downloads[download_id]['thumbnail'] = info.get('thumbnail', '')
            
    except Exception as e:
        downloads[download_id]['status'] = 'error'
        downloads[download_id]['error'] = str(e)

def progress_hook(d, download_id):
    """Update download progress"""
    if d['status'] == 'downloading':
        if 'total_bytes' in d:
            progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
            downloads[download_id]['progress'] = round(progress, 2)
        elif '_percent_str' in d:
            downloads[download_id]['progress'] = d['_percent_str']

@app.route('/api/download', methods=['POST'])
def start_download():
    """Initiate video download"""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    # Generate unique download ID
    download_id = str(uuid.uuid4())
    
    # Initialize download status
    downloads[download_id] = {
        'status': 'pending',
        'progress': 0,
        'url': url
    }
    
    # Start download in background thread
    thread = threading.Thread(target=download_video, args=(url, download_id))
    thread.start()
    
    return jsonify({
        'download_id': download_id,
        'message': 'Download started'
    })

@app.route('/api/status/<download_id>', methods=['GET'])
def get_status(download_id):
    """Get download status"""
    if download_id not in downloads:
        return jsonify({'error': 'Download not found'}), 404
    
    return jsonify(downloads[download_id])

@app.route('/api/download/<download_id>', methods=['GET'])
def download_file(download_id):
    """Download the completed video file"""
    if download_id not in downloads:
        return jsonify({'error': 'Download not found'}), 404
    
    if downloads[download_id]['status'] != 'completed':
        return jsonify({'error': 'Download not completed'}), 400
    
    filename = downloads[download_id]['filename']
    file_path = DOWNLOAD_DIR / filename
    
    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(file_path, as_attachment=True)

@app.route('/api/info', methods=['POST'])
def get_video_info():
    """Get video information without downloading"""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return jsonify({
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'description': info.get('description', '')[:200]
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
