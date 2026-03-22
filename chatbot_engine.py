"""
JECRC Foundation - College Helpdesk AI Chatbot
NLP Engine - The AI Brain
Project: J-TECHTRIX 7.0

Features:
- TF-IDF + Cosine Similarity for Intent Classification
- Keyword Matching Fallback
- Hinglish (Hindi-English) Support
- 🔧 Advanced Typo Tolerance (Fuzzy Matching)
- 🔧 Smart "Please Retype" Detection
- Context-Aware Responses
- Hybrid Classification (TF-IDF + Keyword Together)
- 🌐 NEW: Multi-Language Support (Hindi/English)
- 🌐 NEW: Auto Language Detection
"""

import json
import random
import re
import string
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt_tab')
except (LookupError, OSError):
    try:
        nltk.download('punkt_tab', quiet=True)
    except Exception:
        pass

try:
    nltk.data.find('tokenizers/punkt')
except (LookupError, OSError):
    try:
        nltk.download('punkt', quiet=True)
    except Exception:
        pass

try:
    nltk.data.find('corpora/wordnet')
except (LookupError, OSError):
    try:
        nltk.download('wordnet', quiet=True)
    except Exception:
        pass


class ChatbotEngine:
    """
    NLP-based Chatbot Engine for JECRC Foundation Helpdesk
    🌐 NEW: Multi-Language Support (Hindi/English)
    """

    def __init__(self, intents_file='intents.json', confidence_threshold=0.35):
        """Initialize the chatbot engine"""
        self.lemmatizer = WordNetLemmatizer()
        self.confidence_threshold = confidence_threshold
        self.high_confidence_threshold = 0.80

        self.intents = None
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=8000,
            sublinear_tf=True
        )
        self.intent_vectors = None
        self.pattern_intent_map = []
        self.all_patterns = []
        self.context = {}
        self.conversation_history = {}

        # ═══════════════════════════════════════
        # 🌐 NEW: Language Settings
        # ═══════════════════════════════════════
        self.user_language = {}  # user_id → 'en' or 'hi'
        self.supported_languages = ['en', 'hi']
        self.default_language = 'en'

        # Hindi detection keywords
        self.hindi_indicators = {
            'kya', 'hai', 'kaise', 'kab', 'kahan', 'kaun', 'kitna', 'kitne',
            'kitni', 'kyun', 'konsa', 'mujhe', 'mera', 'meri', 'hum', 'aap',
            'batao', 'bataiye', 'bataye', 'chahiye', 'hoga', 'hogi', 'tha',
            'thi', 'the', 'karo', 'karna', 'milega', 'milegi', 'milta',
            'padhai', 'paisa', 'naukri', 'nokri', 'hostal', 'khana',
            'dawakhana', 'chutti', 'achha', 'theek', 'bahut', 'abhi',
            'pehle', 'baad', 'sab', 'koi', 'aur', 'bhi', 'se', 'ka',
            'ki', 'ke', 'ko', 'ne', 'par', 'pe', 'mein', 'yeh', 'woh',
            'toh', 'nahi', 'nhi', 'haan', 'ji', 'matlab', 'yaani',
            'lekin', 'agar', 'toh', 'phir', 'abhi', 'sala', 'yaar',
            'bhai', 'dost', 'accha', 'sahi', 'galat', 'pata', 'samajh',
            'samjha', 'samjhao', 'dekho', 'suno', 'bolo', 'jao', 'aao',
            'lo', 'do', 'lao', 'dikhao', 'padhna', 'likhna', 'sunna',
            'jaana', 'aana', 'dena', 'lena', 'khelna', 'sochna',
            'fees', 'admission', 'hostel', 'placement',  # common in Hinglish too
            'kaisa', 'kaisi', 'kahan', 'kidhar', 'idhar', 'udhar',
            'wahan', 'yahan', 'tab', 'jab', 'kal', 'aaj', 'parso',
            'subah', 'shaam', 'raat', 'din', 'mahina', 'saal',
        }

        # ═══════════════════════════════════════
        # 🔧 Typo Corrections Database
        # ═══════════════════════════════════════
        self.typo_corrections = {
            # Admission related typos
            'addmission': 'admission', 'admision': 'admission',
            'admisson': 'admission', 'admissin': 'admission',
            'admisin': 'admission', 'addmision': 'admission',
            'admissoin': 'admission', 'admisssion': 'admission',
            'admishn': 'admission', 'edmission': 'admission',
            # Fee related typos
            'fess': 'fees', 'feee': 'fees', 'feees': 'fees',
            'fes': 'fees', 'feis': 'fees', 'fese': 'fees',
            'pees': 'fees', 'phees': 'fees', 'phes': 'fees',
            'fis': 'fees', 'fii': 'fee', 'fie': 'fee',
            # Placement related typos
            'placment': 'placement', 'plcment': 'placement',
            'plcement': 'placement', 'placemnt': 'placement',
            'plecement': 'placement', 'plasment': 'placement',
            'placemnet': 'placement', 'placemet': 'placement',
            'plasmnt': 'placement',
            # Scholarship typos
            'scholarshp': 'scholarship', 'scholorship': 'scholarship',
            'scholarhip': 'scholarship', 'scholarshup': 'scholarship',
            'scolorship': 'scholarship', 'scholarsip': 'scholarship',
            'sclrship': 'scholarship', 'scholarshiop': 'scholarship',
            # Hostel typos
            'hostle': 'hostel', 'hostl': 'hostel', 'hostol': 'hostel',
            'hostell': 'hostel', 'hosel': 'hostel', 'hstel': 'hostel',
            'hostal': 'hostel', 'hoselt': 'hostel', 'hosteel': 'hostel',
            # Attendance typos
            'attendence': 'attendance', 'attendace': 'attendance',
            'attandance': 'attendance', 'attendense': 'attendance',
            'atendance': 'attendance', 'attendnce': 'attendance',
            'attendanc': 'attendance', 'attendens': 'attendance',
            # Department typos
            'deparment': 'department', 'departmnt': 'department',
            'depatment': 'department', 'departmet': 'department',
            'deprtment': 'department', 'departemnt': 'department',
            # Syllabus typos
            'syllabu': 'syllabus', 'syllabs': 'syllabus',
            'sylabus': 'syllabus', 'syllebus': 'syllabus',
            'syllbus': 'syllabus', 'sillabus': 'syllabus',
            'silabus': 'syllabus', 'syllabas': 'syllabus',
            # Timetable typos
            'timetabel': 'timetable', 'timtable': 'timetable',
            'timatable': 'timetable', 'timetble': 'timetable',
            'timetabl': 'timetable', 'timtabel': 'timetable',
            # Canteen typos
            'cantin': 'canteen', 'canten': 'canteen',
            'cantten': 'canteen', 'cafetaria': 'cafeteria',
            'cafetria': 'cafeteria', 'cafeterea': 'cafeteria',
            'cafetiria': 'cafeteria',
            # Library typos
            'librery': 'library', 'laibrary': 'library',
            'libary': 'library', 'libarary': 'library',
            'liberary': 'library', 'librry': 'library',
            'libray': 'library', 'liberry': 'library',
            # Exam typos
            'examm': 'exam', 'exaam': 'exam', 'exma': 'exam',
            'exams': 'exam', 'exm': 'exam', 'examn': 'exam',
            # Ragging typos
            'raging': 'ragging', 'ragin': 'ragging',
            'raggin': 'ragging', 'rgging': 'ragging',
            # Complaint typos
            'complain': 'complaint', 'complant': 'complaint',
            'complait': 'complaint', 'compalint': 'complaint',
            'compaint': 'complaint', 'cmplaint': 'complaint',
            # Internship typos
            'intership': 'internship', 'internshp': 'internship',
            'intrnship': 'internship', 'internshiip': 'internship',
            'internsip': 'internship', 'intenrship': 'internship',
            # Result typos
            'reult': 'result', 'reslt': 'result', 'rsult': 'result',
            'rezult': 'result', 'reasult': 'result', 'resut': 'result',
            # Transport typos
            'tranport': 'transport', 'transort': 'transport',
            'transprt': 'transport', 'trnsport': 'transport',
            # Accreditation typos
            'accredation': 'accreditation', 'acreditation': 'accreditation',
            'acreditaion': 'accreditation', 'accredtation': 'accreditation',
            # Certificate typos
            'certificte': 'certificate', 'certifcate': 'certificate',
            'cirtificate': 'certificate', 'sertificate': 'certificate',
            # Eligibility typos
            'elegibility': 'eligibility', 'eligiblity': 'eligibility',
            'eligibilty': 'eligibility', 'elgibility': 'eligibility',
            'eligibity': 'eligibility', 'eligblity': 'eligibility',
            # Course typos
            'corse': 'course', 'coures': 'course', 'cource': 'course',
            'coarse': 'course', 'courss': 'course',
            # Branch typos
            'brach': 'branch', 'barnch': 'branch', 'brnch': 'branch',
            'braanch': 'branch',
            # College typos
            'colege': 'college', 'collage': 'college', 'colleg': 'college',
            'collge': 'college', 'colleeg': 'college',
            # Engineering typos
            'enginnering': 'engineering', 'engneering': 'engineering',
            'enginering': 'engineering', 'enginring': 'engineering',
            'engineerng': 'engineering', 'engg': 'engineering',
            # Computer typos
            'compter': 'computer', 'computr': 'computer',
            'comuter': 'computer', 'compueter': 'computer',
            'compuutr': 'computer',
            # Science typos
            'sciene': 'science', 'scince': 'science',
            'scienc': 'science', 'sicence': 'science',
            # Mechanical typos
            'mechancal': 'mechanical', 'mechnaical': 'mechanical',
            'mechancial': 'mechanical', 'mechanicl': 'mechanical',
            # Electrical typos
            'electricl': 'electrical', 'electrcal': 'electrical',
            'electrial': 'electrical', 'electirical': 'electrical',
            # Electronics typos
            'elctronics': 'electronics', 'electroncs': 'electronics',
            'elecrtonics': 'electronics', 'electonics': 'electronics',
            # Sports typos
            'sprots': 'sports', 'spors': 'sports',
            'spoerts': 'sports', 'spports': 'sports',
            # Parking typos
            'parkin': 'parking', 'pakring': 'parking', 'prking': 'parking',
            # Medical typos
            'medcal': 'medical', 'medicl': 'medical', 'mdical': 'medical',
            # WiFi typos
            'wfi': 'wifi', 'wify': 'wifi', 'wie-fi': 'wifi', 'wifii': 'wifi',
            # Alumni typos
            'alumini': 'alumni', 'almuni': 'alumni',
            'alumai': 'alumni', 'alumi': 'alumni',
            # JECRC typos
            'jercr': 'jecrc', 'jerc': 'jecrc', 'jercc': 'jecrc',
            'jcrc': 'jecrc', 'jecr': 'jecrc', 'jecrcc': 'jecrc',
            # Counselling typos
            'counsling': 'counselling', 'counseling': 'counselling',
            'cunselling': 'counselling', 'counselin': 'counselling',
            # Backlog typos
            'baklog': 'backlog', 'backlo': 'backlog',
            'baclog': 'backlog', 'bcklog': 'backlog', 'baklogg': 'backlog',
            # Grievance typos
            'greivance': 'grievance', 'greviance': 'grievance',
            'greivence': 'grievance', 'grevance': 'grievance',
            # Convocation typos
            'convacation': 'convocation', 'convocaton': 'convocation',
            'convocaion': 'convocation', 'convokation': 'convocation',
            # Common Hindi-English misspellings
            'kaise': 'how', 'kese': 'how',
            'kitna': 'how much', 'kitne': 'how many',
            'kitni': 'how much', 'chahiye': 'need',
            'chaiye': 'need', 'chahie': 'need',
            'batao': 'tell', 'btao': 'tell', 'batayo': 'tell',
            'milega': 'available', 'millega': 'available',
            'milga': 'available',
        }

        # Hinglish word mappings
        self.hinglish_map = {
            'kaise': 'how', 'kya': 'what', 'kab': 'when',
            'kahan': 'where', 'kaun': 'who', 'kitna': 'how much',
            'kitne': 'how many', 'kitni': 'how much', 'kyun': 'why',
            'konsa': 'which', 'chahiye': 'need want', 'hai': 'is',
            'hain': 'are', 'tha': 'was', 'hoga': 'will be',
            'batao': 'tell', 'bataiye': 'tell', 'bataye': 'tell',
            'milega': 'available get', 'milegi': 'available get',
            'milta': 'available', 'karna': 'do', 'lena': 'take',
            'dena': 'give', 'janna': 'know',
            'padhai': 'study academics', 'paisa': 'fee money',
            'naukri': 'job placement', 'nokri': 'job placement',
            'parhai': 'study', 'hostal': 'hostel',
            'khana': 'food mess', 'bus': 'transport bus',
            'gaadi': 'vehicle transport', 'dawakhana': 'medical hospital',
            'doctor': 'medical doctor', 'chutti': 'holiday leave',
            'safai': 'cleanliness', 'mujhe': 'i need me',
            'mera': 'my', 'meri': 'my', 'hum': 'we',
            'aap': 'you', 'unka': 'their', 'achha': 'good',
            'theek': 'okay fine', 'bahut': 'very much',
            'abhi': 'now', 'pehle': 'first before',
            'baad': 'after later', 'sab': 'all',
            'koi': 'any someone',
        }

        # ═══════════════════════════════════════
        # 🔧 NEW: Devanagari → English Keyword Map
        # (For Hindi voice input recognition)
        # ═══════════════════════════════════════
        self.devanagari_keyword_map = {
            # College-related
            'क्लब': 'club clubs', 'क्लब्स': 'clubs', 'क्लबों': 'clubs',
            'एडमिशन': 'admission', 'दाखिला': 'admission',
            'फीस': 'fees fee', 'शुल्क': 'fees fee',
            'प्लेसमेंट': 'placement', 'नौकरी': 'job placement',
            'हॉस्टल': 'hostel', 'छात्रावास': 'hostel',
            'कॉलेज': 'college jecrc', 'विश्वविद्यालय': 'university',
            'कोर्स': 'course', 'पाठ्यक्रम': 'course',
            'ब्रांच': 'branch department', 'शाखा': 'branch',
            'डिपार्टमेंट': 'department', 'विभाग': 'department',
            'परीक्षा': 'exam examination', 'एग्जाम': 'exam',
            'सिलेबस': 'syllabus', 'पाठ्यक्रम': 'syllabus',
            'लाइब्रेरी': 'library', 'पुस्तकालय': 'library',
            'कैंपस': 'campus', 'परिसर': 'campus',

            # Facilities
            'स्पोर्ट्स': 'sports', 'खेल': 'sports games',
            'बस': 'bus transport', 'ट्रांसपोर्ट': 'transport',
            'पार्किंग': 'parking',
            'वाईफाई': 'wifi', 'इंटरनेट': 'internet wifi',
            'मेडिकल': 'medical', 'डॉक्टर': 'doctor medical',
            'अस्पताल': 'hospital medical',
            'कैंटीन': 'canteen food', 'मेस': 'mess food',
            'खाना': 'food mess canteen', 'भोजन': 'food mess',
            'ऑडिटोरियम': 'auditorium', 'सभागार': 'auditorium',
            'लैब': 'lab laboratory', 'प्रयोगशाला': 'lab laboratory',
            'जिम': 'gym sports',

            # Academics
            'अटेंडेंस': 'attendance', 'उपस्थिति': 'attendance',
            'रिजल्ट': 'result', 'परिणाम': 'result',
            'बैकलॉग': 'backlog', 'सप्लीमेंट्री': 'supplementary backlog',
            'टाइमटेबल': 'timetable schedule',
            'समय': 'timing timetable', 'सारणी': 'timetable',
            'सेमेस्टर': 'semester',
            'प्रोजेक्ट': 'project', 'परियोजना': 'project',
            'असाइनमेंट': 'assignment',

            # Financial
            'स्कॉलरशिप': 'scholarship', 'छात्रवृत्ति': 'scholarship',
            'लोन': 'loan education', 'ऋण': 'loan',
            'रिफंड': 'refund',
            'पैकेज': 'package placement salary',
            'सैलरी': 'salary package',

            # People
            'प्रिंसिपल': 'principal director',
            'डायरेक्टर': 'director principal',
            'चेयरमैन': 'chairman management',
            'फैकल्टी': 'faculty teacher professor',
            'प्रोफेसर': 'professor faculty teacher',
            'टीचर': 'teacher faculty',
            'शिक्षक': 'teacher faculty',
            'एलुमनाई': 'alumni', 'पूर्व': 'alumni former',

            # Activities
            'इवेंट': 'event fest', 'कार्यक्रम': 'event',
            'फेस्ट': 'fest event', 'उत्सव': 'fest event',
            'सोसाइटी': 'society clubs',
            'रोबोटिक्स': 'robotics club',
            'कोडिंग': 'coding club programming',
            'हैकाथॉन': 'hackathon coding',
            'स्टार्टअप': 'startup entrepreneurship',
            'इंटर्नशिप': 'internship training',
            'ट्रेनिंग': 'training placement',
            'सेमिनार': 'seminar', 'वर्कशॉप': 'workshop',

            # Safety / Rules
            'रैगिंग': 'ragging', 'शिकायत': 'complaint grievance',
            'समस्या': 'problem complaint',
            'नियम': 'rules discipline',
            'ड्रेस': 'dress code uniform',
            'यूनिफॉर्म': 'uniform dress code',
            'सुरक्षा': 'safety security',
            'आपातकालीन': 'emergency',

            # Certificates
            'सर्टिफिकेट': 'certificate',
            'प्रमाणपत्र': 'certificate',
            'कन्वोकेशन': 'convocation degree',
            'डिग्री': 'degree convocation',
            'दीक्षांत': 'convocation',

            # Research
            'रिसर्च': 'research', 'अनुसंधान': 'research',
            'पेटेंट': 'patent research',

            # Contact
            'संपर्क': 'contact', 'फोन': 'phone contact',
            'ईमेल': 'email contact',
            'पता': 'address location',
            'वेबसाइट': 'website',

            # Common Hindi words → intent helpers
            'कैसे': 'how', 'कैसा': 'how', 'कैसी': 'how',
            'कितना': 'how much', 'कितनी': 'how much', 'कितने': 'how many',
            'कब': 'when', 'कहाँ': 'where', 'कहां': 'where',
            'क्या': 'what', 'कौन': 'who', 'कौनसा': 'which',
            'बताओ': 'tell about', 'बताइए': 'tell about',
            'बताएं': 'tell about', 'बतायें': 'tell about',
            'जानकारी': 'information details',
            'सुविधा': 'facility', 'सुविधाएं': 'facilities',
            'सुविधाएँ': 'facilities',
            'प्रक्रिया': 'process', 'तरीका': 'process method',
            'पात्रता': 'eligibility',
            'दस्तावेज': 'documents', 'दस्तावेज़': 'documents',
            'फॉर्म': 'form application',
            'आवेदन': 'apply application',
            'मदद': 'help', 'सहायता': 'help',
            'में': 'in', 'है': 'is', 'हैं': 'are',
            'के': 'of', 'का': 'of', 'की': 'of',
            'और': 'and', 'या': 'or',
            'अच्छा': 'good', 'बेहतर': 'better',
            'उपलब्ध': 'available', 'मिलेगा': 'available get',
            'कौनसी': 'which', 'कौनसे': 'which',
            'छुट्टी': 'holiday vacation leave',
            'छुट्टियां': 'holidays vacation',
        }

        # Load intents
        self._load_intents(intents_file)
        self._build_vocabulary()
        self._train()

        print(f"🤖 {self.__class__.__name__} initialized successfully!")
        print(f"  📝 Typo corrections loaded: {len(self.typo_corrections)}")
        print(f"  📝 Vocabulary words: {len(self.vocabulary)}")
        print(f"  🌐 Languages supported: {self.supported_languages}")

    # ═══════════════════════════════════════
    # 🌐 NEW: Language Detection
    # ═══════════════════════════════════════
    def detect_language(self, text):
        """
        Auto-detect if the message is in Hindi/Hinglish or English
        Returns: 'hi' or 'en'
        """
        if not text:
            return 'en'

        text_lower = text.lower().strip()
        words = text_lower.split()

        if not words:
            return 'en'

        # Check for Devanagari script (pure Hindi)
        devanagari_count = sum(1 for char in text if '\u0900' <= char <= '\u097F')
        if devanagari_count > len(text) * 0.3:
            return 'hi'

        # Check for Hindi/Hinglish indicator words
        hindi_word_count = 0
        english_word_count = 0
        total_meaningful_words = 0

        for word in words:
            clean_word = word.strip(string.punctuation).lower()
            if len(clean_word) <= 1:
                continue

            total_meaningful_words += 1

            if clean_word in self.hindi_indicators:
                hindi_word_count += 1
            elif clean_word in self.hinglish_map:
                hindi_word_count += 1
            else:
                english_word_count += 1

        if total_meaningful_words == 0:
            return 'en'

        hindi_ratio = hindi_word_count / total_meaningful_words

        # If more than 30% words are Hindi → Hindi mode
        if hindi_ratio >= 0.30:
            return 'hi'

        # Common Hinglish sentence patterns
        hinglish_patterns = [
            r'\b(kya|kaise|kab|kahan|kitna|kitne|kitni)\b',
            r'\b(hai|hain|tha|thi|hoga|hogi)\b',
            r'\b(chahiye|batao|bataiye|milega|milegi)\b',
            r'\b(mujhe|mera|meri|humko|humara)\b',
            r'\b(kaisa|kaisi|konsa|konsi)\b',
        ]

        pattern_matches = 0
        for pattern in hinglish_patterns:
            if re.search(pattern, text_lower):
                pattern_matches += 1

        if pattern_matches >= 2:
            return 'hi'

        return 'en'

    # ═══════════════════════════════════════
    # 🌐 NEW: Set/Get User Language
    # ═══════════════════════════════════════
    def set_user_language(self, user_id, language):
        """Manually set language for a user"""
        if language in self.supported_languages:
            self.user_language[user_id] = language
            print(f"  🌐 Language set: {user_id} → {language}")
            return True
        return False

    def get_user_language(self, user_id):
        """Get current language for a user"""
        return self.user_language.get(user_id, self.default_language)

    # ═══════════════════════════════════════
    # 🌐 NEW: Get Response in Correct Language
    # ═══════════════════════════════════════
    def _get_response_for_intent(self, intent_tag, language='en'):
        """Get response for the given intent tag in the specified language"""
        for intent in self.intents:
            if intent['tag'] == intent_tag:
                # 🌐 Try Hindi responses first if language is Hindi
                if language == 'hi':
                    hindi_responses = intent.get('responses_hi', [])
                    if hindi_responses:
                        return random.choice(hindi_responses)
                    # Fallback: English response with Hindi note
                    en_responses = intent.get('responses', [])
                    if en_responses:
                        response = random.choice(en_responses)
                        return response + "\n\n_(Hindi mein jawab jaldi available hoga!)_"

                # English responses
                responses = intent.get('responses', [])
                if responses:
                    return random.choice(responses)

        # Default fallback
        for intent in self.intents:
            if intent['tag'] == 'default':
                if language == 'hi':
                    hindi_responses = intent.get('responses_hi', [])
                    if hindi_responses:
                        return random.choice(hindi_responses)
                return random.choice(intent.get('responses', [
                    "I'm sorry, I couldn't understand that. Please contact JECRC Foundation at +91-141-2770232."
                ]))

        return "I'm sorry, I couldn't understand that. Please contact JECRC Foundation at +91-141-2770232 for help."

    # ═══════════════════════════════════════
    # Build Vocabulary
    # ═══════════════════════════════════════
    def _build_vocabulary(self):
        """Build vocabulary from intents for fuzzy matching"""
        self.vocabulary = set()
        for intent in self.intents:
            for pattern in intent.get('patterns', []):
                words = pattern.lower().split()
                for word in words:
                    clean = word.strip(string.punctuation)
                    if len(clean) > 2:
                        self.vocabulary.add(clean)

        important_words = {
            'admission', 'fees', 'fee', 'placement', 'hostel', 'library',
            'exam', 'result', 'syllabus', 'timetable', 'attendance',
            'scholarship', 'department', 'branch', 'course', 'college',
            'canteen', 'cafeteria', 'transport', 'bus', 'parking',
            'sports', 'wifi', 'medical', 'ragging', 'complaint',
            'grievance', 'internship', 'certificate', 'convocation',
            'alumni', 'accreditation', 'naac', 'aicte', 'eligibility',
            'backlog', 'supplementary', 'counselling', 'engineering',
            'computer', 'science', 'mechanical', 'electrical',
            'electronics', 'civil', 'jecrc', 'foundation', 'campus',
            'mess', 'faculty', 'professor', 'teacher', 'director',
            'principal', 'chairman', 'club', 'event', 'fest',
            'ncc', 'nss', 'entrepreneur', 'startup', 'research',
            'patent', 'innovation',
        }
        self.vocabulary.update(important_words)

    # ═══════════════════════════════════════
    # Levenshtein Distance
    # ═══════════════════════════════════════
    def _levenshtein_distance(self, s1, s2):
        """Calculate edit distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        prev_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = prev_row[j + 1] + 1
                deletions = curr_row[j] + 1
                substitutions = prev_row[j] + (c1 != c2)
                curr_row.append(min(insertions, deletions, substitutions))
            prev_row = curr_row
        return prev_row[-1]

    # ═══════════════════════════════════════
    # Fuzzy Match Word
    # ═══════════════════════════════════════
    def _fuzzy_match_word(self, word, max_distance=2):
        """Find closest matching word in vocabulary"""
        if not word or len(word) <= 2:
            return word, False
        word_lower = word.lower()
        if word_lower in self.vocabulary:
            return word_lower, False
        if word_lower in self.typo_corrections:
            corrected = self.typo_corrections[word_lower]
            print(f"    🔤 Typo fixed (dict): '{word}' → '{corrected}'")
            return corrected, True

        best_match = None
        best_distance = float('inf')
        if len(word_lower) <= 4:
            allowed_distance = 1
        elif len(word_lower) <= 6:
            allowed_distance = 2
        else:
            allowed_distance = min(max_distance, 3)

        for vocab_word in self.vocabulary:
            if abs(len(vocab_word) - len(word_lower)) > allowed_distance:
                continue
            if word_lower[0] == vocab_word[0] or word_lower[-1] == vocab_word[-1]:
                dist = self._levenshtein_distance(word_lower, vocab_word)
                if dist < best_distance and dist <= allowed_distance:
                    best_distance = dist
                    best_match = vocab_word

        if best_match and best_distance > 0:
            print(f"    🔤 Typo fixed (fuzzy): '{word}' → '{best_match}' (distance: {best_distance})")
            return best_match, True

        return word_lower, False

    # ═══════════════════════════════════════
    # Fix Typos
    # ═══════════════════════════════════════
    def _fix_typos(self, text):
        """Fix typos in user message"""
        if not text:
            return text, 0, [], []
        words = text.lower().strip().split()
        corrected_words = []
        corrections_made = 0
        original_list = []
        fixed_list = []

        for word in words:
            clean_word = word.strip(string.punctuation)
            if len(clean_word) <= 2:
                corrected_words.append(clean_word)
                continue
            corrected, was_corrected = self._fuzzy_match_word(clean_word)
            corrected_words.append(corrected)
            if was_corrected:
                corrections_made += 1
                original_list.append(clean_word)
                fixed_list.append(corrected)

        corrected_text = ' '.join(corrected_words)
        return corrected_text, corrections_made, original_list, fixed_list

        # Fix Typos
        corrected_text, num_corrections, original_words, fixed_words = self._fix_typos(user_message)
        if num_corrections > 0:
            print(f"  🔤 Typos fixed ({num_corrections}): {list(zip(original_words, fixed_words))}")

        # 🔧 NEW: Convert Devanagari for better matching
        devanagari_converted = self._convert_devanagari_to_english(user_message)
        if devanagari_converted != user_message:
            print(f"  🔤 Devanagari converted: '{devanagari_converted}'")
            # Use converted text for matching if original was Hindi
            if not corrected_text or corrected_text == user_message.lower():
                corrected_text = devanagari_converted

    # ═══════════════════════════════════════
    # 🔧 NEW: Devanagari to English Conversion
    # ═══════════════════════════════════════
    def _convert_devanagari_to_english(self, text):
        """
        Convert Devanagari Hindi words to English keywords
        Example: "क्लब्स कैसे है कॉलेज में" → "clubs how is college in"
        """
        if not text:
            return text

        # Check if text has any Devanagari characters
        has_devanagari = any('\u0900' <= char <= '\u097F' for char in text)
        if not has_devanagari:
            return text

        print(f"    🔤 Devanagari detected: '{text}'")

        words = text.strip().split()
        converted_words = []
        conversions_made = 0

        for word in words:
            # Clean punctuation (including Hindi purna viram ।)
            clean_word = word.strip('।,!?.\'\"()[]{}:;')

            if clean_word in self.devanagari_keyword_map:
                english = self.devanagari_keyword_map[clean_word]
                converted_words.append(english)
                conversions_made += 1
            else:
                # Try without matras/endings (partial match)
                matched = False
                for hindi_word, english_word in self.devanagari_keyword_map.items():
                    if (clean_word.startswith(hindi_word) or
                        hindi_word.startswith(clean_word)) and \
                            len(clean_word) >= 2 and len(hindi_word) >= 2:
                        # Check similarity (at least 70% overlap)
                        min_len = min(len(clean_word), len(hindi_word))
                        max_len = max(len(clean_word), len(hindi_word))
                        if min_len / max_len >= 0.6:
                            converted_words.append(english_word)
                            conversions_made += 1
                            matched = True
                            break

                if not matched:
                    converted_words.append(clean_word)

        result = ' '.join(converted_words)

        if conversions_made > 0:
            print(f"    🔤 Converted to: '{result}' ({conversions_made} words)")

        return result

    # ═══════════════════════════════════════
    # Gibberish Detection
    # ═══════════════════════════════════════
    def _is_gibberish(self, text):
        """Detect if user typed random/gibberish text"""
        if not text:
            return True
        words = text.lower().strip().split()
        if len(text.strip()) <= 1:
            return True

        unknown_count = 0
        total_meaningful = 0

        for word in words:
            clean = word.strip(string.punctuation)
            if len(clean) <= 1:
                continue
            total_meaningful += 1
            is_known = (
                clean in self.vocabulary or
                clean in self.typo_corrections or
                clean in self.hinglish_map or
                clean in self.hindi_indicators or  # 🌐 NEW: Hindi words are NOT gibberish
                len(clean) <= 2
            )
            if not is_known:
                _, was_corrected = self._fuzzy_match_word(clean, max_distance=2)
                is_known = was_corrected
            if not is_known:
                # 🌐 NEW: Check for Devanagari script
                if any('\u0900' <= char <= '\u097F' for char in clean):
                    is_known = True
            if not is_known:
                unknown_count += 1

        if total_meaningful == 0:
            return True
        unknown_ratio = unknown_count / total_meaningful
        if unknown_ratio > 0.7 and total_meaningful >= 2:
            print(f"    🚫 Gibberish detected: {unknown_ratio:.0%} unknown words")
            return True
        if len(text.strip()) > 3:
            unique_chars = len(set(text.strip().replace(' ', '')))
            if unique_chars <= 2:
                print(f"    🚫 Gibberish detected: only {unique_chars} unique characters")
                return True
        return False

    def _load_intents(self, intents_file):
        """Load intents from JSON file"""
        try:
            with open(intents_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.intents = data['intents']
            print(f"✅ Loaded {len(self.intents)} intents from {intents_file}")

            # 🌐 Count Hindi responses
            hindi_count = sum(1 for i in self.intents if i.get('responses_hi'))
            print(f"  🌐 Hindi responses available: {hindi_count}/{len(self.intents)} intents")
        except FileNotFoundError:
            print(f"❌ Error: {intents_file} not found!")
            self.intents = []
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            self.intents = []

    def _preprocess(self, text):
        """Preprocess user input text"""
        if not text:
            return ""
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)

        # 🔧 NEW: Convert Devanagari Hindi to English keywords FIRST
        text = self._convert_devanagari_to_english(text)

        text, num_fixes, _, _ = self._fix_typos(text)
        words = text.split()
        translated_words = []
        for word in words:
            clean_word = word.strip(string.punctuation)
            if clean_word in self.hinglish_map:
                translated_words.append(self.hinglish_map[clean_word])
            else:
                translated_words.append(clean_word)
        text = ' '.join(translated_words)
        text = text.translate(str.maketrans('', '', string.punctuation))
        try:
            tokens = word_tokenize(text)
            tokens = [
                self.lemmatizer.lemmatize(token)
                for token in tokens if len(token) > 1
            ]
            return ' '.join(tokens)
        except Exception:
            return text

    def _train(self):
        """Train TF-IDF model on all intent patterns"""
        if not self.intents:
            print("❌ No intents to train on!")
            return
        self.all_patterns = []
        self.pattern_intent_map = []
        for intent in self.intents:
            tag = intent.get('tag', '')
            patterns = intent.get('patterns', [])
            for pattern in patterns:
                processed = self._preprocess(pattern)
                if processed:
                    self.all_patterns.append(processed)
                    self.pattern_intent_map.append(tag)
        if self.all_patterns:
            self.intent_vectors = self.vectorizer.fit_transform(self.all_patterns)
            print(f"✅ Trained on {len(self.all_patterns)} patterns across {len(self.intents)} intents")
        else:
            print("❌ No valid patterns found for training!")

    def _classify_intent(self, user_message):
        """Classify user message using TF-IDF + Cosine Similarity"""
        processed_msg = self._preprocess(user_message)
        if not processed_msg or self.intent_vectors is None:
            return 'default', 0.0
        try:
            user_vector = self.vectorizer.transform([processed_msg])
            similarities = cosine_similarity(user_vector, self.intent_vectors).flatten()
            best_idx = np.argmax(similarities)
            best_score = similarities[best_idx]
            best_intent = self.pattern_intent_map[best_idx]

            top_indices = np.argsort(similarities)[-3:][::-1]
            top_intents = [self.pattern_intent_map[i] for i in top_indices]
            top_scores = [similarities[i] for i in top_indices]

            if len(top_intents) >= 2 and top_intents[0] == top_intents[1]:
                best_score = min(best_score * 1.2, 1.0)

            print(f"    📊 TF-IDF Top 3 for '{user_message}':")
            for i in range(min(3, len(top_indices))):
                print(f"      {i+1}. {top_intents[i]} ({top_scores[i]:.2%})")

            return best_intent, float(best_score)
        except Exception as e:
            print(f"⚠️ Classification error: {e}")
            return 'default', 0.0

    def _keyword_fallback(self, user_message):
        """Fallback: Match keywords when TF-IDF confidence is low"""
        msg_lower = user_message.lower().strip()
        corrected_msg, _, _, _ = self._fix_typos(msg_lower)

        keyword_map = {
            'spiritual research cell': 'research_publications',
            'research cell': 'research_publications',
            'research center': 'research_publications',
            'lateral entry': 'admission_lateral',
            'diploma to btech': 'admission_lateral',
            'reap counselling': 'reap_counselling',
            'jee main': 'jee_main', 'jee score': 'jee_main',
            'gap year': 'gap_year', 'gap certificate': 'gap_year',
            'last date': 'admission_deadline',
            'ai ml': 'aiml_specialization',
            'artificial intelligence': 'aiml_specialization',
            'machine learning': 'aiml_specialization',
            'data science': 'data_science_specialization',
            'cyber security': 'cyber_security_specialization',
            'computer science': 'cse_department',
            'information technology': 'it_department',
            'civil engineering': 'ce_department',
            'seminar hall': 'auditorium_seminar',
            'campus life': 'campus_life',
            'how to reach': 'campus_navigation',
            'student portal': 'student_login_erp',
            'student login': 'student_login_erp',
            'green campus': 'environment_green',
            'near college': 'nearby_places',
            'id card': 'dress_code', 'dress code': 'dress_code',
            'back paper': 'backlog_kt',
            'semester system': 'semester_system',
            'higher studies': 'higher_studies',
            'after btech': 'higher_studies',
            'branch wise placement': 'placement_statistics_detailed',
            'placement training': 'placement_training',
            'fee refund': 'fee_refund',
            'fee payment': 'fee_payment',
            'how to pay': 'fee_payment',
            'summer training': 'internship',
            'who are you': 'bot_identity',
            'about college': 'about_college',
            'about jecrc': 'about_college',
            'jecrc foundation': 'about_college',
            'is jecrc good': 'admission_comparison',
            'anti ragging': 'ragging',
            'women cell': 'women_cell',
            'mental health': 'counselling_mental_health',
            'anti drug': 'anti_drug',
            'reap': 'reap_counselling',
            'eligib': 'admission_eligibility',
            'cutoff': 'admission_eligibility',
            'document': 'admission_documents',
            'deadline': 'admission_deadline',
            'admission': 'admission_process',
            'apply': 'admission_process',
            'cse': 'cse_department', 'ece': 'ece_department',
            'electrical': 'ee_department',
            'mechanical': 'me_department',
            'mba': 'mba_program', 'mca': 'mca_program',
            'mtech': 'mtech_program',
            'department': 'departments', 'branch': 'departments',
            'course': 'departments',
            'scholarship': 'scholarship',
            'refund': 'fee_refund',
            'installment': 'fee_payment',
            'fee': 'fee_structure', 'fees': 'fee_structure',
            'placement': 'placement', 'package': 'placement',
            'internship': 'internship',
            'hostel rule': 'hostel_rules',
            'mess': 'mess_food', 'canteen': 'mess_food',
            'food': 'mess_food', 'cafeteria': 'mess_food',
            'hostel': 'hostel',
            'backlog': 'backlog_kt', 'supplementary': 'backlog_kt',
            'attendance': 'attendance',
            'result': 'result', 'marks': 'result',
            'cgpa': 'result', 'sgpa': 'result',
            'exam': 'exam_schedule',
            'syllabus': 'syllabus',
            'timetable': 'timetable', 'schedule': 'timetable',
            'faculty': 'hod_faculty', 'hod': 'hod_faculty',
            'professor': 'hod_faculty', 'teacher': 'hod_faculty',
            'gate': 'higher_studies',
            'certification': 'certifications_courses',
            'nptel': 'certifications_courses',
            'transfer': 'transfer_migration',
            'convocation': 'convocation', 'degree': 'convocation',
            'library': 'library', 'book': 'library',
            'lab': 'lab_facilities',
            'sport': 'sports', 'gym': 'sports',
            'wifi': 'wifi', 'internet': 'wifi',
            'bus': 'transport', 'transport': 'transport',
            'parking': 'parking',
            'medical': 'medical', 'doctor': 'medical',
            'auditorium': 'auditorium_seminar',
            'campus': 'campus_navigation',
            'location': 'campus_navigation',
            'erp': 'student_login_erp',
            'ragging': 'ragging',
            'icc': 'women_cell',
            'stress': 'counselling_mental_health',
            'counselling': 'counselling_mental_health',
            'drug': 'anti_drug', 'smoking': 'anti_drug',
            'complaint': 'complaint', 'grievance': 'complaint',
            'discipline': 'discipline_rules', 'rules': 'discipline_rules',
            'disability': 'disability_support',
            'chairman': 'chairman_management',
            'director': 'director_principal',
            'principal': 'director_principal',
            'vision': 'vision_mission', 'mission': 'vision_mission',
            'accreditation': 'accreditation', 'naac': 'accreditation',
            'nba': 'accreditation', 'aicte': 'accreditation',
            'alumni': 'alumni',
            'event': 'events', 'fest': 'events',
            'club': 'clubs', 'society': 'clubs',
            'nss': 'ncc_nss', 'ncc': 'ncc_nss',
            'entrepreneur': 'entrepreneurship_ecell',
            'startup': 'entrepreneurship_ecell',
            'research': 'research_publications',
            'uniform': 'dress_code',
            'parent': 'parent_guardian', 'ptm': 'parent_guardian',
            'contact': 'contact', 'phone': 'contact',
            'email': 'contact',
            'namaste': 'greeting', 'hello': 'greeting',
            'hey': 'greeting', 'hi': 'greeting',
            'bye': 'goodbye', 'goodbye': 'goodbye',
            'thank': 'thanks',
            'help': 'help',
        }
        
        # EXISTING: check msg_lower and corrected_msg
        # 🔧 UPDATED: Also check devanagari-converted text
        converted_msg = self._convert_devanagari_to_english(msg_lower)

        for text_to_check in [msg_lower, corrected_msg, converted_msg]:
            for keyword, intent_tag in keyword_map.items():
                if keyword in text_to_check:
                    print(f"    🔑 Keyword matched: '{keyword}' → {intent_tag}")
                    return intent_tag, keyword

        return None, None


    def _exact_match(self, user_message):
        """Check if user message exactly matches any pattern"""
        msg_lower = user_message.lower().strip()
        corrected_msg, _, _, _ = self._fix_typos(msg_lower)

        for check_msg in [msg_lower, corrected_msg]:
            for intent in self.intents:
                tag = intent.get('tag', '')
                patterns = intent.get('patterns', [])
                for pattern in patterns:
                    pattern_lower = pattern.lower().strip()
                    if check_msg == pattern_lower:
                        print(f"    ✨ Exact match: '{pattern}' → {tag}")
                        return tag, 1.0
                    if check_msg in pattern_lower or pattern_lower in check_msg:
                        if len(check_msg) > 3 and len(pattern_lower) > 3:
                            overlap = min(len(check_msg), len(pattern_lower)) / max(len(check_msg), len(pattern_lower))
                            if overlap > 0.6:
                                print(f"    ✨ Close match: '{pattern}' → {tag} ({overlap:.0%})")
                                return tag, 0.85
        return None, 0

    # ═══════════════════════════════════════
    # 🌐 UPDATED: Generate Retype Message (Multi-Language)
    # ═══════════════════════════════════════
    def _generate_retype_message(self, original_msg, corrected_msg, num_corrections, language='en'):
        """Generate a helpful retype message in the correct language"""

        if language == 'hi':
            retype_messages_hi = [
                (
                    "माफ़ कीजिए, मैं आपका सवाल समझ नहीं पाया। 🤔\n\n"
                    "कृपया अपना सवाल **दोबारा टाइप** करें!\n\n"
                    "आप इनके बारे में पूछ सकते हैं:\n"
                    "🔹 एडमिशन प्रक्रिया\n"
                    "🔹 फीस स्ट्रक्चर\n"
                    "🔹 प्लेसमेंट डिटेल्स\n"
                    "🔹 हॉस्टल सुविधाएं\n"
                    "🔹 परीक्षा और सिलेबस\n\n"
                    "💡 उदाहरण: \"admission kaise hota hai?\", \"fees kitni hai?\""
                ),
                (
                    "मैं आपकी बात समझ नहीं पाया। 😅\n\n"
                    "कृपया **सरल शब्दों** में दोबारा पूछें!\n\n"
                    "📌 जैसे:\n"
                    "• \"एडमिशन कैसे होता है?\"\n"
                    "• \"फीस कितनी है?\"\n"
                    "• \"हॉस्टल के बारे में बताओ\"\n"
                    "• \"प्लेसमेंट कैसी है?\"\n\n"
                    "या **\"help\"** टाइप करें सभी विषय देखने के लिए! 📋"
                ),
            ]

            if num_corrections > 0:
                return (
                    f"मैंने आपका सवाल समझने की कोशिश की लेकिन पूरी तरह समझ नहीं पाया। 🤔\n\n"
                    f"कृपया **दोबारा ध्यान से टाइप** करें!\n\n"
                    f"💡 **सुझाव:**\n"
                    f"🔹 सरल हिंदी या English में लिखें\n"
                    f"🔹 जैसे: \"admission kaise hota hai?\"\n"
                    f"🔹 जैसे: \"fees kitni hai?\"\n\n"
                    f"या साइडबार से कोई टॉपिक चुनें! 👈"
                )

            return random.choice(retype_messages_hi)

        # English retype messages (same as before)
        retype_messages = [
            (
                "I'm not sure I understood that correctly. 🤔\n\n"
                "Could you please **retype your question** a bit more clearly?\n\n"
                "Here are some things I can help with:\n"
                "🔹 Admissions & Eligibility\n"
                "🔹 Fee Structure & Scholarships\n"
                "🔹 Placements & Training\n"
                "🔹 Hostel & Campus Life\n"
                "🔹 Exams, Results & Syllabus\n\n"
                "💡 **Tip:** Try typing in simple words like:\n"
                "\"admission process\", \"hostel fees\", \"placement details\""
            ),
            (
                "Hmm, I couldn't quite catch that. 😅\n\n"
                "Could you **please type your question again** in a simpler way?\n\n"
                "📌 For example:\n"
                "• \"How to get admission?\"\n"
                "• \"What is the fee structure?\"\n"
                "• \"Tell me about hostel\"\n"
                "• \"Placement details batao\"\n\n"
                "You can also use the **Quick Topics** on the left sidebar! 👈"
            ),
            (
                "I didn't quite understand your question. 🙁\n\n"
                "Please **try rephrasing** or check for any typos!\n\n"
                "🎯 I'm best at answering about:\n"
                "📋 Admissions | 💰 Fees | 💼 Placements\n"
                "🏠 Hostel | 📚 Academics | 🏛️ Campus Life\n\n"
                "Or type **\"help\"** to see all available topics!"
            ),
        ]

        if num_corrections > 0:
            return (
                f"I tried to understand your question but I'm still not sure what you're looking for. 🤔\n\n"
                f"Could you please **type your question again more carefully**?\n\n"
                f"💡 **Tips:**\n"
                f"🔹 Use simple English or Hinglish\n"
                f"🔹 Example: \"admission kaise hota hai?\"\n"
                f"🔹 Example: \"fees kitni hai?\"\n"
                f"🔹 Example: \"placement details\"\n\n"
                f"Or click a topic from the sidebar for quick answers! 👈"
            )

        return random.choice(retype_messages)

    def _update_context(self, user_id, intent_tag):
        """Update context for a user"""
        for intent in self.intents:
            if intent['tag'] == intent_tag:
                self.context[user_id] = intent.get('context', 'general')
                break

    # ═══════════════════════════════════════
    # 🌐 UPDATED: Main get_response (Multi-Language)
    # ═══════════════════════════════════════
    def get_response(self, user_message, user_id='default', language=None):
        """
        Main method: Get chatbot response for a user message
        🌐 NEW: language parameter ('en', 'hi', or 'auto')
        """
        # Validate input
        if not user_message or not user_message.strip():
            return {
                'reply': "Please type a message so I can help you! 😊",
                'intent': 'empty',
                'confidence': 0.0,
                'method': 'validation',
                'language': 'en'
            }

        user_message = user_message.strip()

        print(f"\n{'='*50}")
        print(f"📝 User: '{user_message}'")
        print(f"{'='*50}")

        # ═══════════════════════════════════════
        # 🌐 NEW: Determine Language
        # ═══════════════════════════════════════
        if language and language in self.supported_languages:
            # User explicitly chose a language
            current_lang = language
            self.set_user_language(user_id, language)
        elif language == 'auto' or language is None:
            # Auto-detect from message
            detected_lang = self.detect_language(user_message)
            # If user has a saved preference, use it (unless auto-detect is very confident)
            saved_lang = self.get_user_language(user_id)
            current_lang = detected_lang
            self.set_user_language(user_id, detected_lang)
        else:
            current_lang = self.get_user_language(user_id)

        print(f"  🌐 Language: {current_lang}")

        # Store in conversation history
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append(user_message)
        if len(self.conversation_history[user_id]) > 10:
            self.conversation_history[user_id] = self.conversation_history[user_id][-10:]

        # Fix Typos
        corrected_text, num_corrections, original_words, fixed_words = self._fix_typos(user_message)
        if num_corrections > 0:
            print(f"  🔤 Typos fixed ({num_corrections}): {list(zip(original_words, fixed_words))}")

        # Gibberish Detection
        if self._is_gibberish(user_message):
            print(f"  🚫 Gibberish detected!")
            if current_lang == 'hi':
                reply = (
                    "मैं आपकी बात समझ नहीं पाया। 😅\n\n"
                    "कृपया अपना सवाल **दोबारा साफ़ शब्दों** में लिखें!\n\n"
                    "उदाहरण:\n"
                    "🔹 \"एडमिशन कैसे होता है?\"\n"
                    "🔹 \"फीस कितनी है?\"\n"
                    "🔹 \"हॉस्टल की सुविधाएं बताओ\"\n\n"
                    "या साइडबार से कोई टॉपिक चुनें! 👈"
                )
            else:
                reply = (
                    "I couldn't understand that. 😅\n\n"
                    "Could you please **retype your question** more clearly? "
                    "For example, you can ask:\n"
                    "🔹 \"What is the admission process?\"\n"
                    "🔹 \"Fee structure batao\"\n"
                    "🔹 \"Hostel facilities kya hai?\"\n"
                    "🔹 \"Placement details\"\n\n"
                    "Or click on a topic from the sidebar! 👈"
                )
            return {
                'reply': reply,
                'intent': 'gibberish',
                'confidence': 0.0,
                'method': 'gibberish_detection',
                'language': current_lang
            }

        # STEP 1: Exact Match
        exact_intent, exact_conf = self._exact_match(user_message)
        if exact_intent and exact_conf >= 0.85:
            response = self._get_response_for_intent(exact_intent, current_lang)
            self._update_context(user_id, exact_intent)
            print(f"  ✅ Result: {exact_intent} (exact, {exact_conf:.0%})")
            return {
                'reply': response,
                'intent': exact_intent,
                'confidence': round(exact_conf, 4),
                'method': 'exact',
                'language': current_lang
            }

        # STEP 2: TF-IDF + Keyword
        tfidf_intent, tfidf_conf = self._classify_intent(
            corrected_text if num_corrections > 0 else user_message
        )
        keyword_intent, keyword_matched = self._keyword_fallback(
            corrected_text if num_corrections > 0 else user_message
        )

        if num_corrections > 0 and tfidf_conf < self.confidence_threshold:
            tfidf_intent_orig, tfidf_conf_orig = self._classify_intent(user_message)
            if tfidf_conf_orig > tfidf_conf:
                tfidf_intent = tfidf_intent_orig
                tfidf_conf = tfidf_conf_orig

        print(f"  📊 TF-IDF: {tfidf_intent} ({tfidf_conf:.2%})")
        print(f"  🔑 Keyword: {keyword_intent} (matched: '{keyword_matched}')")

        # STEP 3: Smart Decision
        final_intent = 'default'
        final_conf = 0.0
        method = 'default'

        if keyword_intent and tfidf_intent == keyword_intent:
            final_intent = tfidf_intent
            final_conf = min(tfidf_conf + 0.15, 1.0)
            method = 'hybrid'
        elif tfidf_conf >= self.high_confidence_threshold:
            final_intent = tfidf_intent
            final_conf = tfidf_conf
            method = 'tfidf'
        elif keyword_intent and tfidf_conf < self.high_confidence_threshold:
            final_intent = keyword_intent
            final_conf = 0.70
            method = 'keyword'
        elif tfidf_conf >= self.confidence_threshold and not keyword_intent:
            final_intent = tfidf_intent
            final_conf = tfidf_conf
            method = 'tfidf'
        else:
            final_intent = 'unclear'
            final_conf = max(tfidf_conf, 0.0)
            method = 'unclear'

        # Retype if no good match
        if final_intent in ['default', 'unclear'] or (method == 'default' and final_conf < self.confidence_threshold):
            response = self._generate_retype_message(user_message, corrected_text, num_corrections, current_lang)
            print(f"  ✅ Final: retype_suggestion | {final_conf:.2%} | {method}")
            return {
                'reply': response,
                'intent': 'unclear_retype',
                'confidence': round(final_conf, 4),
                'method': 'retype_suggestion',
                'language': current_lang
            }

        # Get response in correct language
        response = self._get_response_for_intent(final_intent, current_lang)
        self._update_context(user_id, final_intent)
        print(f"  ✅ Final: {final_intent} | {final_conf:.2%} | {method} | lang={current_lang}")

        return {
            'reply': response,
            'intent': final_intent,
            'confidence': round(final_conf, 4),
            'method': method,
            'language': current_lang
        }

    def get_all_intents(self):
        return [intent['tag'] for intent in self.intents if intent['tag'] != 'default']

    def get_intent_count(self):
        return len(self.intents)

    def get_pattern_count(self):
        return len(self.all_patterns)

    def get_stats(self):
        hindi_count = sum(1 for i in self.intents if i.get('responses_hi'))
        return {
            'total_intents': self.get_intent_count(),
            'total_patterns': self.get_pattern_count(),
            'confidence_threshold': self.confidence_threshold,
            'high_confidence_threshold': self.high_confidence_threshold,
            'typo_corrections_loaded': len(self.typo_corrections),
            'vocabulary_size': len(self.vocabulary),
            'active_sessions': len(self.conversation_history),
            'supported_languages': self.supported_languages,
            'hindi_responses_available': hindi_count,
            'intents_list': self.get_all_intents()
        }


# ── Testing ──
if __name__ == "__main__":
    print("=" * 60)
    print("  JECRC Foundation Helpdesk AI - Engine Test")
    print("  🌐 WITH MULTI-LANGUAGE SUPPORT")
    print("=" * 60)

    engine = ChatbotEngine()
    stats = engine.get_stats()
    print(f"\n📊 Stats:")
    print(f"  Intents: {stats['total_intents']}")
    print(f"  Patterns: {stats['total_patterns']}")
    print(f"  Languages: {stats['supported_languages']}")
    print(f"  Hindi Responses: {stats['hindi_responses_available']}")

    test_queries = [
        ("Hello!", None),
        ("admission kaise hota hai?", None),
        ("fees kitni hai?", None),
        ("What is the fee structure?", 'en'),
        ("hostel ke baare mein batao", 'auto'),
        ("placement details", 'en'),
        ("प्लेसमेंट कैसी है?", None),
    ]

    print(f"\n🧪 Testing {len(test_queries)} queries:\n")
    for query, lang in test_queries:
        result = engine.get_response(query, user_id='test', language=lang)
        print(f"  Q: {query}")
        print(f"  🌐 Lang: {result['language']} | Intent: {result['intent']} | Conf: {result['confidence']:.2%}")
        print(f"  A: {result['reply'][:100]}...")
        print("-" * 60)
