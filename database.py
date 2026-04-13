import sqlite3
import hashlib
import secrets
import time
from datetime import datetime
from config import DATABASE_PATH, fernet, ADMIN_EMAIL, ADMIN_DEFAULT_PASSWORD
import os
import bleach


def get_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_encrypted TEXT UNIQUE NOT NULL,
        email_hash TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        full_name TEXT NOT NULL,
        auth_provider TEXT DEFAULT 'email',
        google_id TEXT UNIQUE,
        phone_encrypted TEXT,
        country_code TEXT DEFAULT 'GB',
        bio TEXT,
        role TEXT DEFAULT 'user',
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        input_text_encrypted TEXT NOT NULL,
        prediction TEXT NOT NULL,
        confidence REAL,
        model_used TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content_encrypted TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS crisis_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        trigger_phrase TEXT NOT NULL,
        user_message_encrypted TEXT NOT NULL,
        user_country TEXT,
        user_phone_encrypted TEXT,
        status TEXT DEFAULT 'pending',
        admin_action TEXT,
        auto_escalate_at TIMESTAMP NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS login_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_hash TEXT NOT NULL,
        ip_address TEXT,
        success BOOLEAN DEFAULT 0,
        attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()

    admin = get_user_by_email(ADMIN_EMAIL)
    if not admin:
        create_user(ADMIN_EMAIL, ADMIN_DEFAULT_PASSWORD, "Admin - Kansi AI", role="admin")

    conn.close()


def encrypt(text):
    if not text:
        return None
    return fernet.encrypt(text.encode()).decode()


def decrypt(token):
    if not token:
        return None
    try:
        return fernet.decrypt(token.encode()).decode()
    except Exception:
        return "[decryption error]"


def email_hash(email):
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


def hash_password(password):
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{pwd_hash}"


def verify_password(stored_hash, password):
    if not stored_hash:
        return False
    salt, pwd_hash = stored_hash.split(":")
    return hashlib.sha256((salt + password).encode()).hexdigest() == pwd_hash


def sanitize(text, max_len=5000):
    if not isinstance(text, str):
        return ""
    text = bleach.clean(text, tags=[], strip=True)
    return text[:max_len].strip()


def create_user(email, password, full_name, auth_provider="email", google_id=None, phone=None, country="GB", role="user"):
    conn = get_db()
    try:
        conn.execute(
            '''INSERT INTO users (email_encrypted, email_hash, password_hash, full_name,
               auth_provider, google_id, phone_encrypted, country_code, role)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (encrypt(email.lower().strip()),
             email_hash(email),
             hash_password(password) if password else None,
             sanitize(full_name, 100),
             auth_provider,
             google_id,
             encrypt(phone) if phone else None,
             sanitize(country, 5),
             role)
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE email_hash = ?", (email_hash(email),)).fetchone()
        return dict(user) if user else None
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email_hash = ?", (email_hash(email),)).fetchone()
    conn.close()
    if user:
        u = dict(user)
        u["email"] = decrypt(u["email_encrypted"])
        u["phone"] = decrypt(u.get("phone_encrypted"))
        return u
    return None


def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user:
        u = dict(user)
        u["email"] = decrypt(u["email_encrypted"])
        u["phone"] = decrypt(u.get("phone_encrypted"))
        return u
    return None


def authenticate_user(email, password):
    user = get_user_by_email(email)
    if user and user["password_hash"] and verify_password(user["password_hash"], password):
        return user
    return None


def check_login_lockout(email, ip, max_attempts, lockout_minutes):
    conn = get_db()
    cutoff = time.time() - (lockout_minutes * 60)
    cutoff_str = datetime.fromtimestamp(cutoff).strftime("%Y-%m-%d %H:%M:%S")
    count = conn.execute(
        "SELECT COUNT(*) FROM login_attempts WHERE email_hash = ? AND success = 0 AND attempted_at > ?",
        (email_hash(email), cutoff_str)
    ).fetchone()[0]
    conn.close()
    return count >= max_attempts


def record_login_attempt(email, ip, success):
    conn = get_db()
    conn.execute("INSERT INTO login_attempts (email_hash, ip_address, success) VALUES (?, ?, ?)",
                 (email_hash(email), ip, 1 if success else 0))
    if success:
        conn.execute("DELETE FROM login_attempts WHERE email_hash = ? AND success = 0",
                     (email_hash(email),))
    conn.commit()
    conn.close()


def update_user_profile(user_id, full_name=None, bio=None, phone=None, country=None):
    conn = get_db()
    updates, values = [], []
    if full_name:
        updates.append("full_name = ?")
        values.append(sanitize(full_name, 100))
    if bio is not None:
        updates.append("bio = ?")
        values.append(sanitize(bio, 500))
    if phone is not None:
        updates.append("phone_encrypted = ?")
        values.append(encrypt(phone))
    if country:
        updates.append("country_code = ?")
        values.append(sanitize(country, 5))
    updates.append("updated_at = ?")
    values.append(datetime.now().isoformat())
    values.append(user_id)
    conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def save_analysis(user_id, input_text, prediction, confidence, model_used):
    conn = get_db()
    conn.execute(
        "INSERT INTO analysis_history (user_id, input_text_encrypted, prediction, confidence, model_used) VALUES (?, ?, ?, ?, ?)",
        (user_id, encrypt(input_text[:500]), prediction, confidence, model_used))
    conn.commit()
    conn.close()


def get_analysis_history(user_id, limit=20):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM analysis_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["input_text"] = decrypt(d["input_text_encrypted"])
        result.append(d)
    return result


def save_chat(user_id, role, content):
    conn = get_db()
    conn.execute("INSERT INTO chat_history (user_id, role, content_encrypted) VALUES (?, ?, ?)",
                 (user_id, role, encrypt(content[:2000])))
    conn.commit()
    conn.close()


def get_chat_history(user_id, limit=20):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM chat_history WHERE user_id = ? ORDER BY created_at ASC LIMIT ?",
        (user_id, limit)).fetchall()
    conn.close()
    return [{"role": r["role"], "content": decrypt(r["content_encrypted"]), "created_at": r["created_at"]} for r in rows]


def create_crisis_alert(user_id, trigger_phrase, message, auto_escalate_at):
    user = get_user_by_id(user_id)
    conn = get_db()
    conn.execute(
        '''INSERT INTO crisis_alerts (user_id, trigger_phrase, user_message_encrypted,
           user_country, user_phone_encrypted, auto_escalate_at)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (user_id, trigger_phrase, encrypt(message[:1000]),
         user.get("country_code", "GB") if user else "GB",
         user.get("phone_encrypted") if user else None,
         auto_escalate_at))
    conn.commit()
    conn.close()


def get_pending_alerts():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM crisis_alerts WHERE status = 'pending' ORDER BY created_at DESC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["user_message"] = decrypt(d["user_message_encrypted"])
        d["user_phone"] = decrypt(d.get("user_phone_encrypted"))
        user = get_user_by_id(d["user_id"])
        d["user_name"] = user["full_name"] if user else "Unknown"
        d["user_email"] = user["email"] if user else "Unknown"
        result.append(d)
    return result


def resolve_alert(alert_id, action):
    conn = get_db()
    conn.execute(
        "UPDATE crisis_alerts SET status = ?, admin_action = ?, resolved_at = ? WHERE id = ?",
        (action, action, datetime.now().isoformat(), alert_id))
    conn.commit()
    conn.close()


def get_auto_escalate_alerts():
    conn = get_db()
    now = datetime.now().isoformat()
    rows = conn.execute(
        "SELECT * FROM crisis_alerts WHERE status = 'pending' AND auto_escalate_at <= ?",
        (now,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["user_message"] = decrypt(d["user_message_encrypted"])
        d["user_phone"] = decrypt(d.get("user_phone_encrypted"))
        result.append(d)
    return result


def get_all_users():
    conn = get_db()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["email"] = decrypt(d["email_encrypted"])
        d["phone"] = decrypt(d.get("phone_encrypted"))
        result.append(d)
    return result


if __name__ == "__main__":
    init_db()
    print("Database initialised.")
