import re

from flask import abort, g, redirect, request, session, url_for

from database import get_user_by_id

STATIC_FILE_RE = re.compile(
    r"\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)$",
    re.IGNORECASE,
)


def _is_api_or_trpc_route(path: str) -> bool:
    """Equivalent to Next matcher '/(api|trpc)(.*)'."""
    return path == '/api' or path.startswith('/api/') or path == '/trpc' or path.startswith('/trpc/')


def _is_static_or_internal(path: str) -> bool:
    """Equivalent to skipping _next and static file extensions."""
    if path.startswith('/_next/'):
        return True
    if path.startswith('/static/'):
        return True
    return bool(STATIC_FILE_RE.search(path))


def _matches_clerk_style_middleware(path: str) -> bool:
    """
    Flask approximation of:
      1) '/((?!_next|...static-extensions...).*)'
      2) '/(api|trpc)(.*)'
    """
    if _is_api_or_trpc_route(path):
        return True
    return not _is_static_or_internal(path)


def auth_middleware():
    """Flask equivalent of Clerk matcher + auth gate for protected routes."""
    path = request.path or '/'
    g.user = None

    if not _matches_clerk_style_middleware(path):
        return

    public_routes = {
        '/': True,
        '/login': True,
        '/register': True,
        '/about': True,
        '/password-reset': True,
        '/password-reset/': True,
    }
    if path in public_routes or path.startswith('/password-reset/'):
        return

    user_id = session.get('user_id')
    if user_id:
        g.user = get_user_by_id(user_id)
        if not g.user:
            session.clear()
            g.user = None

    if _is_api_or_trpc_route(path) or path.startswith(('/dashboard', '/profile', '/history', '/analyze')):
        if not g.user:
            if _is_api_or_trpc_route(path) or request.is_json:
                abort(401, description='Authentication required')
            session.clear()
            return redirect(url_for('login'))
