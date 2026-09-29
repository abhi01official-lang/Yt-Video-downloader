import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)

# Enable CORS for all routes (allows GitHub Pages to make requests)
CORS(app)

def clean_title(title):
    """Sanitize title to remove invalid filename characters."""
    return re.sub(r'[\\/*?:"<>|]', "", title)

@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint to verify backend status."""
    return jsonify({
        "status": "online",
        "message": "YouTube Extractor API is running successfully!"
    }), 200

@app.route("/api/extract", methods=["POST"])
def extract_media():
    data = request.get_json()
    
    if not data or "url" not in data:
        return jsonify({"error": "Please provide a valid YouTube URL"}), 400

    url = data["url"]

    # Production-ready yt-dlp configuration to bypass YouTube datacenter IP blocks
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        # Fallback to iOS/Android client headers which bypass web bot-checks
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'web']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return jsonify({"error": "Unable to fetch video information."}), 400

            title = info.get("title", "YouTube Video")
            thumbnail = info.get("thumbnail", "")
            duration = info.get("duration", 0)

            media_formats = []

            # Extract available format streams
            formats = info.get("formats", [])
            for f in formats:
                # Include video formats with audio or audio-only streams
                if f.get("url"):
                    ext = f.get("ext", "mp4")
                    format_id = f.get("format_id", "")
                    resolution = f.get("format_note") or f.get("resolution") or (f"{f.get('height')}p" if f.get('height') else None)
                    vcodec = f.get("vcodec", "none")
                    acodec = f.get("acodec", "none")
                    
                    # Distinguish between Video+Audio vs Audio-only
                    if vcodec != "none" and acodec != "none":
                        media_type = "video"
                        label = f"Video ({resolution or 'HD'})"
                    elif vcodec == "none" and acodec != "none":
                        media_type = "audio"
                        label = f"Audio Only ({f.get('abr', '128')} kbps)"
                    else:
                        continue

                    filesize = f.get("filesize") or f.get("filesize_approx")
                    filesize_str = f"{round(filesize / (1024 * 1024), 1)} MB" if filesize else "Unknown size"

                    media_formats.append({
                        "format_id": format_id,
                        "url": f.get("url"),
                        "ext": ext,
                        "type": media_type,
                        "label": label,
                        "quality": resolution or "Audio",
                        "size": filesize_str
                    })

            # Sort so best video formats appear first
            media_formats.reverse()

            return jsonify({
                "title": title,
                "thumbnail": thumbnail,
                "duration": duration,
                "formats": media_formats[:10]  # Return top 10 best options
            }), 200

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": f"YouTube extraction error: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
