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
LIBRETRANSLATE_URL = "http://vo8g84408o4scockow4ow8o8.161.97.109.36.sslip.io"
CHUNK_SIZE = 350
CACHE_SIZE = 100
TRANSLATION_TIMEOUT = 60
TRANSLATION_RETRIES = 3

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Extract Video ID ---
def extract_video_id(url):
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([0-9A-Za-z_-]{11})",
        r"(?:v=|/)([0-9A-Za-z_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    if len(url) == 11 and re.match(r"[0-9A-Za-z_-]{11}", url):
        return url
    return None

# --- Fetch Transcript ---
@lru_cache(maxsize=CACHE_SIZE)
def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        for transcript in transcript_list:
            try:
                fetched = transcript.fetch()
                logger.info(f"Fetched transcript in language: {transcript.language_code}")

                # Handle both object & dict forms
                lines = []
                for entry in fetched:
                    if hasattr(entry, "text"):  # object form
                        lines.append(entry.text)
                    elif isinstance(entry, dict) and "text" in entry:  # dict form
                        lines.append(entry["text"])
                return " ".join(line for line in lines if line.strip())

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

# --- Detect Language ---
def detect_language(text):
    try:
        response = requests.post(
            f"{LIBRETRANSLATE_URL}/detect",
            json={"q": text[:1000]},
            timeout=10
        )
        detected_lang = response.json()[0]["language"]
        logger.info(f"Detected source language: {detected_lang}")
        return detected_lang
    except Exception as e:
        logger.error(f"Language detection failed: {str(e)}")
        return "auto"

# --- Translate Chunk ---
def translate_chunk(chunk, source_lang, target_lang, preserve_terms, retries=TRANSLATION_RETRIES):
    term_map = {}
    for i, term in enumerate(preserve_terms):
        placeholder = f"TERM_{i}_X"
        chunk = chunk.replace(term, placeholder)
        term_map[placeholder] = term

    for attempt in range(retries):
        try:
            response = requests.post(
                f"{LIBRETRANSLATE_URL}/translate",
                json={"q": chunk, "source": source_lang, "target": target_lang},
                timeout=TRANSLATION_TIMEOUT
            )
            translated = response.json().get("translatedText", chunk)
            for placeholder, term in term_map.items():
                translated = translated.replace(placeholder, term)
            return translated
        except Exception as e:
            logger.error(f"Translation failed (attempt {attempt+1}/{retries}): {str(e)}")
            time.sleep(2)
    return chunk

# --- API: Fetch Transcript ---
@app.route("/fetch_transcript", methods=["POST"])
def fetch_transcript():
    data = request.get_json()
    video_url = data.get("video_url", "").strip()
    video_id = extract_video_id(video_url)

    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    transcript = get_transcript(video_id)
    if not transcript:
        return jsonify({"error": "Transcript not available"}), 404

    source_lang = detect_language(transcript)

    words = set(re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", transcript))
    preserve_terms = sorted(words)

    return jsonify({
        "transcript": transcript,
        "source_lang": source_lang,
        "suggested_terms": preserve_terms
    })

# --- API: Translate Transcript ---
@app.route("/translate_transcript", methods=["POST"])
def translate_transcript():
    data = request.get_json()
    transcript = data.get("transcript", "").strip()
    source_lang = data.get("source_lang", "auto")
    target_lang = data.get("target_lang", "en")
    preserve_terms = data.get("preserve_terms", [])

    if not transcript:
        return jsonify({"error": "Transcript is empty"}), 400

    start_time = time.time()
    chunks = [transcript[i:i+CHUNK_SIZE] for i in range(0, len(transcript), CHUNK_SIZE)]
    translated_chunks = [translate_chunk(c, source_lang, target_lang, preserve_terms) for c in chunks]

    processing_time = round(time.time() - start_time, 2)
    logger.info(f"Translated {len(chunks)} chunks in {processing_time}s")

    return jsonify({
        "translated": " ".join(translated_chunks),
        "processing_time": processing_time
    })

# --- Home ---
@app.route("/")
def home():
    return render_template("t_index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)