import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

@app.route('/api/extract', methods=['POST'])
def extract():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'Please provide a valid YouTube URL'}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
            # Extract Video + Audio Formats
            video_formats = []
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    video_formats.append({
                        'quality': f.get('format_note') or f"{f.get('height')}p",
                        'ext': f.get('ext'),
                        'url': f.get('url')
                    })

            # Extract Audio-Only Stream
            best_audio = None
            for f in formats:
                if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                    if not best_audio or (f.get('abr') or 0) > (best_audio.get('abr') or 0):
                        best_audio = f

            audio_format = None
            if best_audio:
                audio_format = {
                    'quality': f"{int(best_audio.get('abr', 128))}kbps MP3",
                    'ext': 'mp3',
                    'url': best_audio.get('url')
                }

            return jsonify({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'video_formats': video_formats,
                'audio_format': audio_format
            })

    except Exception as e:
        return jsonify({'error': 'Failed to process video link.'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
