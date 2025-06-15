import pytest
import os
from werkzeug.security import generate_password_hash

from sqlalchemy.orm import joinedload # joinedloadをインポート
# Flaskアプリケーションとデータベースインスタンスをapp.pyからインポート
# test_app.pyからもインポートするため、循環参照を避けるために
# アプリケーションのインスタンス化や設定はここで行う
from app import app as flask_app, db as sqlalchemy_db, User, Organization, Role

@pytest.fixture(scope='session')
def app(request):
    """Session-wide test `Flask` application."""
    # テスト用の設定
    flask_app.config.update({
        "TESTING": True,
        # CI環境のDATABASE_URLを優先し、なければインメモリSQLiteを使用
        "SQLALCHEMY_DATABASE_URI": os.environ.get("DATABASE_URL",
                                                "sqlite:///:memory:"),
        "SECRET_KEY": "test_secret_key_for_pytest",
        "WTF_CSRF_ENABLED": False,  # フォームテストを簡単にするためCSRFを無効化
        "LOGIN_DISABLED": False,  # ログイン機能のテストのため無効化しない
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with flask_app.app_context():
        sqlalchemy_db.create_all()  # 全てのテーブルを作成
        # テスト用の基本的なロールを作成
        if Role.query.count() == 0:
            admin_role = Role(name='admin')
            member_role = Role(name='member')
            sqlalchemy_db.session.add_all([admin_role, member_role])
            sqlalchemy_db.session.commit()
        # テスト用の組織を作成
        if Organization.query.count() == 0:
            test_org = Organization(name="DefaultTestOrg")
            sqlalchemy_db.session.add(test_org)
            sqlalchemy_db.session.commit()

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
        yield sqlalchemy_db # sqlalchemy_dbを返す
        sqlalchemy_db.session.remove() # セッションをクリーンアップ

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def logged_in_user(client, db, app): # appフィクスチャを引数に追加
    """
    テスト用のユーザーを作成し、ログイン状態にするフィクスチャ。
    作成したユーザーオブジェクトとテストクライアントを返す。
    """
    username = "testuser"
    password = "password123"
    org_name = "DefaultTestOrgForLoggedInUser" # logged_in_user専用の組織名にする
    user_instance_id = None # ユーザーIDを保存する変数を追加

    # logged_in_userフィクスチャ内で組織とロールを確実に取得または作成
    with app.app_context(): # appフィクスチャのコンテキストを使用
        organization = Organization.query.filter_by(name=org_name).first()
        if not organization:
            organization = Organization(name=org_name)
            db.session.add(organization)

        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role: # adminロールがなければ作成 (appフィクスチャでも作成しているが念のため)
            admin_role = Role(name='admin')
            db.session.add(admin_role)

        db.session.commit() # 組織とロールを先にコミット

        user = User(username=username,
                    password_hash=generate_password_hash(password),
                    organization_id=organization.id, # コミット後のorganization.idを使用
                    role_id=admin_role.id)
        db.session.add(user)
        db.session.commit() # ユーザーをコミット
        user_instance_id = user.id # コミット後にIDを保存

    client.post('/login', data=dict(username=username, password=password, organization_name=org_name), follow_redirects=True)
    # ユーザーオブジェクトをセッションから再取得して返す
    with app.app_context():
        # role属性も一緒に読み込むように変更 (SQLAlchemy 2.0 style)
        reloaded_user = db.session.get(User, user_instance_id, options=[joinedload(User.role)])
    return reloaded_user, client
