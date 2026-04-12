import importlib
import os
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope='session')
def app_module(tmp_path_factory):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    db_path = tmp_path_factory.mktemp('db') / 'test.db'
    os.environ['KANSI_ENV'] = 'test'
    os.environ['KANSI_DB_PATH'] = str(db_path)
    os.environ['KANSI_SECRET_KEY'] = 'test-secret-key'
    os.environ['KANSI_WEBHOOK_SECRET'] = 'test-webhook-secret'
    os.environ['KANSI_ALLOWED_FETCH_HOSTS'] = 'findahelpline.com'

    database = importlib.import_module('database')
    importlib.reload(database)
    app_module = importlib.import_module('app')
    importlib.reload(app_module)

    app = app_module.app
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=True, SHOW_RESET_LINKS=True)

    if 'boom' not in app.view_functions:
        def boom():
            raise RuntimeError('kaboom')
        app.add_url_rule('/__boom', 'boom', boom)

    return {
        'app_module': app_module,
        'database': database,
        'app': app,
    }


@pytest.fixture()
def app(app_module):
    return app_module['app']


@pytest.fixture()
def database(app_module):
    return app_module['database']


@pytest.fixture()
def client(app):
    return app.test_client()
