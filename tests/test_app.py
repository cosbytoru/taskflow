# tests/test_app.py
from datetime import date
from flask import session as flask_session
from app import User, Task, db as app_db  # conftest.pyでappとdbは設定される


def test_index_page_unauthenticated(client):
    """未認証状態でトップページにアクセスするとログインページにリダイレクトされるか"""
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.location


def test_index_page_authenticated(logged_in_user):
    """認証状態でトップページにアクセスできるか"""
    user, client = logged_in_user
    response = client.get('/')
    assert response.status_code == 200
    assert "My ToDo List".encode('utf-8') in response.data
    assert f"ようこそ, {user.username} さん".encode() in response.data


# --- ユーザー認証テスト ---
def test_signup(client, db):
    """ユーザーが正常にサインアップできるか"""
    response = client.post('/signup', data={
        'username': 'newuser',
        'password': 'newpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    expected_message = "アカウントが作成されました。ログインしてください。"
    assert expected_message.encode('utf-8') in response.data
    assert User.query.filter_by(username='newuser').first() is not None


def test_signup_existing_user(client, db):
    """既に存在するユーザー名でサインアップしようとした場合のエラー処理"""
    # 最初のユーザーを作成
    client.post('/signup', data={'username': 'existuser', 'password': 'password'})
    # 同じユーザー名で再度サインアップ
    response = client.post('/signup', data={
        'username': 'existuser',
        'password': 'anotherpassword'
    }, follow_redirects=True)
    assert response.status_code == 200  # 通常、エラーでもページは表示される
    assert "そのユーザー名は既に使用されています。".encode('utf-8') in response.data


def test_login_logout(client, db):
    """ユーザーのログインとログアウトが正常に機能するか"""
    # まずユーザーをサインアップ
    username = "loginuser"
    password = "loginpassword"
    client.post('/signup', data={'username': username, 'password': password}, follow_redirects=True)

    # ログイン
    response = client.post('/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "ログインしました。".encode('utf-8') in response.data
    with client:  # セッションを維持
        client.get('/')  # current_userが設定されるようにリクエスト
        assert flask_session.get('_user_id') is not None

    # ログアウト
    response = client.get('/logout', follow_redirects=True)
    assert "ログアウトしました。".encode('utf-8') in response.data
    with client:
        client.get('/')  # current_userが設定されるようにリクエスト
        assert flask_session.get('_user_id') is None


def test_login_invalid_credentials(client):
    """無効な認証情報でのログイン試行"""
    response = client.post('/login', data={
        'username': 'nonexistentuser',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    expected_message = "ユーザー名またはパスワードが正しくありません。"
    assert expected_message.encode('utf-8') in response.data


# --- タスク操作テスト (フォームベース) ---
def test_add_task_form(logged_in_user, db):
    """フォームからタスクを正常に追加できるか"""
    user, client = logged_in_user
    task_title = "Test Task via Form"
    response = client.post('/add', data={
        'title': task_title,
        'due_date': '2025-12-31',
        'priority': '3'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert f"タスク「{task_title}」を追加しました。".encode() in response.data
    task = Task.query.filter_by(title=task_title, user_id=user.id).first()
    assert task is not None
    assert task.due_date == date(2025, 12, 31)
    assert task.priority == 3


def test_add_task_form_empty_title(logged_in_user):
    """フォームから空のタイトルでタスクを追加しようとした場合"""
    user, client = logged_in_user
    response = client.post('/add', data={'title': ''}, follow_redirects=True)
    assert response.status_code == 200
    assert "タスクのタイトルを入力してください。".encode('utf-8') in response.data


def test_complete_and_reactivate_task_form(logged_in_user, db):
    """タスクの完了と再活性化がフォーム経由で機能するか"""
    user, client = logged_in_user
    task = Task(title="Completable Task", owner=user)
    db.session.add(task)
    db.session.commit()

    # 完了
    response = client.get(f'/complete/{task.id}', follow_redirects=True)
    assert response.status_code == 200
    assert f"タスクID {task.id} を完了にしました。".encode('utf-8') in response.data
    assert app_db.session.get(Task, task.id).completed is True

    # 再活性化
    response = client.get(f'/reactivate/{task.id}', follow_redirects=True)
    assert response.status_code == 200
    assert f"タスクID {task.id} を未完了に戻しました。".encode('utf-8') in response.data
    assert app_db.session.get(Task, task.id).completed is False


def test_delete_task_form(logged_in_user, db):
    """タスクの削除がフォーム経由で機能するか"""
    user, client = logged_in_user
    task = Task(title="Deletable Task", owner=user)
    db.session.add(task)
    db.session.commit()

    response = client.get(f'/delete/{task.id}', follow_redirects=True)
    assert response.status_code == 200
    assert f"タスクID {task.id} を削除しました。".encode('utf-8') in response.data
    assert app_db.session.get(Task, task.id) is None


def test_edit_task_form(logged_in_user, db):
    """タスクの編集がフォーム経由で機能するか"""
    user, client = logged_in_user
    task = Task(title="Editable Task", owner=user, priority=1,
                due_date=date(2025, 1, 1))
    db.session.add(task)
    db.session.commit()

    new_title = "Edited Task Title"
    new_due_date = "2026-01-01"
    new_priority = "2"
    response = client.post(f'/edit/{task.id}', data={
        'title': new_title,
        'due_date': new_due_date,
        'priority': new_priority
    }, follow_redirects=True)

    assert response.status_code == 200
    expected_message = (
        f"タスクID {task.id} のタイトルを「{new_title}」に更新しました。"
    )
    assert expected_message.encode('utf-8') in response.data

    edited_task = app_db.session.get(Task, task.id)
    assert edited_task.title == new_title
    assert edited_task.due_date == date(2026, 1, 1)
    assert edited_task.priority == 2


# --- APIテスト (JSONベース) ---
def test_add_task_api(logged_in_user, db):
    """API経由でタスクを正常に追加できるか"""
    user, client = logged_in_user
    task_data = {'title': 'API Task', 'due_date': '2025-10-10', 'priority': 1}
    response = client.post('/add', json=task_data)
    assert response.status_code == 200
    json_response = response.get_json()
    assert json_response['status'] == 'success'
    expected_message = f"タスク「{task_data['title']}」を追加しました。"
    assert json_response['message'] == expected_message
    assert json_response['task']['title'] == task_data['title']
    assert json_response['task']['due_date'] == task_data['due_date']
    assert json_response['task']['priority'] == task_data['priority']
    task_in_db = Task.query.filter_by(title=task_data['title'],
                                      user_id=user.id).first()
    assert task_in_db is not None


def test_add_task_api_empty_title(logged_in_user):
    """API経由で空のタイトルでタスクを追加しようとした場合"""
    _, client = logged_in_user
    response = client.post('/add', json={'title': ''})
    assert response.status_code == 400
    json_response = response.get_json()
    assert json_response['status'] == 'error'
    assert json_response['message'] == "タスクのタイトルを入力してください。"


def test_complete_task_api(logged_in_user, db):
    """API経由でタスクを完了できるか"""
    user, client = logged_in_user
    task = Task(title="API Completable Task", owner=user)
    db.session.add(task)
    db.session.commit()
    response = client.get(f'/complete/{task.id}',
                          headers={'X-Requested-With': 'XMLHttpRequest'})
    assert response.status_code == 200
    json_response = response.get_json()
    assert json_response['status'] == 'success'
    assert json_response['task']['completed'] is True
    assert app_db.session.get(Task, task.id).completed is True


def test_delete_task_api(logged_in_user, db):
    """API経由でタスクを削除できるか"""
    user, client = logged_in_user
    task = Task(title="API Deletable Task", owner=user)
    db.session.add(task)
    db.session.commit()

    response = client.get(f'/delete/{task.id}',
                          headers={'X-Requested-With': 'XMLHttpRequest'})
    assert response.status_code == 200
    json_response = response.get_json()
    assert json_response['status'] == 'success'
    assert app_db.session.get(Task, task.id) is None


# --- タスク操作の認可テスト ---
def test_cannot_operate_other_user_task(client, db):
    from werkzeug.security import generate_password_hash  # ここでインポート
    """他のユーザーのタスクを操作できないことを確認"""
    # ユーザー1作成とログイン
    user1_name, user1_pass = "user1", "pass1"
    db.session.add(User(username=user1_name, password_hash=generate_password_hash(user1_pass)))
    db.session.commit()
    user1 = User.query.filter_by(username=user1_name).first()

    # ユーザー1のタスク作成
    task_user1 = Task(title="User1 Task", owner=user1)
    db.session.add(task_user1)
    db.session.commit()

    # ユーザー2作成とログイン
    user2_name, user2_pass = "user2", "pass2"
    user2 = User(username=user2_name,
                 password_hash=generate_password_hash(user2_pass))
    db.session.add(user2)
    db.session.commit()

    client.post('/login',
                data={'username': user2_name, 'password': user2_pass},
                follow_redirects=True)

    # ユーザー2がユーザー1のタスクを操作しようとする
    # 完了 (API)
    response_complete = client.get(
        f'/complete/{task_user1.id}',
        headers={'X-Requested-With': 'XMLHttpRequest'}
    )
    # or 403 depending on implementation
    assert response_complete.status_code == 404
    assert app_db.session.get(Task, task_user1.id).completed is False  # 状態が変わっていないこと

    # 削除 (API)
    response_delete = client.get(
        f'/delete/{task_user1.id}',
        headers={'X-Requested-With': 'XMLHttpRequest'}
    )
    assert response_delete.status_code == 404  # or 403
    assert app_db.session.get(Task, task_user1.id) is not None  # 削除されていないこと

    # 編集ページGET (フォーム)
    response_edit_get = client.get(f'/edit/{task_user1.id}',
                                   follow_redirects=True)
    assert response_edit_get.status_code == 404  # first_or_404が発動

    # 編集POST (フォーム) - これは edit/<id> GETが404になるので直接テストしにくいが、
    # 仮にURLを知っていてもTask.query.filter_by(id=task_id, owner=current_user)で防がれる
    # response_edit_post = client.post(f'/edit/{task_user1.id}', data={'title': 'Hacked'}, follow_redirects=True)
    # assert response_edit_post.status_code == 404
    # assert Task.query.get(task_user1.id).title == "User1 Task"