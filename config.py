import os
import secrets


def env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


class BaseConfig:
    APP_NAME = 'Kansi AI'
    ENV_NAME = os.getenv('KANSI_ENV', 'development').lower()
    SECRET_KEY = os.getenv('KANSI_SECRET_KEY')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = env_flag('KANSI_SESSION_COOKIE_SECURE', False)
    PERMANENT_SESSION_LIFETIME_DAYS = int(os.getenv('KANSI_SESSION_LIFETIME_DAYS', '7'))
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token']
    MAX_CONTENT_LENGTH = int(os.getenv('KANSI_MAX_CONTENT_LENGTH', str(64 * 1024)))
    DEBUG = env_flag('KANSI_DEBUG', False)
    TESTING = False
    PROPAGATE_EXCEPTIONS = False
    TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv('KANSI_TRUSTED_ORIGINS', '').split(',') if origin.strip()]
    SITE_URL = os.getenv('KANSI_SITE_URL', '').rstrip('/')
    SHOW_RESET_LINKS = env_flag('KANSI_SHOW_RESET_LINKS', False)
    SECURITY_WEBHOOK_SECRET = os.getenv('KANSI_WEBHOOK_SECRET', '')
    SECURITY_LOG_LEVEL = os.getenv('KANSI_LOG_LEVEL', 'INFO').upper()
    PASSWORD_RESET_TTL_MINUTES = int(os.getenv('KANSI_PASSWORD_RESET_TTL_MINUTES', '30'))
    SECURITY_ALLOWED_FETCH_HOSTS = [
        host.strip().lower()
        for host in os.getenv('KANSI_ALLOWED_FETCH_HOSTS', 'findahelpline.com').split(',')
        if host.strip()
    ]
    ENABLE_DEMO_GOOGLE_AUTH = env_flag(
        'KANSI_ENABLE_DEMO_GOOGLE_AUTH',
        ENV_NAME != 'production'
    )


class TestConfig(BaseConfig):
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = True
    SECRET_KEY = os.getenv('KANSI_SECRET_KEY', 'test-secret-key')
    SHOW_RESET_LINKS = True
    SESSION_COOKIE_SECURE = False
    ENABLE_DEMO_GOOGLE_AUTH = True
