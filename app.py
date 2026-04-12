
import json
import logging
import os
import re
import secrets
from datetime import timedelta
from functools import wraps

import joblib
from flask import (
    Flask, abort, flash, g, jsonify, redirect, render_template,
    request, session, url_for
)
from flask_wtf.csrf import CSRFError, CSRFProtect, generate_csrf

from config import BaseConfig, TestConfig
from database import (
    authenticate_user,
    count_security_events,
    create_password_reset_token,
    create_user,
    get_analysis_history,
    get_password_reset_record,
    get_recent_security_events,
    get_user_by_email,
    get_user_by_id,
    init_db,
    mark_password_reset_used,
    record_security_event,
    save_analysis,
    set_user_admin,
    update_user_password,
    update_user_profile,
)
from security import (
    SecretRedactionFilter,
    ValidationError,
    ensure_safe_fetch_url,
    expiry_iso,
    generate_reset_token,
    is_expired,
    normalize_email,
    token_hash,
    validate_analysis_text,
    validate_bio,
    validate_email,
    validate_full_name,
    validate_password,
    verify_webhook_signature,
)


from middleware import auth_middleware

csrf = CSRFProtect()


CHAT_STARTERS = [
    "I have been feeling disconnected from everything lately.",
    "My thoughts feel heavy and I do not know where to begin.",
    "I need help making sense of how I have been feeling this week."
]


def create_app():
    app = Flask(__name__)
    app_config = TestConfig if os.getenv('KANSI_ENV') == 'test' else BaseConfig
    app.config.from_object(app_config)
    app.permanent_session_lifetime = timedelta(days=app.config['PERMANENT_SESSION_LIFETIME_DAYS'])

    if not app.config['SECRET_KEY']:
        if app.config.get('ENV_NAME') == 'production':
            raise RuntimeError('Set KANSI_SECRET_KEY before starting the app.')
        app.config['SECRET_KEY'] = secrets.token_urlsafe(32)

    configure_logging(app)
    csrf.init_app(app)
    init_db()

    model_dir = os.path.join(os.path.dirname(__file__), 'models')
    app.config['MODEL'] = joblib.load(os.path.join(model_dir, 'kansi_ai_model.pkl'))
    app.config['TFIDF'] = joblib.load(os.path.join(model_dir, 'tfidf_vectorizer.pkl'))
    app.config['LABEL_ENCODER'] = joblib.load(os.path.join(model_dir, 'label_encoder.pkl'))
    with open(os.path.join(model_dir, 'training_results.json'), 'r') as handle:
        app.config['TRAINING_RESULTS'] = json.load(handle)

    register_security_hooks(app)
    register_routes(app)
    register_error_handlers(app)
    return app


def configure_logging(app):
    app.logger.setLevel(getattr(logging, app.config['SECURITY_LOG_LEVEL'], logging.INFO))
    if not any(isinstance(f, SecretRedactionFilter) for f in app.logger.filters):
        app.logger.addFilter(SecretRedactionFilter())


def is_api_request():
    return request.path.startswith('/api/') or request.is_json


def log_security_event(app, level, message, **metadata):
    redacted = {key: value for key, value in metadata.items() if key not in {'token', 'password', 'text'}}
    getattr(app.logger, level)(f"{message} | {json.dumps(redacted, sort_keys=True)}")


def get_request_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def rate_limit_exceeded(event_type, limit, window_seconds, subject=None):
    from datetime import datetime, timedelta, timezone
    since_iso = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).isoformat()
    ip_address = get_request_ip()
    ip_count = count_security_events(event_type, since_iso, ip_address=ip_address)
    subject_count = count_security_events(event_type, since_iso, subject=subject) if subject else 0
    return ip_count >= limit or subject_count >= limit


def record_rate_limit_hit(event_type, subject=None):
    record_security_event(
        event_type=event_type,
        subject=subject,
        ip_address=get_request_ip(),
        metadata={'path': request.path}
    )


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            record_security_event('access_denied', subject='anonymous', ip_address=get_request_ip(), metadata={'path': request.path})
            if is_api_request():
                abort(401)
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not g.user.get('is_admin'):
            record_security_event(
                'admin_access_denied',
                subject=str(g.user['id']),
                ip_address=get_request_ip(),
                metadata={'path': request.path}
            )
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def clean_input_text(text):
    """Normalize user text before vectorization."""
    cleaned = text.lower()
    cleaned = re.sub(r'http\S+|www\.\S+', '', cleaned)
    cleaned = re.sub(r'@\w+', '', cleaned)
    cleaned = re.sub(r'#\w+', '', cleaned)
    cleaned = re.sub(r'[^a-zA-Z\s]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def analyze_text_input(text):
    """Run the local model and return structured analysis data."""
    cleaned = clean_input_text(text)
    features = app.config['TFIDF'].transform([cleaned])
    model = app.config['MODEL']

    if hasattr(model, 'predict_proba'):
        probabilities = model.predict_proba(features)[0]
        prediction = model.predict(features)[0]
        confidence = float(max(probabilities)) * 100
    else:
        prediction = model.predict(features)[0]
        decision = model.decision_function(features)[0]
        confidence = min(abs(float(decision)) * 20, 99.0)

    label = 'Depressive Indicators Detected' if prediction == 1 else 'No Depressive Indicators'
    return {
        'prediction': int(prediction),
        'label': label,
        'confidence': round(confidence, 2),
        'model': app.config['TRAINING_RESULTS'].get('model_name', 'Logistic Regression'),
    }


def detect_emotional_signals(text):
    lowered = text.lower()
    signal_map = {
        'overwhelmed': ['overwhelmed', 'too much', 'cant cope', "can't cope", 'burned out', 'burnt out'],
        'sad': ['sad', 'down', 'empty', 'hopeless', 'low', 'numb'],
        'anxious': ['anxious', 'worried', 'panic', 'afraid', 'stressed', 'uneasy'],
        'lonely': ['alone', 'lonely', 'isolated', 'disconnected'],
        'tired': ['tired', 'exhausted', 'drained', 'sleep', 'insomnia'],
    }
    return [signal for signal, keywords in signal_map.items() if any(keyword in lowered for keyword in keywords)]


def has_high_risk_language(text):
    lowered = text.lower()
    urgent_markers = [
        'suicide', 'kill myself', 'end my life', 'dont want to live',
        "don't want to live", 'self harm', 'hurt myself'
    ]
    return any(marker in lowered for marker in urgent_markers)


def build_chatbot_reply(user_name, text, analysis):
    signals = detect_emotional_signals(text)
    confidence = analysis['confidence']
    is_distress = analysis['prediction'] == 1
    risk_detected = has_high_risk_language(text)

    opening = f"{user_name}, thank you for sharing that. "
    if risk_detected:
        message = (
            opening +
            "What you wrote sounds urgent, and I want to respond carefully. "
            "Please contact local emergency support now or reach out to Samaritans at 116 123 if you are in the UK. "
            "If you are in the US or Canada, call or text 988. If texting feels easier, message a trusted person and tell them you need immediate support."
        )
        suggestions = [
            "Move closer to another person or call someone you trust right now.",
            "Use an emergency or crisis line in your area as soon as possible.",
            "Come back after you are safe if you want help organizing what to say."
        ]
        return message, suggestions, "Urgent support recommended"

    if 'overwhelmed' in signals:
        reflection = "It sounds like things may be piling up faster than you can recover from them. "
    elif 'sad' in signals:
        reflection = "Your words carry a lot of heaviness, and that deserves care. "
    elif 'anxious' in signals:
        reflection = "I can hear a lot of tension and uncertainty in the way you described this. "
    elif 'lonely' in signals:
        reflection = "Feeling disconnected can make even ordinary moments feel harder to carry. "
    elif 'tired' in signals:
        reflection = "It sounds like your energy has been stretched thin for a while. "
    else:
        reflection = "I am hearing that this has been difficult to hold on your own. "

    if is_distress:
        guidance = (
            f"My screening model picked up signs of emotional distress with about {confidence}% confidence. "
            "That is not a diagnosis, but it does suggest this may be a good moment to slow down and involve support."
        )
        status = "Emotional strain detected"
        suggestions = [
            "Name one person you could contact today, even with a short message.",
            "Write one concrete thing that has felt hardest in the last 24 hours.",
            "If this feeling keeps rising, consider speaking with a counselor, GP, or mental health professional."
        ]
    else:
        guidance = (
            f"My screening model did not find strong depressive indicators in this message and estimated {confidence}% confidence. "
            "Even so, your experience still matters, and we can keep unpacking it together."
        )
        status = "Supportive check-in"
        suggestions = [
            "Tell me what part of today has felt heaviest or most confusing.",
            "Try describing what you need most right now: rest, clarity, comfort, or connection.",
            "If it helps, we can turn this into a small plan for the next few hours."
        ]

    closing = (
        " If you want, send another message about what happened, what you are feeling in your body, "
        "or what kind of support you wish you had right now."
    )
    return opening + reflection + guidance + closing, suggestions, status


def register_security_hooks(app):
    @app.before_request
    def auth_middleware_wrapper():
        auth_middleware()

    @app.before_request
    def load_current_user():
        g.user = None
        user_id = session.get('user_id')
        if user_id is not None:
            g.user = get_user_by_id(user_id)
            if not g.user:
                session.clear()

    @app.before_request
    def enforce_same_origin():
        if request.method in {'GET', 'HEAD', 'OPTIONS'}:
            return
        if request.endpoint == 'webhook_events':
            return
        origin = request.headers.get('Origin')
        if not origin:
            return
        allowed_origins = set(app.config['TRUSTED_ORIGINS'])
        allowed_origins.add(request.host_url.rstrip('/'))
        if origin not in allowed_origins:
            record_security_event('origin_blocked', subject=request.endpoint, ip_address=get_request_ip(), metadata={'origin': origin})
            abort(403)

    @app.after_request
    def add_security_headers(response):
        origin = request.headers.get('Origin')
        allowed_origins = set(app.config['TRUSTED_ORIGINS'])
        allowed_origins.add(request.host_url.rstrip('/'))
        if origin and origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Vary'] = 'Origin'

        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
        response.headers['Cache-Control'] = 'no-store' if request.path.startswith('/api/') else 'no-cache'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self'; "
            "connect-src 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
        if app.config['SESSION_COOKIE_SECURE']:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    @app.context_processor
    def inject_template_defaults():
        return {
            'user': getattr(g, 'user', None),
            'csrf_token_value': generate_csrf(),
            'site_url': app.config['SITE_URL'] or request.url_root.rstrip('/'),
            'preview_image_url': f"{app.config['SITE_URL'] or request.url_root.rstrip('/')}{url_for('static', filename='img/social-preview.svg')}",
            'demo_google_auth_enabled': app.config['ENABLE_DEMO_GOOGLE_AUTH'],
        }


def render_error(status_code, title, message):
    if is_api_request():
        return jsonify({'error': message}), status_code
    return render_template('error.html', status_code=status_code, title=title, message=message), status_code


def register_error_handlers(app):
    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        record_security_event('csrf_rejected', subject=request.endpoint, ip_address=get_request_ip(), metadata={'reason': error.description})
        return render_error(400, 'Request blocked', 'Your session token was missing or invalid. Please refresh the page and try again.')

    @app.errorhandler(400)
    def bad_request(_error):
        return render_error(400, 'Bad request', 'The request could not be processed safely.')

    @app.errorhandler(401)
    def unauthorized(_error):
        return render_error(401, 'Unauthorized', 'Please log in to continue.')

    @app.errorhandler(403)
    def forbidden(_error):
        return render_error(403, 'Forbidden', 'You do not have permission to access this resource.')

    @app.errorhandler(404)
    def not_found(_error):
        return render_error(404, 'Not found', 'The page you requested could not be found.')

    @app.errorhandler(429)
    def too_many_requests(_error):
        return render_error(429, 'Too many requests', 'Too many attempts were detected. Please wait and try again.')

    @app.errorhandler(500)
    def internal_error(error):
        log_security_event(app, 'error', 'Internal server error', path=request.path, endpoint=request.endpoint, error=str(error))
        return render_error(500, 'Server error', 'Something went wrong. Please try again in a moment.')


def register_routes(app):
    @app.route('/')
    def index():
        if g.user:
            return redirect(url_for('dashboard'))
        return render_template('index.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            try:
                email = validate_email(request.form.get('email', ''))
                password = validate_password(request.form.get('password', ''))
                confirm_password = request.form.get('confirm_password', '')
                full_name = validate_full_name(request.form.get('full_name', ''))
            except ValidationError as exc:
                flash(str(exc), 'error')
                return render_template('register.html'), 400

            if password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('register.html'), 400

            if rate_limit_exceeded('register_attempt', limit=5, window_seconds=900, subject=email):
                abort(429)

            if get_user_by_email(email):
                record_rate_limit_hit('register_attempt', subject=email)
                flash('An account with this email already exists.', 'error')
                return render_template('register.html'), 400

            user = create_user(email, password, full_name)
            if user:
                session.clear()
                session['user_id'] = user['id']
                session.permanent = True
                flash('Account created successfully. Welcome to Kansi AI.', 'success')
                return redirect(url_for('dashboard'))

            flash('Registration failed. Please try again.', 'error')
            return render_template('register.html'), 400

        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            try:
                email = validate_email(request.form.get('email', ''))
            except ValidationError as exc:
                flash(str(exc), 'error')
                return render_template('login.html'), 400

            password = request.form.get('password', '')
            if rate_limit_exceeded('login_failed', limit=5, window_seconds=900, subject=email):
                log_security_event(app, 'warning', 'Login rate limit exceeded', email=email, ip=get_request_ip())
                abort(429)

            user = authenticate_user(email, password)
            if user:
                session.clear()
                session['user_id'] = user['id']
                session.permanent = True
                flash(f'Welcome back, {user["full_name"]}.', 'success')
                return redirect(url_for('dashboard'))

            record_rate_limit_hit('login_failed', subject=email)
            flash('Invalid email or password.', 'error')
            return render_template('login.html'), 400

        return render_template('login.html')

    @app.route('/auth/google', methods=['POST'])
    def google_auth():
        if not app.config['ENABLE_DEMO_GOOGLE_AUTH']:
            abort(403)
        data = request.get_json(silent=True) or {}
        try:
            email = validate_email(data.get('email', ''))
            full_name = validate_full_name(data.get('name') or normalize_email(email).split('@')[0].replace('.', ' '))
        except ValidationError as exc:
            return jsonify({'error': str(exc)}), 400

        google_id = (data.get('google_id') or '').strip()[:255] or None
        picture = (data.get('picture') or '').strip()[:500] or None

        if rate_limit_exceeded('google_auth_attempt', limit=10, window_seconds=900, subject=email):
            abort(429)

        user = get_user_by_email(email)
        if not user:
            user = create_user(
                email=email,
                password=None,
                full_name=full_name,
                auth_provider='google',
                google_id=google_id,
                profile_picture=picture
            )

        if user:
            session.clear()
            session['user_id'] = user['id']
            session.permanent = True
            return jsonify({'success': True, 'redirect': url_for('dashboard')})

        record_rate_limit_hit('google_auth_attempt', subject=email)
        return jsonify({'error': 'Authentication failed.'}), 400

    @app.route('/logout', methods=['POST'])
    @login_required
    def logout():
        session.clear()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        history = get_analysis_history(g.user['id'], limit=10)
        return render_template(
            'dashboard.html',
            history=history,
            results=app.config['TRAINING_RESULTS'],
            chat_starters=CHAT_STARTERS
        )

    @app.route('/analyze', methods=['POST'])
    @login_required
    def analyze():
        try:
            text = validate_analysis_text(request.form.get('text', ''))
        except ValidationError as exc:
            flash(str(exc), 'warning')
            return redirect(url_for('dashboard'))

        if rate_limit_exceeded('analyze', limit=20, window_seconds=3600, subject=str(g.user['id'])):
            abort(429)

        analysis = analyze_text_input(text)
        save_analysis(
            user_id=g.user['id'],
            input_text=text[:500],
            prediction=analysis['label'],
            confidence=analysis['confidence'],
            model_used=analysis['model']
        )
        record_rate_limit_hit('analyze', subject=str(g.user['id']))

        return render_template(
            'result.html',
            text=text,
            prediction=analysis['label'],
            confidence=analysis['confidence'],
            is_depressive=(analysis['prediction'] == 1)
        )

    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        if request.method == 'POST':
            try:
                full_name = validate_full_name(request.form.get('full_name', ''))
                bio = validate_bio(request.form.get('bio', ''))
            except ValidationError as exc:
                flash(str(exc), 'error')
                history = get_analysis_history(g.user['id'], limit=50)
                return render_template('profile.html', history=history), 400

            update_user_profile(g.user['id'], full_name=full_name, bio=bio)
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('profile'))

        history = get_analysis_history(g.user['id'], limit=50)
        return render_template('profile.html', history=history)

    @app.route('/history')
    @login_required
    def history():
        analyses = get_analysis_history(g.user['id'], limit=100)
        return render_template('history.html', history=analyses)

    @app.route('/about')
    def about():
        return render_template('about.html', results=app.config['TRAINING_RESULTS'])

    @app.route('/password-reset', methods=['GET', 'POST'])
    def password_reset_request():
        reset_link = None
        if request.method == 'POST':
            email_raw = request.form.get('email', '')
            try:
                email = validate_email(email_raw)
            except ValidationError:
                email = normalize_email(email_raw) if email_raw else ''

            if rate_limit_exceeded('password_reset_request', limit=5, window_seconds=3600, subject=email or None):
                abort(429)

            user = get_user_by_email(email) if email else None
            if user and user.get('auth_provider') == 'email':
                token, hashed = generate_reset_token()
                create_password_reset_token(user['id'], hashed, expiry_iso(app.config['PASSWORD_RESET_TTL_MINUTES']))
                if app.config['SHOW_RESET_LINKS']:
                    reset_link = url_for('password_reset', token=token, _external=False)
            record_rate_limit_hit('password_reset_request', subject=email or 'unknown')
            flash('If the account exists, a reset link has been prepared.', 'info')
        return render_template('reset_request.html', reset_link=reset_link)

    @app.route('/password-reset/<token>', methods=['GET', 'POST'])
    def password_reset(token):
        record = get_password_reset_record(token_hash(token))
        if not record or record.get('used_at') or is_expired(record['expires_at']):
            abort(404)

        if request.method == 'POST':
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            try:
                validate_password(password)
            except ValidationError as exc:
                flash(str(exc), 'error')
                return render_template('reset_password.html', token=token), 400

            if password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('reset_password.html', token=token), 400

            update_user_password(record['user_id'], password)
            mark_password_reset_used(token_hash(token))
            flash('Password updated successfully. You can log in now.', 'success')
            return redirect(url_for('login'))

        return render_template('reset_password.html', token=token)

    @app.route('/admin/security')
    @admin_required
    def admin_security():
        return render_template('admin_security.html', security_events=get_recent_security_events(limit=25))

    @app.route('/api/analyze', methods=['POST'])
    @login_required
    def api_analyze():
        data = request.get_json(silent=True) or {}
        try:
            text = validate_analysis_text(data.get('text', ''))
        except ValidationError as exc:
            return jsonify({'error': str(exc)}), 400

        if rate_limit_exceeded('api_analyze', limit=20, window_seconds=3600, subject=str(g.user['id'])):
            abort(429)

        analysis = analyze_text_input(text)
        record_rate_limit_hit('api_analyze', subject=str(g.user['id']))
        return jsonify({
            'prediction': 'depressive' if analysis['prediction'] == 1 else 'non_depressive',
            'confidence': analysis['confidence'],
            'model': analysis['model'],
            'disclaimer': 'This is a screening tool, not a clinical diagnosis. Please consult a mental health professional.'
        })

    @app.route('/api/chat', methods=['POST'])
    @login_required
    def api_chat():
        data = request.get_json(silent=True) or {}
        try:
            text = validate_analysis_text(data.get('text', ''))
        except ValidationError as exc:
            return jsonify({'error': str(exc)}), 400

        if rate_limit_exceeded('api_chat', limit=30, window_seconds=3600, subject=str(g.user['id'])):
            abort(429)

        analysis = analyze_text_input(text)
        reply, suggestions, status = build_chatbot_reply(g.user['full_name'], text, analysis)

        save_analysis(
            user_id=g.user['id'],
            input_text=text[:500],
            prediction=analysis['label'],
            confidence=analysis['confidence'],
            model_used=analysis['model']
        )
        record_rate_limit_hit('api_chat', subject=str(g.user['id']))

        return jsonify({
            'reply': reply,
            'suggestions': suggestions,
            'analysis': {
                'label': analysis['label'],
                'confidence': analysis['confidence'],
                'model': analysis['model'],
                'status': status,
            },
            'disclaimer': 'Kansi AI offers supportive screening, not clinical diagnosis.'
        })

    @csrf.exempt
    @app.route('/webhooks/events', methods=['POST'])
    def webhook_events():
        raw_body = request.get_data(cache=True)
        signature = request.headers.get('X-Kansi-Signature', '')
        if not verify_webhook_signature(app.config['SECURITY_WEBHOOK_SECRET'], raw_body, signature):
            record_security_event('webhook_rejected', subject='signature', ip_address=get_request_ip(), metadata={'path': request.path})
            abort(403)

        payload = request.get_json(silent=True) or {}
        if 'event' not in payload:
            return jsonify({'error': 'Missing event field.'}), 400

        record_security_event('webhook_accepted', subject=str(payload['event']), ip_address=get_request_ip())
        return jsonify({'status': 'accepted'}), 200

    @app.route('/api/support-preview', methods=['POST'])
    @admin_required
    def support_preview():
        data = request.get_json(silent=True) or {}
        try:
            url = ensure_safe_fetch_url(data.get('url', ''), app.config['SECURITY_ALLOWED_FETCH_HOSTS'])
        except ValidationError as exc:
            return jsonify({'error': str(exc)}), 400
        return jsonify({'allowed_url': url})


app = create_app()


if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    app.run(debug=app.config['DEBUG'], host='127.0.0.1', port=port)
