# 🎥 YouTube Transcript Translator

A Flask-based web application that:
- Fetches YouTube video transcripts using [`youtube-transcript-api`](https://pypi.org/project/youtube-transcript-api/).
- Detects the language of the transcript via [LibreTranslate](https://libretranslate.com/).
- Translates the transcript into your target language.
- Allows you to preserve proper nouns or specific terms during translation.
- Supports proxy usage via [Webshare.io](https://proxy.webshare.io/).

---

## 🚀 Features
- **Automatic Transcript Retrieval**: Works with regular YouTube URLs, Shorts, or direct video IDs.
- **Language Detection**: Uses LibreTranslate's `/detect` API.
- **Customizable Translation**: Translate to any supported target language.
- **Term Preservation**: Avoids translating certain words/phrases (like names, brands).
- **Proxy Support**: Useful for restricted environments.

---

## 📦 Requirements

- Python **3.9+**
- pip
- LibreTranslate instance (local or hosted)
- (Optional) Webshare Proxy account for YouTube API calls

---

## 🔧 Installation

1. **Clone this repository**
   ```bash
   git clone https://github.com/yourusername/youtube-transcript-translator.git
   cd youtube-transcript-translator

2. **Create a virtual environment**
   '''bash
    python -m venv venv
    source venv/bin/activate    # On Linux/Mac
    venv\Scripts\activate       # On Windows

3. **Install dependencies**
'''bash
    pip install -r requirements.txt

4. **Create a .env file in the project root:**
'''bash
    LIBRETRANSLATE_URL=http://localhost:5000
    WEBPROXY_USER=your_webshare_username
    WEBPROXY_PASS=your_webshare_password


5. **Running Locally**
'''bash
    python app.py