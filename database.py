"""
Kansi AI - Database Module
===========================
SQLite database for user management, sessions, analysis history,
password reset workflows, and security event tracking.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError

DEFAULT_DB_PATH = (
    os.path.join('/tmp', 'kansi_ai.db')
    if os.getenv('VERCEL') == '1'
    else os.path.join(os.path.dirname(__file__), 'data', 'kansi_ai.db')
)

DB_PATH = os.getenv('KANSI_DB_PATH', DEFAULT_DB_PATH)

password_hasher = PasswordHasher()


def utcnow():
    return datetime.now(timezone.utc)


def utcnow_iso():
    return utcnow().isoformat()


def get_db():
    """Get database connection."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_column(conn, table_name, column_name, definition):
    """Add a column if it does not exist."""
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing = {row['name'] for row in rows}
    if column_name not in existing:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db():
    """Initialize the database schema."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            full_name TEXT NOT NULL,
            auth_provider TEXT DEFAULT 'email',
            google_id TEXT UNIQUE,
            profile_picture TEXT,
            bio TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            is_admin BOOLEAN DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            is_valid BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            input_text TEXT NOT NULL,
            prediction TEXT NOT NULL,
            confidence REAL,
            model_used TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            theme TEXT DEFAULT 'light',
            notifications_enabled BOOLEAN DEFAULT 1,
            language TEXT DEFAULT 'en',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS security_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            subject TEXT,
            ip_address TEXT,
            metadata TEXT,
            created_at TIMESTAMP NOT NULL
        )
    ''')

    ensure_column(conn, 'users', 'is_admin', 'BOOLEAN DEFAULT 0')
    ensure_column(conn, 'users', 'is_active', 'BOOLEAN DEFAULT 1')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_history_user_created ON analysis_history(user_id, created_at DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_security_events_lookup ON security_events(event_type, subject, ip_address, created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_password_reset_lookup ON password_reset_tokens(token_hash, expires_at, used_at)')

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


def hash_password(password):
    """Hash password using Argon2id."""
    return password_hasher.hash(password)


def verify_password(stored_hash, password):
    """Verify a password against a stored hash."""
    if not stored_hash:
        return False

    if stored_hash.startswith('$argon2'):
        try:
            return password_hasher.verify(stored_hash, password)
        except (InvalidHash, VerifyMismatchError):
            return False

    # Legacy fallback for old SHA-256 salted hashes. They will be upgraded on login.
    if ':' in stored_hash:
        salt, pwd_hash = stored_hash.split(':', 1)
        import hashlib
        return hashlib.sha256((salt + password).encode()).hexdigest() == pwd_hash

    return False


def needs_password_rehash(stored_hash):
    if not stored_hash or not stored_hash.startswith('$argon2'):
        return True
    try:
        return password_hasher.check_needs_rehash(stored_hash)
    except InvalidHash:
        return True


def create_user(email, password, full_name, auth_provider='email', google_id=None, profile_picture=None, is_admin=False):
    """Create a new user account."""
    conn = get_db()
    try:
        password_hash = hash_password(password) if password else None
        conn.execute(
            '''
            INSERT INTO users (email, password_hash, full_name, auth_provider, google_id, profile_picture, is_admin)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (email, password_hash, full_name, auth_provider, google_id, profile_picture, int(bool(is_admin)))
        )
        conn.commit()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.execute('INSERT INTO user_preferences (user_id) VALUES (?)', (user['id'],))
        conn.commit()
        return dict(user)
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def update_user_password(user_id, password):
    conn = get_db()
    conn.execute(
        'UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?',
        (hash_password(password), utcnow_iso(), user_id)
    )
    conn.commit()
    conn.close()


def update_last_login(user_id):
    conn = get_db()
    conn.execute(
        'UPDATE users SET last_login = ?, updated_at = ? WHERE id = ?',
        (utcnow_iso(), utcnow_iso(), user_id)
    )
    conn.commit()
    conn.close()


def authenticate_user(email, password):
    """Authenticate user with email and password."""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    if not user or not user['password_hash']:
        conn.close()
        return None

    if not verify_password(user['password_hash'], password):
        conn.close()
        return None

    if needs_password_rehash(user['password_hash']):
        conn.execute(
            'UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?',
            (hash_password(password), utcnow_iso(), user['id'])
        )
        conn.commit()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()

    conn.close()
    update_last_login(user['id'])
    return dict(user)


def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_email(email):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return dict(user) if user else None


def set_user_admin(user_id, is_admin=True):
    conn = get_db()
    conn.execute(
        'UPDATE users SET is_admin = ?, updated_at = ? WHERE id = ?',
        (int(bool(is_admin)), utcnow_iso(), user_id)
    )
    conn.commit()
    conn.close()


def update_user_profile(user_id, full_name=None, bio=None, profile_picture=None):
    """Update user profile information."""
    conn = get_db()
    current = conn.execute(
        'SELECT full_name, bio, profile_picture FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()
    if not current:
        conn.close()
        return

    next_full_name = full_name if full_name else current['full_name']
    next_bio = bio if bio is not None else current['bio']
    next_picture = profile_picture if profile_picture else current['profile_picture']

    conn.execute(
        '''
        UPDATE users
        SET full_name = ?, bio = ?, profile_picture = ?, updated_at = ?
        WHERE id = ?
        ''',
        (next_full_name, next_bio, next_picture, utcnow_iso(), user_id)
    )
    conn.commit()
    conn.close()


def save_analysis(user_id, input_text, prediction, confidence, model_used):
    """Save analysis result to history."""
    conn = get_db()
    conn.execute(
        '''
        INSERT INTO analysis_history (user_id, input_text, prediction, confidence, model_used)
        VALUES (?, ?, ?, ?, ?)
        ''',
        (user_id, input_text, prediction, confidence, model_used)
    )
    conn.commit()
    conn.close()


def get_analysis_history(user_id, limit=20):
    conn = get_db()
    rows = conn.execute(
        '''
        SELECT * FROM analysis_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        ''',
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_password_reset_token(user_id, token_hash, expires_at):
    conn = get_db()
    conn.execute(
        '''
        INSERT INTO password_reset_tokens (user_id, token_hash, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        ''',
        (user_id, token_hash, utcnow_iso(), expires_at)
    )
    conn.commit()
    conn.close()


def get_password_reset_record(token_hash):
    conn = get_db()
    row = conn.execute(
        '''
        SELECT prt.*, users.email, users.full_name
        FROM password_reset_tokens prt
        JOIN users ON users.id = prt.user_id
        WHERE prt.token_hash = ?
        ''',
        (token_hash,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def mark_password_reset_used(token_hash):
    conn = get_db()
    conn.execute(
        'UPDATE password_reset_tokens SET used_at = ? WHERE token_hash = ?',
        (utcnow_iso(), token_hash)
    )
    conn.commit()
    conn.close()


def record_security_event(event_type, subject=None, ip_address=None, metadata=None):
    conn = get_db()
    conn.execute(
        '''
        INSERT INTO security_events (event_type, subject, ip_address, metadata, created_at)
        VALUES (?, ?, ?, ?, ?)
        ''',
        (
            event_type,
            subject,
            ip_address,
            json.dumps(metadata or {}, sort_keys=True),
            utcnow_iso()
        )
    )
    conn.commit()
    conn.close()


def count_security_events(event_type, since_iso, subject=None, ip_address=None):
    conn = get_db()
    query = 'SELECT COUNT(*) AS count FROM security_events WHERE event_type = ? AND created_at >= ?'
    params = [event_type, since_iso]
    if subject is not None:
        query += ' AND subject = ?'
        params.append(subject)
    if ip_address is not None:
        query += ' AND ip_address = ?'
        params.append(ip_address)
    row = conn.execute(query, params).fetchone()
    conn.close()
    return int(row['count'])


def get_recent_security_events(limit=20):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM security_events ORDER BY created_at DESC LIMIT ?',
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


if __name__ == '__main__':
    init_db()
    print("Database setup complete.")
