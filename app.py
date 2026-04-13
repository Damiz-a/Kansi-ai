import os, re, json, joblib, requests
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from database import (
    init_db, create_user, authenticate_user, get_user_by_id, get_user_by_email,
    update_user_profile, save_analysis, get_analysis_history, save_chat, get_chat_history,
    create_crisis_alert, get_pending_alerts, resolve_alert, get_auto_escalate_alerts,
    check_login_lockout, record_login_attempt, sanitize, get_all_users
)
from config import (
    FLASK_SECRET_KEY, ANTHROPIC_API_KEY, GOOGLE_CLIENT_ID,
    MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES, MAX_PAYLOAD_SIZE_BYTES,
    ALERT_TIMEOUT_SECONDS, TRIGGER_PHRASES, CRISIS_HOTLINES
)
from chatbot import respond as chatbot_respond

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.permanent_session_lifetime = timedelta(days=7)
app.config["MAX_CONTENT_LENGTH"] = MAX_PAYLOAD_SIZE_BYTES

limiter = Limiter(get_remote_address, app=app, default_limits=["120 per minute"], storage_uri="memory://")

init_db()

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
model = joblib.load(os.path.join(MODEL_DIR, "kansi_ai_model.pkl"))
tfidf = joblib.load(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"))
with open(os.path.join(MODEL_DIR, "training_results.json")) as f:
    training_results = json.load(f)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        g.user = get_user_by_id(session["user_id"])
        if not g.user:
            session.clear()
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        g.user = get_user_by_id(session["user_id"])
        if not g.user or g.user.get("role") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated


def clean_for_model(text):
    text = text.lower()
    text = re.sub(r"[^a-zA-Z\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def check_triggers(text):
    lower = text.lower().strip()
    for phrase in TRIGGER_PHRASES:
        if phrase in lower:
            return phrase
    return None


def predict_text(text):
    cleaned = clean_for_model(text)
    features = tfidf.transform([cleaned])
    prediction = model.predict(features)[0]
    if hasattr(model, "predict_proba"):
        confidence = float(max(model.predict_proba(features)[0])) * 100
    else:
        confidence = min(abs(float(model.decision_function(features)[0])) * 20, 99.0)
    label = "Depressive Indicators Detected" if prediction == 1 else "No Depressive Indicators"
    return prediction, label, round(confidence, 2)


def verify_google_token_via_claude(id_token):
    if not ANTHROPIC_API_KEY:
        return None
    try:
        resp = requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
            json={
                "model": "claude-sonnet-4-20250514", "max_tokens": 500,
                "system": "You are a helper that verifies Google OAuth tokens. Given a Google ID token, extract and return ONLY a JSON object with keys: email, name, sub (Google user ID), picture. If the token appears invalid, return {\"error\": \"invalid\"}. Return raw JSON only, no markdown.",
                "messages": [{"role": "user", "content": f"Verify this Google ID token and extract user info: {id_token}"}]
            }, timeout=15)
        data = resp.json()
        text = data.get("content", [{}])[0].get("text", "")
        text = text.strip().strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()
        return json.loads(text)
    except Exception:
        return None


@app.before_request
def enforce_payload():
    if request.content_length and request.content_length > MAX_PAYLOAD_SIZE_BYTES:
        abort(413)


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/terms")
def terms():
    user = get_user_by_id(session["user_id"]) if "user_id" in session else None
    return render_template("terms.html", user=user)


@app.route("/register", methods=["GET", "POST"])
@limiter.limit(f"{MAX_LOGIN_ATTEMPTS} per {LOGIN_LOCKOUT_MINUTES} minutes", methods=["POST"])
def register():
    if request.method == "POST":
        email = sanitize(request.form.get("email", ""), 254).lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        full_name = sanitize(request.form.get("full_name", ""), 100)
        phone = sanitize(request.form.get("phone", ""), 20)
        country = sanitize(request.form.get("country", "GB"), 5)
        agreed = request.form.get("agree_terms")

        if not all([email, password, full_name]):
            flash("All fields are required.", "error")
            return render_template("register.html")
        if not agreed:
            flash("You must agree to the terms and conditions.", "error")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("register.html")
        if get_user_by_email(email):
            flash("An account with this email already exists.", "error")
            return render_template("register.html")

        user = create_user(email, password, full_name, phone=phone, country=country)
        if user:
            session["user_id"] = user["id"]
            session.permanent = True
            flash(f"Welcome to Kansi AI, {full_name}!", "success")
            return redirect(url_for("dashboard"))
        flash("Registration failed.", "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
@limiter.limit(f"{MAX_LOGIN_ATTEMPTS} per {LOGIN_LOCKOUT_MINUTES} minutes", methods=["POST"])
def login():
    if request.method == "POST":
        email = sanitize(request.form.get("email", ""), 254).lower()
        password = request.form.get("password", "")
        ip = get_remote_address()

        if check_login_lockout(email, ip, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_MINUTES):
            flash(f"Too many attempts. Try again in {LOGIN_LOCKOUT_MINUTES} minutes.", "error")
            return render_template("login.html")

        user = authenticate_user(email, password)
        if user:
            record_login_attempt(email, ip, True)
            session["user_id"] = user["id"]
            session.permanent = True
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for("dashboard"))
        record_login_attempt(email, ip, False)
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/auth/google", methods=["POST"])
@limiter.limit("10 per minute")
def google_auth():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    id_token = data.get("id_token")
    email = sanitize(data.get("email", ""), 254).lower()
    name = sanitize(data.get("name", ""), 100)
    google_id = sanitize(data.get("google_id", ""), 200)

    if id_token and ANTHROPIC_API_KEY:
        verified = verify_google_token_via_claude(id_token)
        if verified and not verified.get("error"):
            email = verified.get("email", email)
            name = verified.get("name", name)
            google_id = verified.get("sub", google_id)

    if not email:
        return jsonify({"error": "Email required"}), 400

    user = get_user_by_email(email)
    if not user:
        user = create_user(email=email, password=None, full_name=name or email.split("@")[0],
                           auth_provider="google", google_id=google_id)
    if user:
        session["user_id"] = user["id"]
        session.permanent = True
        return jsonify({"success": True, "redirect": url_for("dashboard")})
    return jsonify({"error": "Authentication failed"}), 400


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    history = get_analysis_history(g.user["id"], limit=10)
    return render_template("dashboard.html", user=g.user, history=history, results=training_results)


@app.route("/chat")
@login_required
def chat_page():
    history = get_chat_history(g.user["id"], limit=50)
    return render_template("chat.html", user=g.user, chat_history=history)


@app.route("/api/chat", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def api_chat():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    msg = sanitize(data.get("message", ""), 2000)
    if not msg:
        return jsonify({"error": "Message required"}), 400

    trigger = check_triggers(msg)
    if trigger:
        escalate_time = (datetime.now() + timedelta(seconds=ALERT_TIMEOUT_SECONDS)).isoformat()
        create_crisis_alert(g.user["id"], trigger, msg, escalate_time)

    save_chat(g.user["id"], "user", msg)
    reply = chatbot_respond(msg, g.user["full_name"])
    save_chat(g.user["id"], "assistant", reply)
    return jsonify({"reply": reply})


@app.route("/analyze", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def analyze():
    text = sanitize(request.form.get("text", ""), 5000)
    if not text or len(text) < 10:
        flash("Please enter at least 10 characters.", "warning")
        return redirect(url_for("dashboard"))

    trigger = check_triggers(text)
    if trigger:
        escalate_time = (datetime.now() + timedelta(seconds=ALERT_TIMEOUT_SECONDS)).isoformat()
        create_crisis_alert(g.user["id"], trigger, text, escalate_time)

    prediction_num, label, confidence = predict_text(text)
    save_analysis(g.user["id"], text, label, confidence, training_results.get("model_name", "Logistic Regression"))
    return render_template("result.html", user=g.user, text=text, prediction=label,
                           confidence=confidence, is_depressive=(prediction_num == 1))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        update_user_profile(g.user["id"],
            full_name=sanitize(request.form.get("full_name", ""), 100),
            bio=sanitize(request.form.get("bio", ""), 500),
            phone=sanitize(request.form.get("phone", ""), 20),
            country=sanitize(request.form.get("country", ""), 5))
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))
    history = get_analysis_history(g.user["id"], limit=50)
    return render_template("profile.html", user=g.user, history=history)


@app.route("/history")
@login_required
def history():
    return render_template("history.html", user=g.user, history=get_analysis_history(g.user["id"], limit=100))


@app.route("/about")
def about():
    user = get_user_by_id(session["user_id"]) if "user_id" in session else None
    return render_template("about.html", user=user, results=training_results)


@app.route("/admin")
@admin_required
def admin_panel():
    alerts = get_pending_alerts()
    auto = get_auto_escalate_alerts()
    for a in auto:
        resolve_alert(a["id"], "auto_escalated")
    return render_template("admin.html", user=g.user, alerts=alerts, users=get_all_users(),
                           hotlines=CRISIS_HOTLINES, auto_escalated=len(auto))


@app.route("/admin/alert/<int:alert_id>/<action>", methods=["POST"])
@admin_required
@limiter.limit("30 per minute")
def handle_alert(alert_id, action):
    if action not in ("escalated", "cancelled"):
        abort(400)
    resolve_alert(alert_id, action)
    flash(f"Alert {alert_id} {action}.", "success" if action == "cancelled" else "warning")
    return redirect(url_for("admin_panel"))


@app.route("/api/analyze", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def api_analyze():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    text = sanitize(data.get("text", ""), 5000)
    if not text:
        return jsonify({"error": "Text required"}), 400
    _, label, confidence = predict_text(text)
    return jsonify({"prediction": label, "confidence": confidence, "model": training_results.get("model_name")})


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "Payload too large"}), 413

@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"error": "Too many requests. Please slow down."}), 429

@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
