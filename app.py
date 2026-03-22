"""
============================================================
  JECRC Foundation - College Helpdesk AI Chatbot
  Main Flask Application
  Project: J-TECHTRIX 7.0

  🔧 UPDATED:
  - Admin authentication (login/logout)
  - Rate limiting
  - Input sanitization
  - Voice chat (AssemblyAI + gTTS)
  - 🔥 Text-to-Speech API route
  - 🔥 Format choice support (text/speech/both)
  - 🌐 NEW: Multi-Language Support (Hindi/English)
  - 🌐 NEW: Language toggle API
  - 🌐 NEW: Auto language detection

  Run: python app.py
  Visit: http://localhost:5000
============================================================
"""

from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
from collections import defaultdict
import uuid
import datetime
import time
import html
import os
import requests
from dotenv import load_dotenv

# Load env files
load_dotenv('.env')
load_dotenv('api.env')

from config import Config
from chatbot_engine import ChatbotEngine
from database import ChatDatabase
from web_scraper import WebScraper

# ── Initialize Flask App ──
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# ── Initialize Components ──
print("\n" + "=" * 60)
print("🤖 JECRC Foundation Helpdesk AI Chatbot")
print("📌 Project: J-TECHTRIX 7.0")
print("🌐 Multi-Language Support: Hindi + English")
print("=" * 60 + "\n")

chatbot = ChatbotEngine(
    intents_file='intents.json',
    confidence_threshold=Config.CONFIDENCE_THRESHOLD
)

database = ChatDatabase(db_path=Config.DATABASE_PATH)
scraper = WebScraper()

# Verify API keys
_aai_key = os.getenv("ASSEMBLYAI_API_KEY", "")
print(f"🎤 AssemblyAI Key: {'✅ Loaded' if _aai_key else '❌ MISSING!'}")
print(f"\n✅ All components initialized!")
print(f"🌐 Server ready at http://localhost:{Config.PORT}")
print(f"🔐 Admin: http://localhost:{Config.PORT}/admin")
print("=" * 60 + "\n")

database.cleanup_old_chats(days=90)


# ══════════════════════════════════════
# 🔧 Rate Limiting
# ══════════════════════════════════════
request_counts = defaultdict(list)
last_cleanup = time.time()


def check_rate_limit(ip):
    """Check if IP has exceeded rate limit"""
    global last_cleanup
    now = time.time()

    if now - last_cleanup > 300:
        old_ips = [k for k, v in request_counts.items()
                   if not v or now - v[-1] > 120]
        for old_ip in old_ips:
            del request_counts[old_ip]
        last_cleanup = now

    request_counts[ip] = [t for t in request_counts[ip] if now - t < 60]
    if len(request_counts[ip]) >= Config.RATE_LIMIT_PER_MINUTE:
        return False
    request_counts[ip].append(now)
    return True


# ══════════════════════════════════════
# 🔧 Admin Authentication
# ══════════════════════════════════════
def admin_required(f):
    """Protect admin routes with login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            if request.path.startswith('/api/admin'):
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'Admin login required'
                }), 401
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# ══════════════════════════════════════
# 🎤 Speech-to-Text (AssemblyAI)
# ══════════════════════════════════════
def speech_to_text(audio_file_path):
    """Convert audio to text using AssemblyAI"""
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        print("  ❌ ASSEMBLYAI_API_KEY not found!")
        return None

    try:
        file_size = os.path.getsize(audio_file_path)
        print(f"  📁 File size: {file_size / 1024:.1f} KB")

        if file_size < 100:
            print("  ❌ File too small")
            return None

        # Step 1: Upload
        print("  🎤 Uploading to AssemblyAI...")
        with open(audio_file_path, 'rb') as f:
            file_data = f.read()

        upload_response = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers={
                "authorization": api_key,
                "content-type": "application/octet-stream"
            },
            data=file_data,
            timeout=60
        )
        print(f"  📡 Upload status: {upload_response.status_code}")

        if upload_response.status_code != 200:
            print(f"  ❌ Upload failed: {upload_response.text[:300]}")
            return None

        audio_url = upload_response.json().get('upload_url')
        if not audio_url:
            print("  ❌ No upload_url")
            return None

        print(f"  ✅ Uploaded!")

        # Step 2: Request transcription
        print("  🧠 Requesting transcription...")
        transcript_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            headers={
                "authorization": api_key,
                "content-type": "application/json"
            },
            json={
                "audio_url": audio_url,
                "speech_models": ["universal-2"]
            },
            timeout=30
        )
        print(f"  📡 Transcript status: {transcript_response.status_code}")

        if transcript_response.status_code != 200:
            print(f"  ❌ Transcript failed: {transcript_response.text[:300]}")
            return None

        transcript_id = transcript_response.json().get('id')
        if not transcript_id:
            print("  ❌ No transcript ID")
            return None

        print(f"  📝 Transcript ID: {transcript_id}")

        # Step 3: Poll for result
        print("  ⏳ Waiting for result...")
        for attempt in range(1, 91):
            time.sleep(1)
            poll = requests.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers={"authorization": api_key},
                timeout=15
            )
            result = poll.json()
            status = result.get('status')

            if status == 'completed':
                text = result.get('text', '')
                print(f"  ✅ Result: '{text}'")
                return text if text and text.strip() else None
            elif status == 'error':
                print(f"  ❌ Error: {result.get('error')}")
                return None

            if attempt % 5 == 0:
                print(f"  ⏳ {status}... ({attempt}s)")

        print("  ❌ Timeout!")
        return None

    except Exception as e:
        print(f"  ❌ STT Error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ══════════════════════════════════════
# 🔊 Text-to-Speech (Google TTS - FREE)
# ══════════════════════════════════════
# ══════════════════════════════════════
# 🔊 Text-to-Speech (Google TTS - FREE)
# ══════════════════════════════════════

def clean_text_for_speech(text):
    """
    Remove emojis and format text properly for TTS
    🔹 → bullet point (spoken naturally)
    ✅ → removed
    All emojis → stripped
    """
    import re

    if not text:
        return ""

    clean = text

    # Step 1: Remove markdown bold markers
    clean = clean.replace('**', '').replace('__', '').replace('*', '')

    # Step 1.5: 🔧 NEW - Fix number ranges for natural speech
    # "4-6 LPA" → "4 to 6 LPA"
    # "₹95,000 - ₹1,25,000" → "₹95,000 to ₹1,25,000"
    # "9:00 AM - 4:30 PM" → "9:00 AM to 4:30 PM"
    clean = re.sub(
        r'(\d[\d,.:]*)\s*[-–—]\s*([\d₹][\d,.:]*)',
        r'\1 to \2',
        clean
    )

    # Also fix standalone ranges like "85-90%" → "85 to 90%"
    clean = re.sub(
        r'(\d+)\s*[-–—]\s*(\d+)(%)',
        r'\1 to \2\3',
        clean
    )

    # Fix "₹" symbol for speech
    clean = clean.replace('₹', 'rupees ')

    # Fix "LPA" to be spoken clearly
    clean = re.sub(r'\bLPA\b', 'L P A', clean)

    # Fix "+" to "plus"
    clean = re.sub(r'(\d)\+', r'\1 plus', clean)

    # Step 2: Replace bullet-style emojis with "Point:" or just dash
    bullet_emojis = [
        '🔹', '🔸', '▪️', '▫️', '◾', '◽', '◆', '◇',
        '●', '○', '•', '►', '▸', '➤', '➜', '➡️',
        '👉', '📌', '📍', '🔘',
    ]
    for emoji in bullet_emojis:
        clean = clean.replace(emoji, ' - ')

    # Step 3: Replace numbered/label emojis with readable text
    label_replacements = {
        '1️⃣': '1.', '2️⃣': '2.', '3️⃣': '3.', '4️⃣': '4.',
        '5️⃣': '5.', '6️⃣': '6.', '7️⃣': '7.', '8️⃣': '8.',
        '9️⃣': '9.', '🔟': '10.',
        '✅': '', '❌': 'Not allowed,',
        '⚠️': 'Important,', '🚫': 'Not allowed,',
        '💡': 'Tip,', '📞': 'Phone:', '📧': 'Email:',
        '📍': 'Address:', '🌐': 'Website:',
        '📋': '', '📊': '', '📈': '', '📉': '',
        '💰': '', '💳': '', '🏦': '',
        '🎓': '', '🏛️': '', '🏫': '', '🏠': '',
        '💼': '', '🎯': '', '🎉': '', '🏆': '',
        '🤖': '', '👋': '', '😊': '', '😅': '',
        '🤔': '', '🙁': '', '👈': '', '🔥': '',
        '💚': '', '👩': '', '♿': '', '⚖️': '',
        '📜': '', '👔': '', '📱': '', '📧': '',
        '🚨': '', '🏧': '', '📅': '', '🌧️': '',
        '🍕': '', '🎂': '', '💻': '', '📡': '',
        '⚡': '', '⚙️': '', '🏗️': '', '🔒': '',
        '📝': '', '📚': '', '🔬': '', '🕐': '',
        '📶': '', '🚌': '', '🅿️': '', '🎭': '',
        '🌟': '', '🌿': '', '🏅': '', '⭐': '',
        '🇮🇳': '', '🚀': '', '🍽️': '', '🏥': '',
        '🚭': '', '👨‍🏫': '', '👨‍👩‍👧': '', '📄': '',
        '✈️': '', '🆘': '', '💬': '', '🎤': '',
        '🔊': '', '_(': '', ')_': '',
    }
    for emoji, replacement in label_replacements.items():
        clean = clean.replace(emoji, replacement)

    # Step 4: Remove ALL remaining emojis using regex
    # This catches any emoji we might have missed
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # Emoticons
        "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
        "\U0001F680-\U0001F6FF"  # Transport & Map
        "\U0001F1E0-\U0001F1FF"  # Flags
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"  # Enclosed characters
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols Extended-A
        "\U00002600-\U000026FF"  # Misc Symbols
        "\U0000FE00-\U0000FE0F"  # Variation Selectors
        "\U0000200D"             # Zero Width Joiner
        "\U00002000-\U0000200F"  # General Punctuation
        "\U0000205F-\U00002060"  # General Punctuation
        "\U00002934-\U00002935"  # Arrows
        "\U000025AA-\U000025AB"  # Small squares
        "\U000025FB-\U000025FE"  # Medium squares
        "\U00002B05-\U00002B07"  # Arrows
        "\U00002B1B-\U00002B1C"  # Large squares
        "\U00002B50"             # Star
        "\U00002B55"             # Circle
        "\U0000231A-\U0000231B"  # Watch/Hourglass
        "\U000023E9-\U000023F3"  # Media controls
        "\U000023F8-\U000023FA"  # Media controls
        "\U00003030"             # Wavy Dash
        "\U000000A9"             # Copyright
        "\U000000AE"             # Registered
        "\U00002122"             # Trademark
        "]+",
        flags=re.UNICODE
    )
    clean = emoji_pattern.sub(' ', clean)

    # Step 5: Clean up extra spaces and formatting
    clean = re.sub(r'\s*-\s*-\s*', ' - ', clean)  # Double dashes
    clean = re.sub(r'\s+', ' ', clean)              # Multiple spaces
    clean = re.sub(r'\n\s*\n', '\n', clean)         # Multiple newlines
    clean = clean.strip()

    return clean


def text_to_speech(text, language='en'):
    """
    Convert text to speech using Google TTS
    Supports Hindi ('hi') and English ('en')
    """
    try:
        from gtts import gTTS

        # 🔧 NEW: Clean text - remove emojis + markdown
        clean_text = clean_text_for_speech(text)

        if not clean_text or len(clean_text) < 2:
            clean_text = "Here is the information you requested."

        if len(clean_text) > 3000:
            clean_text = clean_text[:3000] + "..."

        # Set TTS language
        tts_lang = 'hi' if language == 'hi' else 'en'

        print(f"  🔊 Generating audio ({len(clean_text)} chars, lang={tts_lang})...")
        print(f"  🔊 Preview: {clean_text[:100]}...")

        tts = gTTS(text=clean_text, lang=tts_lang, slow=False)

        audio_filename = f"audio_{uuid.uuid4().hex[:12]}.mp3"
        audio_path = os.path.join("static", audio_filename)
        os.makedirs("static", exist_ok=True)
        tts.save(audio_path)

        audio_size = os.path.getsize(audio_path)
        print(f"  ✅ Audio ready ({audio_size / 1024:.1f} KB)")

        return f"/static/{audio_filename}"

    except Exception as e:
        print(f"  ❌ TTS Error: {e}")
        return None


# ══════════════════════════════════════
# 🎤 Voice Chat Route
# ══════════════════════════════════════
@app.route('/api/voice-chat', methods=['POST'])
def voice_chat():
    """Voice chat endpoint - with format choice + language support"""
    file_path = None
    try:
        if 'audio' not in request.files:
            return jsonify({
                "error": "No audio file received",
                "reply": "No audio received. Please try again. 🎤"
            }), 400

        audio_file = request.files['audio']
        session_id = request.form.get('session_id', str(uuid.uuid4()))
        response_format = request.form.get('response_format', 'both')
        # 🌐 NEW: Language from voice request
        language = request.form.get('language', 'auto')

        audio_file.seek(0, 2)
        file_size = audio_file.tell()
        audio_file.seek(0)

        if file_size < 500:
            return jsonify({
                "reply": "Recording too short. Speak for at least 2 seconds. 🎤",
                "user_text": "",
                "audio_url": None
            }), 400

        if file_size > 25 * 1024 * 1024:
            return jsonify({
                "reply": "Recording too long (max 25MB). 🎤",
                "user_text": "",
                "audio_url": None
            }), 400

        print(f"\n🎤 Voice Request ({file_size / 1024:.1f} KB, lang={language})")

        # Save temp file
        content_type = audio_file.content_type or 'audio/webm'
        ext = '.webm'
        if 'ogg' in content_type:
            ext = '.ogg'
        elif 'mp4' in content_type:
            ext = '.mp4'
        elif 'wav' in content_type:
            ext = '.wav'

        file_path = os.path.join(os.getcwd(), f"temp_{uuid.uuid4().hex[:12]}{ext}")
        audio_file.save(file_path)

        # Step 1: Speech → Text
        user_text = speech_to_text(file_path)

        if not user_text or not user_text.strip():
            return jsonify({
                "user_text": "",
                "reply": "Couldn't hear you. Please speak clearly and try again. 🎤",
                "audio_url": None
            })

        print(f"  🗣️ '{user_text}'")

        # Step 2: Chatbot Response (🌐 with language)
        result = chatbot.get_response(user_text, user_id=session_id, language=language)
        bot_reply = result.get('reply', 'Sorry, could not process that.')
        response_lang = result.get('language', 'en')

        print(f"  🤖 Intent: {result.get('intent')} ({result.get('confidence', 0):.0%}) | Lang: {response_lang}")

        # Step 3: Generate audio (🌐 in correct language)
        audio_url = None
        if response_format in ('speech', 'both'):
            audio_url = text_to_speech(bot_reply, language=response_lang)

        # Step 4: Save to DB
        try:
            database.save_chat(
                session_id=session_id,
                user_message=f"🎤 {user_text}",
                bot_response=bot_reply,
                intent=result.get('intent', 'voice'),
                confidence=result.get('confidence', 0.0),
                method=f"voice_{result.get('method', 'unknown')}",
                ip_address=request.remote_addr or '0.0.0.0',
                user_agent=request.headers.get('User-Agent', '')[:200]
            )
        except Exception:
            pass

        return jsonify({
            "user_text": user_text,
            "reply": bot_reply,
            "audio_url": audio_url,
            "intent": result.get('intent', ''),
            "confidence": result.get('confidence', 0.0),
            "response_format": response_format,
            "language": response_lang,
            "timestamp": datetime.datetime.now().isoformat()
        })

    except Exception as e:
        print(f"  ❌ Voice Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "reply": "Voice processing failed. Try typing instead. 😅",
            "user_text": "",
            "audio_url": None
        }), 500

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


# ══════════════════════════════════════
# 🔥 Text-to-Speech API Route
# ══════════════════════════════════════
@app.route('/api/text-to-speech', methods=['POST'])
def tts_endpoint():
    """Convert text to speech - supports multi-language"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data"}), 400

        text = data.get('text', '')
        # 🌐 NEW: Language parameter
        language = data.get('language', 'en')

        if not text or not text.strip():
            return jsonify({"error": "No text provided"}), 400

        print(f"\n🔊 TTS Request ({len(text)} chars, lang={language})")
        audio_url = text_to_speech(text, language=language)

        if audio_url:
            return jsonify({
                "audio_url": audio_url,
                "language": language,
                "status": "success"
            })
        else:
            return jsonify({
                "error": "Audio generation failed",
                "status": "error"
            }), 500

    except Exception as e:
        print(f"  ❌ TTS endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════
# 🌐 NEW: Language API Routes
# ══════════════════════════════════════
@app.route('/api/set-language', methods=['POST'])
def set_language():
    """Set language preference for a user session"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data"}), 400

        language = data.get('language', 'en')
        session_id = data.get('session_id', str(uuid.uuid4()))

        if language not in ['en', 'hi', 'auto']:
            return jsonify({
                "error": "Unsupported language. Use 'en', 'hi', or 'auto'."
            }), 400

        # Set in chatbot engine
        if language != 'auto':
            chatbot.set_user_language(session_id, language)

        # Also store in Flask session
        session['language'] = language

        print(f"🌐 Language set: {session_id} → {language}")

        return jsonify({
            "status": "success",
            "language": language,
            "message": f"Language set to {'Hindi' if language == 'hi' else 'English' if language == 'en' else 'Auto-detect'}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/get-language', methods=['GET'])
def get_language():
    """Get current language preference"""
    try:
        session_id = request.args.get('session_id', '')
        language = 'en'

        if session_id:
            language = chatbot.get_user_language(session_id)
        elif 'language' in session:
            language = session['language']

        return jsonify({
            "language": language,
            "supported_languages": [
                {"code": "en", "name": "English", "native": "English"},
                {"code": "hi", "name": "Hindi", "native": "हिंदी"},
                {"code": "auto", "name": "Auto-Detect", "native": "Auto"}
            ]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════
# 🧹 Cleanup Old Audio Files
# ══════════════════════════════════════
@app.route('/api/admin/cleanup-audio', methods=['POST'])
@admin_required
def cleanup_audio():
    """Remove old generated audio files from static folder"""
    try:
        count = 0
        now = time.time()
        static_dir = "static"
        for filename in os.listdir(static_dir):
            if filename.startswith("audio_") and filename.endswith(".mp3"):
                filepath = os.path.join(static_dir, filename)
                if now - os.path.getmtime(filepath) > 3600:
                    os.remove(filepath)
                    count += 1
        return jsonify({
            "status": "success",
            "message": f"Cleaned up {count} old audio files"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ══════════════════════════════════════
# ROUTES - Main Pages
# ══════════════════════════════════════
@app.route('/')
def home():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html', config=Config)


@app.route('/widget')
def widget():
    return render_template('chatbot_widget.html', config=Config)


# ══════════════════════════════════════
# Admin Login/Logout Routes
# ══════════════════════════════════════
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            session['admin_login_time'] = datetime.datetime.now().isoformat()
            print(f"✅ Admin login: {username} from {request.remote_addr}")
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Invalid username or password!"
            print(f"❌ Failed admin login attempt from {request.remote_addr}")

    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_login.html', error=error, config=Config)


@app.route('/admin/logout')
def admin_logout():
    username = session.get('admin_username', 'unknown')
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    session.pop('admin_login_time', None)
    print(f"👋 Admin logout: {username}")
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin.html', config=Config)


# ══════════════════════════════════════
# API ROUTES - Chat (🌐 UPDATED)
# ══════════════════════════════════════
@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat API - 🌐 with multi-language support"""
    try:
        ip = request.remote_addr or '0.0.0.0'
        if not check_rate_limit(ip):
            return jsonify({
                'error': 'Rate limit exceeded',
                'reply': 'Thoda slow karo! 😅 Please wait a moment.'
            }), 429

        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({
                'error': 'No message provided',
                'reply': 'Please send a message!'
            }), 400

        user_message = html.escape(data['message'].strip())
        session_id = data.get('session_id', str(uuid.uuid4()))

        # 🌐 NEW: Get language preference from request
        language = data.get('language', 'auto')

        if len(user_message) > Config.MAX_MESSAGE_LENGTH:
            return jsonify({
                'reply': f'Message too long! Keep it under {Config.MAX_MESSAGE_LENGTH} chars. 📝',
                'intent': 'error',
                'confidence': 0.0,
                'method': 'validation',
                'language': language
            }), 400

        if not user_message:
            return jsonify({
                'reply': 'Please type something! 😊',
                'intent': 'empty',
                'confidence': 0.0,
                'method': 'validation',
                'language': language
            })

        # 🌐 UPDATED: Pass language to chatbot engine
        result = chatbot.get_response(
            user_message,
            user_id=session_id,
            language=language
        )

        chat_id = database.save_chat(
            session_id=session_id,
            user_message=user_message,
            bot_response=result['reply'],
            intent=result['intent'],
            confidence=result['confidence'],
            method=result['method'],
            ip_address=ip,
            user_agent=request.headers.get('User-Agent', '')[:200]
        )

        return jsonify({
            'reply': result['reply'],
            'intent': result['intent'],
            'confidence': result['confidence'],
            'method': result['method'],
            'chat_id': chat_id,
            'session_id': session_id,
            'language': result.get('language', 'en'),
            'timestamp': datetime.datetime.now().isoformat()
        })

    except Exception as e:
        print(f"❌ Chat API error: {e}")
        return jsonify({
            'error': str(e),
            'reply': 'Sorry, something went wrong. Please try again! 🙏'
        }), 500


@app.route('/api/feedback', methods=['POST'])
def feedback():
    try:
        data = request.get_json()
        chat_id = data.get('chat_id')
        rating = data.get('rating', 3)
        comment = html.escape(data.get('comment', ''))

        if chat_id:
            database.save_feedback(chat_id, rating, comment)
            return jsonify({'status': 'success', 'message': 'Thank you! 🙏'})
        return jsonify({'status': 'error', 'message': 'Missing chat_id'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ══════════════════════════════════════
# API ROUTES - Admin (PROTECTED)
# ══════════════════════════════════════
@app.route('/api/admin/analytics', methods=['GET'])
@admin_required
def analytics():
    try:
        data = database.get_analytics()
        stats = chatbot.get_stats()
        data['chatbot_stats'] = stats
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/history', methods=['GET'])
@admin_required
def chat_history():
    try:
        limit = request.args.get('limit', Config.MAX_CHAT_HISTORY, type=int)
        session_id = request.args.get('session_id', None)
        history = database.get_chat_history(session_id=session_id, limit=limit)
        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/scrape', methods=['POST'])
@admin_required
def trigger_scrape():
    try:
        data = scraper.scrape_all()
        return jsonify({
            'status': 'success',
            'message': 'Website scraped successfully!',
            'sections': len(data)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/admin/resolve', methods=['POST'])
@admin_required
def resolve_query():
    try:
        data = request.get_json()
        query_id = data.get('query_id')
        admin_response = html.escape(data.get('response', ''))
        database.resolve_query(query_id, admin_response)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ══════════════════════════════════════
# API ROUTES - Info (🌐 UPDATED)
# ══════════════════════════════════════
@app.route('/api/info', methods=['GET'])
def info():
    return jsonify({
        'name': Config.BOT_NAME,
        'college': Config.COLLEGE_NAME,
        'version': '1.1.0',
        'project': 'J-TECHTRIX 7.0',
        'features': {
            'multi_language': True,
            'supported_languages': ['en', 'hi', 'auto'],
            'voice_chat': True,
            'text_to_speech': True
        },
        'stats': chatbot.get_stats()
    })


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'languages': ['en', 'hi']
    })


# ══════════════════════════════════════
# Error Handlers
# ══════════════════════════════════════
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'API endpoint not found'}), 404
    return render_template('index.html', config=Config)


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500


# ══════════════════════════════════════
# Run Application
# ══════════════════════════════════════
if __name__ == '__main__':
    print(f"\n🚀 Starting JECRC Foundation Helpdesk AI Chatbot...")
    print(f"🌐 Open: http://localhost:{Config.PORT}")
    print(f"🔐 Admin: http://localhost:{Config.PORT}/admin/login")
    print(f"🔧 Chat API: http://localhost:{Config.PORT}/api/chat")
    print(f"🎤 Voice API: http://localhost:{Config.PORT}/api/voice-chat")
    print(f"🔊 TTS API: http://localhost:{Config.PORT}/api/text-to-speech")
    print(f"🌐 Language API: http://localhost:{Config.PORT}/api/set-language")
    print(f"🌐 Languages: English 🇬🇧 + Hindi 🇮🇳 + Auto-detect 🤖")
    print(f"\nPress Ctrl+C to stop.\n")

    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
