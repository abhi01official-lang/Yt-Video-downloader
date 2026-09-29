from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "message": "YouTube Downloader API is running!"})

@app.route('/api/extract', methods=['POST'])
def extract_video():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Please provide a valid YouTube URL'}), 400

    url = data['url']

    # Updated ydl options using client fallback chain and custom headers
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'format': 'best',
        'extractor_args': {
            'youtube': {
                'player_client': ['web_creator', 'android', 'ios'],
                'skip': ['hls', 'dash']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'YouTube Video')
            thumbnail = info.get('thumbnail', '')
            formats = info.get('formats', [])

            video_formats = []
            audio_format = None

            for f in formats:
                # Direct stream video formats
                if f.get('vcodec') != 'none' and f.get('url'):
                    height = f.get('height')
                    quality = f"{height}p" if height else (f.get('format_note') or "SD")
                    ext = f.get('ext', 'mp4')
                    
                    video_formats.append({
                        'quality': quality,
                        'ext': ext,
                        'url': f['url'],
                        'height': height or 0
                    })

                # Best available audio stream
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none' and f.get('url'):
                    audio_format = {
                        'quality': f"{int(f.get('abr', 128))} kbps",
                        'ext': f.get('ext', 'mp3'),
                        'url': f['url']
                    }

            # Filter distinct resolutions (1080p, 720p, 480p, 360p)
            unique_videos = []
            seen_qualities = set()
            for v in sorted(video_formats, key=lambda x: x['height'], reverse=True):
                if v['quality'] not in seen_qualities and v['height'] in [360, 480, 720, 1080]:
                    seen_qualities.add(v['quality'])
                    unique_videos.append({
                        'quality': v['quality'],
                        'ext': v['ext'],
                        'url': v['url']
                    })

            # General fallback if standard resolutions aren't matched
            if not unique_videos and video_formats:
                unique_videos = [{
                    'quality': video_formats[0]['quality'],
                    'ext': video_formats[0]['ext'],
                    'url': video_formats[0]['url']
                }]

            return jsonify({
                'title': title,
                'thumbnail': thumbnail,
                'video_formats': unique_videos,
                'audio_format': audio_format
            })

    except Exception as e:
        return jsonify({'error': f'Failed to process video: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
