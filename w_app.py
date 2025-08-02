from flask import Flask, render_template, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import requests
import re
import logging
from functools import lru_cache
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

# --- Configuration ---
LIBRETRANSLATE_URL = "https://translate.shabeerkhan.com"  # Change if needed
CHUNK_SIZE = 350
CACHE_SIZE = 100
TRANSLATION_TIMEOUT = 60  # seconds
TRANSLATION_RETRIES = 3

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Extract Video ID ---
def extract_video_id(url):
    """
    Extract YouTube video ID from any format (including Shorts).
    Works for:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - VIDEO_ID directly
    """
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([0-9A-Za-z_-]{11})",
        r"(?:v=|/)([0-9A-Za-z_-]{11})"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # If it's already a raw ID
    if len(url) == 11 and re.match(r"[0-9A-Za-z_-]{11}", url):
        return url

    return None

# --- Fetch Transcript (First Available) ---
@lru_cache(maxsize=CACHE_SIZE)
def get_transcript(video_id):
    """Fetch the first available transcript in any language."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Loop through available transcripts
        for transcript in transcript_list:
            try:
                fetched = transcript.fetch()
                logger.info(f"Fetched transcript in language: {transcript.language_code}")

                # FIX: Use .text property
                return " ".join(entry.text for entry in fetched)
            except Exception as e:
                logger.warning(f"Failed to fetch transcript in {transcript.language_code}: {e}")
                continue

        logger.warning(f"No transcript fetched for {video_id}")
        return None

    except TranscriptsDisabled:
        logger.warning(f"Transcripts disabled for {video_id}")
        return None
    except NoTranscriptFound:
        logger.warning(f"No transcript found for {video_id}")
        return None
    except Exception as e:
        logger.error(f"Error fetching transcript for {video_id}: {str(e)}")
        return None

# --- Translate Chunks Sequentially ---
def translate_chunk(chunk, target_lang, preserve_terms, retries=TRANSLATION_RETRIES):
    """Translate a text chunk while preserving specific terms."""
    term_map = {}
    for i, term in enumerate(preserve_terms):
        placeholder = f"TERM_{i}_X"
        chunk = chunk.replace(term, placeholder)
        term_map[placeholder] = term

    for attempt in range(retries):
        try:
            response = requests.post(
                f"{LIBRETRANSLATE_URL}/translate",
                json={
                    "q": chunk,
                    "source": "auto",
                    "target": target_lang
                },
                timeout=TRANSLATION_TIMEOUT
            )
            translated = response.json().get("translatedText", chunk)

            # Restore preserved terms
            for placeholder, term in term_map.items():
                translated = translated.replace(placeholder, term)

            return translated
        except Exception as e:
            logger.error(f"Translation failed (attempt {attempt+1}/{retries}): {str(e)}")
            time.sleep(2)  # Backoff before retry

    # Fallback to original if all retries fail
    return chunk

# --- API Endpoint ---
@app.route("/translate", methods=["POST"])
def handle_translation():
    start_time = time.time()
    data = request.get_json()

    # Validate input
    video_url = data.get("video_url", "").strip()
    target_lang = data.get("target_lang", "es").strip()
    preserve_terms = [t.strip() for t in data.get("preserve_terms", []) if t.strip()]

    # Extract Video ID
    video_id = extract_video_id(video_url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL or Shorts link"}), 400

    # Fetch Transcript
    transcript = get_transcript(video_id)
    if not transcript:
        return jsonify({"error": "Transcript not available for this video"}), 404

    # Split transcript into chunks for translation
    chunks = [transcript[i:i+CHUNK_SIZE] for i in range(0, len(transcript), CHUNK_SIZE)]

    # Translate sequentially (safer for local LibreTranslate)
    translated_chunks = []
    for chunk in chunks:
        translated_chunks.append(translate_chunk(chunk, target_lang, preserve_terms))

    processing_time = round(time.time() - start_time, 2)
    logger.info(f"Translated {len(chunks)} chunks in {processing_time}s")

    return jsonify({
        "original": transcript,
        "translated": " ".join(translated_chunks),
        "status": "success",
        "processing_time": processing_time
    })

# --- Home Route ---
@app.route("/")
def home():
    return render_template("index.html")

# --- Run App ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
