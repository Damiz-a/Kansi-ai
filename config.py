import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", Fernet.generate_key().decode())
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_DEFAULT_PASSWORD = os.getenv("ADMIN_DEFAULT_PASSWORD", Fernet.generate_key().decode()[:16])
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
ALERT_TIMEOUT_SECONDS = int(os.getenv("ALERT_TIMEOUT_SECONDS", "60"))
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_LOCKOUT_MINUTES = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "25"))
MAX_PAYLOAD_SIZE_BYTES = int(os.getenv("MAX_PAYLOAD_SIZE_BYTES", "10240"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/kansi_ai.db")

fernet = Fernet(ENCRYPTION_KEY if len(ENCRYPTION_KEY) == 44 else Fernet.generate_key())

CRISIS_HOTLINES = {
    "GB": {"name": "Samaritans", "number": "116 123", "emergency": "999"},
    "US": {"name": "988 Suicide & Crisis Lifeline", "number": "988", "emergency": "911"},
    "CA": {"name": "Crisis Services Canada", "number": "1-833-456-4566", "emergency": "911"},
    "AU": {"name": "Lifeline Australia", "number": "13 11 14", "emergency": "000"},
    "IN": {"name": "iCall", "number": "9152987821", "emergency": "112"},
    "NG": {"name": "SURPIN", "number": "0800-123-0800", "emergency": "112"},
    "ZA": {"name": "SADAG", "number": "0800 567 567", "emergency": "10111"},
    "DEFAULT": {"name": "Crisis Text Line", "number": "Text HOME to 741741", "emergency": "112"},
}

TRIGGER_PHRASES = [
    "i want to kill myself", "i want to die", "i am going to end it",
    "i want to end my life", "i am tired of life", "i want to commit suicide",
    "i don't want to live anymore", "i wish i was dead", "life is not worth living",
    "i am going to kill myself", "nobody would miss me", "the world is better without me",
    "i have nothing to live for", "i want it all to end", "i can't go on anymore",
    "i am planning to end it", "i just want the pain to stop", "i want to disappear forever",
    "goodbye cruel world", "this is my last day",
]
