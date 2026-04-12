from functools import wraps
from flask import request, abort, redirect, url_for, jsonify, session, g
from database import get_user_by_id

def is_api_request():
    \"\"\"Check if request is API call.\"\"\"
    return request.path.startswith('/api/') or request.is_json or request.path.startswith('/webhooks/')

def is_static_request():
    \"\"\"Check if request is for static assets.\"\"\"
    return (
        request.path.startswith('/static/') or
        request.path in ['/favicon.ico'] or
        any(request.path.endswith(ext) for ext in ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico'])
    )

def auth_middleware():
    \"\"\"Flask equivalent of Clerk middleware: protect dynamic/API routes, skip static/public.\"\"\"
    # Skip static files, public routes
    if is_static_request():
        return

    public_routes = {
        '/': True,
        '/login': True,
        '/register': True,
        '/about': True,
        '/password-reset': True,
        '/password-reset/': True  # prefix match
    }
    if request.path in public_routes or request.path.startswith('/password-reset/'):
        return

    # Load user if session present
    user_id = session.get('user_id')
    if user_id:
        g.user = get_user_by_id(user_id)
        if not g.user:
            session.clear()
            g.user = None

    # Protect API/dynamic routes (Clerk matcher equivalent)
    if is_api_request() or request.path.startswith(('/dashboard', '/profile', '/history', '/analyze')):
        if not g.user:
            if is_api_request():
                abort(401, description='Authentication required')
            session.clear()
            return redirect(url_for('login'))

