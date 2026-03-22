"""
============================================================
  JECRC Foundation - College Helpdesk AI Chatbot
  Configuration File
  Project: J-TECHTRIX 7.0
  
  🔧 UPDATED: Admin authentication + security settings
  🔧 FIXED: Static SECRET_KEY (no session loss on restart)
============================================================
"""

import os


class Config:
    """Application Configuration"""

    # ── Flask Settings ──
    SECRET_KEY = os.environ.get(
        'SECRET_KEY',
        'jecrc-j-techtrix-7-chatbot-secret-key-2025-fixed'
    )
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    HOST = '0.0.0.0'
    PORT = int(os.environ.get('PORT', 5000))

    # ── Database ──
    DATABASE_PATH = 'chat_history.db'

    # ── JECRC Foundation Information ──
    COLLEGE_NAME = "JECRC Foundation"
    COLLEGE_FULL_NAME = (
        "Jaipur Engineering College and Research Centre "
        "(JECRC Foundation)"
    )
    COLLEGE_WEBSITE = "https://jecrcfoundation.com/"
    COLLEGE_EMAIL = "info@jecrcfoundation.com"
    COLLEGE_PHONE = "+91-141-2770232"
    COLLEGE_ADDRESS = (
        "JECRC Campus, Ramchandrapura, Vidhani, "
        "Sitapura Industrial Area Extension, "
        "Jaipur, Rajasthan 303905"
    )
    AFFILIATED_TO = "Rajasthan Technical University (RTU), Kota"
    APPROVED_BY = "AICTE, New Delhi"
    ESTABLISHED = "2000"

    # ── Chatbot Settings ──
    BOT_NAME = "JECRC Foundation Helpdesk AI"
    CONFIDENCE_THRESHOLD = 0.35
    MAX_CHAT_HISTORY = 100

    # ── Web Scraping ──
    SCRAPE_ENABLED = True
    SCRAPE_INTERVAL_HOURS = 24
    SCRAPE_URLS = [
        "https://jecrcfoundation.com/",
        "https://jecrcfoundation.com/admission",
        "https://jecrcfoundation.com/placement",
        "https://jecrcfoundation.com/department",
        "https://jecrcfoundation.com/campus-life",
        "https://jecrcfoundation.com/about-us",
        "https://jecrcfoundation.com/contact-us",
    ]

    # ── 🔧 Admin Authentication ──
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'jecrc@admin2025')
    
    # 🔧 Rate limiting
    RATE_LIMIT_PER_MINUTE = 30
    MAX_MESSAGE_LENGTH = 500
