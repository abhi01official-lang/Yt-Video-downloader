import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

COOKIES_PATH = '/tmp/yt_cookies.txt'
if os.environ.get('YOUTUBE_COOKIES'):
    with open(COOKIES_PATH, 'w') as f:
        f.write(os.environ.get('YOUTUBE_COOKIES'))

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "online", "message": "YouTube Extractor API is running!"}), 200

@app.route('/api/extract', methods=['POST'])
def extract_video():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Please provide a valid YouTube URL'}), 400

    url = data['url']

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'format': 'best',
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'mweb'],
                'skip': ['hls', 'dash']
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X; en_US)',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    if os.path.exists(COOKIES_PATH):
        ydl_opts['cookiefile'] = COOKIES_PATH

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'YouTube Video')
            thumbnail = info.get('thumbnail', '')
            formats = info.get('formats', [])

            video_formats = []
            audio_format = None

            for f in formats:
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

                if f.get('acodec') != 'none' and f.get('vcodec') == 'none' and f.get('url'):
                    audio_format = {
                        'quality': f"{int(f.get('abr', 128))} kbps",
                        'ext': f.get('ext', 'mp3'),
                        'url': f['url']
                    }

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
            }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to process video: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
