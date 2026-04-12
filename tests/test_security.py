import hashlib
import hmac
import re


def extract_csrf_token(html):
    patterns = [
        r'name="csrf_token" value="([^"]+)"',
        r'meta name="csrf-token" content="([^"]+)"'
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    raise AssertionError('CSRF token not found in response.')


def login_session(client, user_id):
    with client.session_transaction() as session:
        session['user_id'] = user_id


def test_homepage_sets_security_headers_and_preview_metadata(client):
    response = client.get('/')
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'Content-Security-Policy' in response.headers
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert 'kansi-favicon.svg' in html
    assert 'og:image' in html
    assert 'social-preview.svg' in html


def test_csrf_blocks_login_without_token(client):
    response = client.post('/login', data={'email': 'user@example.com', 'password': 'ExamplePassword1'})
    assert response.status_code == 400
    assert 'session token was missing or invalid' in response.get_data(as_text=True).lower()


def test_register_hashes_password_with_argon2(client, database):
    page = client.get('/register')
    csrf_token = extract_csrf_token(page.get_data(as_text=True))

    response = client.post(
        '/register',
        data={
            'csrf_token': csrf_token,
            'full_name': 'Taylor Secure',
            'email': 'taylor@example.com',
            'password': 'SecurePassword1',
            'confirm_password': 'SecurePassword1',
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    user = database.get_user_by_email('taylor@example.com')
    assert user['password_hash'].startswith('$argon2')


def test_authenticated_chat_requires_csrf_and_returns_reply(client, database):
    user = database.get_user_by_email('chat@example.com') or database.create_user(
        'chat@example.com', 'SecurePassword1', 'Chat Example'
    )
    login_session(client, user['id'])

    no_csrf = client.post('/api/chat', json={'text': 'I have been feeling low and overwhelmed lately.'})
    assert no_csrf.status_code == 400

    page = client.get('/dashboard')
    csrf_token = extract_csrf_token(page.get_data(as_text=True))
    response = client.post(
        '/api/chat',
        json={'text': 'I have been feeling low and overwhelmed lately.'},
        headers={'X-CSRFToken': csrf_token}
    )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload['analysis']['label']
    assert payload['reply']


def test_login_rate_limiting_returns_429(client):
    page = client.get('/login')
    csrf_token = extract_csrf_token(page.get_data(as_text=True))

    for _ in range(5):
        response = client.post(
            '/login',
            data={
                'csrf_token': csrf_token,
                'email': 'unknown@example.com',
                'password': 'WrongPassword1',
            }
        )
        assert response.status_code in {400, 429}

    final_response = client.post(
        '/login',
        data={
            'csrf_token': csrf_token,
            'email': 'unknown@example.com',
            'password': 'WrongPassword1',
        }
    )
    assert final_response.status_code == 429


def test_password_reset_flow_updates_password(client, database):
    user = database.get_user_by_email('reset@example.com') or database.create_user(
        'reset@example.com', 'OldPassword1A', 'Reset Example'
    )

    request_page = client.get('/password-reset')
    request_token = extract_csrf_token(request_page.get_data(as_text=True))
    response = client.post(
        '/password-reset',
        data={'csrf_token': request_token, 'email': user['email']},
        follow_redirects=True
    )

    html = response.get_data(as_text=True)
    link_match = re.search(r'/password-reset/([A-Za-z0-9_\-]+)', html)
    assert link_match, html
    reset_token = link_match.group(1)

    reset_page = client.get(f'/password-reset/{reset_token}')
    csrf_token = extract_csrf_token(reset_page.get_data(as_text=True))
    update = client.post(
        f'/password-reset/{reset_token}',
        data={
            'csrf_token': csrf_token,
            'password': 'NewPassword1A',
            'confirm_password': 'NewPassword1A',
        },
        follow_redirects=False
    )

    assert update.status_code == 302
    assert database.authenticate_user('reset@example.com', 'NewPassword1A')


def test_admin_protection_and_history_ownership(client, database):
    owner = database.get_user_by_email('owner@example.com') or database.create_user(
        'owner@example.com', 'OwnerPassword1', 'Owner Person'
    )
    other = database.get_user_by_email('other@example.com') or database.create_user(
        'other@example.com', 'OtherPassword1', 'Other Person'
    )
    admin = database.get_user_by_email('admin@example.com') or database.create_user(
        'admin@example.com', 'AdminPassword1', 'Admin Person'
    )
    database.set_user_admin(admin['id'], True)
    database.save_analysis(owner['id'], 'owner secret entry', 'No Depressive Indicators', 20.0, 'Logistic Regression')
    database.save_analysis(other['id'], 'other secret entry', 'No Depressive Indicators', 20.0, 'Logistic Regression')

    login_session(client, owner['id'])
    history = client.get('/history')
    html = history.get_data(as_text=True)
    assert 'owner secret entry' in html
    assert 'other secret entry' not in html

    blocked = client.get('/admin/security')
    assert blocked.status_code == 403

    login_session(client, admin['id'])
    allowed = client.get('/admin/security')
    assert allowed.status_code == 200


def test_webhook_signature_verification(client, app):
    payload = b'{"event":"delivery"}'
    bad = client.post('/webhooks/events', data=payload, content_type='application/json', headers={'X-Kansi-Signature': 'sha256=bad'})
    assert bad.status_code == 403

    signature = hmac.new(app.config['SECURITY_WEBHOOK_SECRET'].encode(), payload, hashlib.sha256).hexdigest()
    good = client.post(
        '/webhooks/events',
        data=payload,
        content_type='application/json',
        headers={'X-Kansi-Signature': f'sha256={signature}'}
    )
    assert good.status_code == 200
    assert good.get_json()['status'] == 'accepted'


def test_ssrf_protection_blocks_private_hosts_and_allows_allowlisted_https(client, database):
    admin = database.get_user_by_email('ssrf-admin@example.com') or database.create_user(
        'ssrf-admin@example.com', 'AdminPassword1', 'SSRF Admin'
    )
    database.set_user_admin(admin['id'], True)
    login_session(client, admin['id'])

    page = client.get('/dashboard')
    csrf_token = extract_csrf_token(page.get_data(as_text=True))

    blocked = client.post(
        '/api/support-preview',
        json={'url': 'https://localhost/private'},
        headers={'X-CSRFToken': csrf_token}
    )
    assert blocked.status_code == 400

    allowed = client.post(
        '/api/support-preview',
        json={'url': 'https://findahelpline.com/help'},
        headers={'X-CSRFToken': csrf_token}
    )
    assert allowed.status_code == 200
    assert allowed.get_json()['allowed_url'] == 'https://findahelpline.com/help'


def test_safe_error_pages_do_not_leak_tracebacks(client):
    response = client.get('/__boom')
    body = response.get_data(as_text=True)
    assert response.status_code == 500
    assert 'Traceback' not in body
    assert 'Something went wrong' in body
