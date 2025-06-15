import pytest
import os
from werkzeug.security import generate_password_hash

# Flaskアプリケーションとデータベースインスタンスをapp.pyからインポート
# test_app.pyからもインポートするため、循環参照を避けるために
# アプリケーションのインスタンス化や設定はここで行う
from app import app as flask_app, db as sqlalchemy_db, User

@pytest.fixture(scope='session')
def app(request):
    """Session-wide test `Flask` application."""
    # テスト用の設定
    flask_app.config.update({
        "TESTING": True,
        # 環境変数からテスト用DBのURIを取得、なければインメモリSQLiteを使用
        "SQLALCHEMY_DATABASE_URI": os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:"),
        "SECRET_KEY": "test_secret_key_for_pytest",
        "WTF_CSRF_ENABLED": False,  # フォームテストを簡単にするためCSRFを無効化
        "LOGIN_DISABLED": False, # ログイン機能のテストのため無効化しない
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with flask_app.app_context():
        sqlalchemy_db.create_all() # 全てのテーブルを作成

    yield flask_app # テスト実行

    with flask_app.app_context():
        sqlalchemy_db.drop_all() # 全てのテーブルを削除

@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function')
def db(app):
    """Provides the database instance for a test, ensuring a clean state."""
    with app.app_context():
        # 各テスト前にはテーブルのデータをクリアする
        # (create_all/drop_allはセッションスコープで行うため、ここではデータのみ削除)
        for table in reversed(sqlalchemy_db.metadata.sorted_tables):
            sqlalchemy_db.session.execute(table.delete())
        sqlalchemy_db.session.commit()
        yield sqlalchemy_db
        sqlalchemy_db.session.remove() # セッションをクリーンアップ

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def logged_in_user(client, db):
    """
    テスト用のユーザーを作成し、ログイン状態にするフィクスチャ。
    作成したユーザーオブジェクトとテストクライアントを返す。
    """
    username = "testuser"
    password = "password123"

    user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()

    client.post('/login', data=dict(username=username, password=password), follow_redirects=True)
    return user, client
