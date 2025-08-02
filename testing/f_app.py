from flask import Flask, render_template, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from concurrent.futures import ThreadPoolExecutor
import requests
import re
import logging
from functools import lru_cache
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

# Configuration
LIBRETRANSLATE_URL = "https://translate.shabeerkhan.com"
MAX_WORKERS = 4  # Number of parallel translation threads
CHUNK_SIZE = 350  # Optimal balance between speed and stability
CACHE_SIZE = 100  # Number of transcripts to cache

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@lru_cache(maxsize=CACHE_SIZE)
def get_transcript(video_id):
    """Fetch and cache YouTube transcripts"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id) # Fetch transcript in default language : languages=['en']
        if not transcript:
            logger.error(f"No transcript found for video ID: {video_id}")
            return None
        # Join all text entries into a single string
        return " ".join([entry['text'] for entry in transcript])
    except Exception as e:
        logger.error(f"Transcript error for {video_id}: {str(e)}")
        return None

def translate_chunk(chunk, target_lang, preserve_terms):
    """Translate a text chunk with term preservation"""
    # Create term mapping
    term_map = {}
    for i, term in enumerate(preserve_terms):
        placeholder = f"TERM_{i}_X"
        chunk = chunk.replace(term, placeholder)
        term_map[placeholder] = term
    
    try:
        response = requests.post(
            f"{LIBRETRANSLATE_URL}/translate",
            json={
                'q': chunk,
                'source': 'auto', # Automatically detect source language
                'target': target_lang
            },
            timeout=10
        )
        translated = response.json().get('translatedText', chunk)
        
        # Restore preserved terms
        for placeholder, term in term_map.items():
            translated = translated.replace(placeholder, term)
            
        return translated
    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        return chunk  # Fallback to original text

@app.route('/translate', methods=['POST'])
def handle_translation():
    start_time = time.time()
    data = request.get_json()
    
    # Input validation
    video_url = data.get('video_url', '').strip()
    target_lang = data.get('target_lang', 'es').strip()
    preserve_terms = [t.strip() for t in data.get('preserve_terms', []) if t.strip()]
    
    # Extract video ID
    video_id = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', video_url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    video_id = video_id.group(1)
    
    # Get transcript
    transcript = get_transcript(video_id)
    if not transcript:
        return jsonify({'error': 'Transcript not available'}), 404
    
    # Split into chunks
    chunks = [transcript[i:i+CHUNK_SIZE] for i in range(0, len(transcript), CHUNK_SIZE)]
    
    # Parallel translation
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for chunk in chunks:
            future = executor.submit(
                translate_chunk,
                chunk,
                target_lang,
                preserve_terms
            )
            futures.append(future)
        
        translated_chunks = [future.result() for future in futures]
    
    logger.info(f"Translated {len(chunks)} chunks in {time.time()-start_time:.2f}s")
    
    return jsonify({
        'original': transcript,
        'translated': ' '.join(translated_chunks),
        'status': 'success',
        'processing_time': round(time.time()-start_time, 2)
    })

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)