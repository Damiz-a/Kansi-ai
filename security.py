import hashlib
import hmac
import ipaddress
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse


EMAIL_RE = re.compile(r'^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,63}$', re.IGNORECASE)
NAME_RE = re.compile(r"^[A-Za-z ,.'\-]{2,80}$")
TOKEN_BYTES = 32


class ValidationError(ValueError):
    pass


class SecretRedactionFilter(logging.Filter):
    EMAIL_PATTERN = re.compile(r'([A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]*@([A-Za-z0-9.\-]+\.[A-Za-z]{2,63})')
    TOKEN_PATTERN = re.compile(r'([A-Za-z0-9_\-]{24,})')

    def filter(self, record):
        message = record.getMessage()
        message = self.EMAIL_PATTERN.sub(r'\1***@\2', message)
        message = self.TOKEN_PATTERN.sub('[REDACTED_TOKEN]', message)
        record.msg = message
        record.args = ()
        return True


def utcnow():
    return datetime.now(timezone.utc)


def normalize_email(email):
    return email.strip().lower()


def validate_email(email):
    email = normalize_email(email)
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise ValidationError('Enter a valid email address.')
    return email


def validate_full_name(name):
    name = ' '.join(name.strip().split())
    if not NAME_RE.match(name):
        raise ValidationError('Use 2 to 80 letters for your name.')
    return name


def validate_password(password):
    if len(password) < 12:
        raise ValidationError('Password must be at least 12 characters long.')
    if password.lower() == password or password.upper() == password or not any(char.isdigit() for char in password):
        raise ValidationError('Password must include upper case, lower case, and a number.')
    return password


def validate_bio(bio):
    bio = bio.strip()
    if len(bio) > 500:
        raise ValidationError('Bio must be 500 characters or fewer.')
    return bio


def validate_analysis_text(text):
    text = text.strip()
    if len(text) < 10:
        raise ValidationError('Please share at least 10 characters.')
    if len(text) > 2000:
        raise ValidationError('Please keep messages under 2000 characters.')
    return text


def generate_reset_token():
    token = secrets.token_urlsafe(TOKEN_BYTES)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def expiry_iso(minutes):
    return (utcnow() + timedelta(minutes=minutes)).isoformat()


def is_expired(timestamp):
    return datetime.fromisoformat(timestamp) < utcnow()


def verify_webhook_signature(secret, payload, signature_header):
    if not secret or not signature_header or not signature_header.startswith('sha256='):
        return False
    provided = signature_header.split('=', 1)[1]
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided)


def ensure_safe_fetch_url(url, allowed_hosts):
    parsed = urlparse(url)
    if parsed.scheme not in {'https'}:
        raise ValidationError('Only HTTPS URLs are allowed.')
    if not parsed.hostname:
        raise ValidationError('A hostname is required.')

    hostname = parsed.hostname.lower()
    if allowed_hosts and hostname not in {host.lower() for host in allowed_hosts}:
        raise ValidationError('Hostname is not allowlisted.')

    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            raise ValidationError('Private network addresses are not allowed.')
    except ValueError:
        if hostname in {'localhost'}:
            raise ValidationError('Localhost is not allowed.')

    return url
