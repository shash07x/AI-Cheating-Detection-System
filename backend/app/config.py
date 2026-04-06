"""
Application Configuration
"""

import os
from datetime import timedelta


class Config:
    """Base configuration class"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = False
    TESTING = False
    
    # Database (if you're using one)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///proctoring.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Socket.IO
    CORS_ALLOWED_ORIGINS = "*"  # Change in production
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    # Upload (if needed)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Proctoring Settings
    BLACK_FRAME_THRESHOLD = 10
    COVERED_FRAME_VARIANCE = 15
    
    # Audio Settings
    SAMPLE_RATE = 16000
    AUDIO_CHUNK_DURATION = 2.0  # seconds


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # Add production-specific settings here


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True


# ==================== AUTHENTICITY DETECTION CONFIG ====================

class AuthenticityConfig:
    """Speech Authenticity Detection Configuration"""
    
    # Feature flags
    ENABLED = True
    REAL_TIME_MODE = True
    LINGUISTIC_ANALYSIS = True
    AUDIO_FEATURE_ANALYSIS = True
    
    # Models
    WHISPER_MODEL = "base"
    WHISPER_DEVICE = "cpu"
    WHISPER_LANGUAGE = "en"
    
    # Processing
    TRANSCRIPTION_INTERVAL = 5.0
    MIN_AUDIO_LENGTH = 3.0
    AUDIO_BUFFER_SIZE = 10
    
    # Thresholds
    AUTHENTIC_THRESHOLD = 60
    AI_GENERATED_THRESHOLD = 70
    
    # Linguistic features
    FILLER_WORD_MIN = 0.005
    FORMAL_STRUCTURE_MAX = 0.7
    
    # Audio features
    MONOTONE_THRESHOLD = 0.6
    PAUSE_PATTERN_THRESHOLD = 0.7
    
    # AI signature phrases
    AI_SIGNATURE_PHRASES = [
        "first and foremost",
        "it's important to note",
        "it's worth mentioning",
        "in conclusion",
        "to summarize",
        "as previously mentioned",
        "furthermore",
        "moreover",
        "subsequently",
        "in other words",
        "that being said",
        "with that in mind",
        "it goes without saying"
    ]
    
    FILLER_WORDS = [
        "um", "uh", "like", "you know", "so", "well",
        "actually", "basically", "literally", "right",
        "okay", "alright", "hmm", "ah", "er"
    ]
    
    # Performance
    MAX_CONCURRENT_TRANSCRIPTIONS = 3
    CACHE_TRANSCRIPTS = True
    FAIL_SAFE_MODE = True
    
    # Logging
    LOG_LEVEL = "INFO"
    LOG_TRANSCRIPTS = True
    LOG_SCORES = True
    
    # Storage
    STORE_TRANSCRIPTS = False
    TRANSCRIPT_DIR = "data/transcripts"
    RETENTION_HOURS = 24


# Singleton instances
config = Config()
authenticity_config = AuthenticityConfig()


# Configuration selector based on environment
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name='default'):
    """Get configuration by name"""
    return config_by_name.get(config_name, DevelopmentConfig)