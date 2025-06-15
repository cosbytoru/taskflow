# app.py

import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import joinedload

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a_default_fallback_secret_key')

# --- データベース接続情報 ---
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASS = os.environ.get("POSTGRES_PASSWORD", "mysecretpassword")
DB_HOST = os.environ.get("DB_HOST", "db")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "postgres")

# CI環境など、外部からDATABASE_URLが指定された場合はそちらを優先
if os.environ.get('DATABASE_URL'):
    DATABASE_URI = os.environ.get('DATABASE_URL')
else:
    DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- Flask-SQLAlchemyとFlask-Migrateの設定 ---
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Flask-Loginの設定 ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- 定数 ---
# SQLAlchemyとMigrateの初期化をapp.config設定後に行う
db = SQLAlchemy(app)
migrate = Migrate(app, db)


TICKET_STATUSES = ['新規', '対応中', '保留', '解決済み', 'クローズ']
PRIORITIES = {1: "低", 2: "中", 3: "高"}

# --- データベースモデル ---

class Organization(db.Model):
    __tablename__ = 'organizations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    users = db.relationship('User', backref='organization', lazy='dynamic')
    tickets = db.relationship('Ticket', backref='organization', lazy='dynamic')

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False) #例: 'admin', 'member'
    users = db.relationship('User', backref='role', lazy=True)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)

    # ユーザーが一意である制約を organization_id と username の組み合わせにする
    __table_args__ = (db.UniqueConstraint('username', 'organization_id', name='_username_org_uc'),)
    
    # リレーションシップ
    requested_tickets = db.relationship('Ticket', foreign_keys='Ticket.requester_id', backref='requester', lazy=True)
    assigned_tickets = db.relationship('Ticket', foreign_keys='Ticket.assignee_id', backref='assignee', lazy=True)
    
    def is_admin(self):
        return self.role and self.role.name == 'admin'

class Ticket(db.Model):
    __tablename__ = 'tickets'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='新規')
    due_date = db.Column(db.Date, nullable=True)
    priority = db.Column(db.Integer, nullable=True, default=2)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # 担当者は未定の場合もある
    
    subtickets = db.relationship('SubTicket', backref='ticket', lazy=True, cascade="all, delete-orphan")

class SubTicket(db.Model):
    __tablename__ = 'subtickets'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)


# --- ユーザーローダーとヘルパー ---
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash("この操作を行うには管理者権限が必要です。", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# 初回起動時にロールを作成するためのコマンド
@app.cli.command("init-db")
def init_db_command():
    """データベースを初期化し、基本的なロールを作成します。"""
    db.create_all()
    # Check if roles exist
    if Role.query.count() == 0:
        print("Creating default roles...")
        roles = ['admin', 'member']
        for role_name in roles:
            db.session.add(Role(name=role_name))
        db.session.commit()
        print("Roles created.")
    else:
        print("Roles already exist.")
    print("Database initialized.")


# --- ルーティング ---
@app.route('/')
@login_required
def index():
    try:
        # ログインユーザーが所属する組織の全ユーザーを取得
        organization_users = User.query.filter_by(organization_id=current_user.organization_id).all()
        
        # ベースとなるクエリ (自組織のチケットのみ)
        # joinedloadを使用してN+1問題を回避
        query = Ticket.query.options(
            joinedload(Ticket.requester),
            joinedload(Ticket.assignee)
        ).filter_by(organization_id=current_user.organization_id)

        # 絞り込み (フィルタリング)
        filter_status = request.args.get('filter_status')
        if filter_status and filter_status != 'all':
            query = query.filter(Ticket.status == filter_status)

        # 検索機能
        search_term = request.args.get('search_term')
        if search_term:
            query = query.filter(Ticket.title.ilike(f'%{search_term}%'))

        # 並び替え機能 (デフォルトはID降順)
        sort_by = request.args.get('sort_by', 'id')
        sort_order = request.args.get('sort_order', 'desc')

        sort_logic = {
            'priority': Ticket.priority,
            'due_date': Ticket.due_date,
            'id': Ticket.id
        }
        
        order_column = sort_logic.get(sort_by, Ticket.id)
        if sort_order == 'desc':
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())

        tickets = query.all()
    except Exception as error:
        flash(f"チケットの読み込み中にエラー: {error}", "danger")
        tickets = []
        organization_users = []

    return render_template(
        'index.html', 
        tickets=tickets, 
        organization_users=organization_users,
        priorities=PRIORITIES,
        ticket_statuses=TICKET_STATUSES,
        current_sort_by=sort_by, 
        current_sort_order=sort_order, 
        current_filter_status=filter_status, 
        current_search_term=search_term
    )

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        organization_name = request.form.get('organization_name')

        if not all([username, password, organization_name]):
            flash("すべてのフィールドを入力してください。", "warning")
            return redirect(url_for('signup'))
        
        # 組織が既に存在するか確認
        org_exists = Organization.query.filter_by(name=organization_name).first()
        if org_exists:
            flash("その組織名は既に使用されています。別の名前を選択してください。", "warning")
            return redirect(url_for('signup'))
        
        try:
            # 1. 組織を作成
            new_organization = Organization(name=organization_name)
            db.session.add(new_organization)
            
            # 2. 役割を取得（なければ作成）
            admin_role = Role.query.filter_by(name='admin').first()
            if not admin_role:
                admin_role = Role(name='admin')
                db.session.add(admin_role)
            
            member_role = Role.query.filter_by(name='member').first()
            if not member_role:
                member_role = Role(name='member')
                db.session.add(member_role)
            
            db.session.flush() # IDを確定させる

            # 3. ユーザーを作成し、組織の最初のユーザーとして管理者ロールを割り当てる
            hashed_password = generate_password_hash(password)
            new_user = User(
                username=username, 
                password_hash=hashed_password,
                organization_id=new_organization.id,
                role_id=admin_role.id
            )
            db.session.add(new_user)
            db.session.commit()
            
            flash("組織とアカウントが作成されました。ログインしてください。", "success")
            return redirect(url_for('login'))
        except Exception as error:
            db.session.rollback()
            print(f"ユーザー登録中にエラー: {error}")
            flash("アカウント作成中にエラーが発生しました。", "danger")
            return redirect(url_for('signup'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        organization_name = request.form.get('organization_name')

        organization = Organization.query.filter_by(name=organization_name).first()
        if not organization:
            flash("組織が見つかりません。", "danger")
            return redirect(url_for('login'))
        
        user = User.query.filter_by(username=username, organization_id=organization.id).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("ログインしました。", "success")
            return redirect(url_for('index'))
        else:
            flash("ユーザー名、パスワード、または組織名が正しくありません。", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("ログアウトしました。", "info")
    return redirect(url_for('login'))


@app.route('/ticket/add', methods=['POST'])
@login_required
def add_ticket():
    title = request.form.get('title')
    due_date_str = request.form.get('due_date')
    priority = request.form.get('priority', type=int, default=2)
    assignee_id = request.form.get('assignee_id', type=int)

    if not title:
        flash("チケットのタイトルを入力してください。", "warning")
        return redirect(url_for('index'))

    try:
        new_ticket = Ticket(
            title=title, 
            requester_id=current_user.id,
            organization_id=current_user.organization_id,
            priority=priority,
            assignee_id=assignee_id # default=None で処理される想定
        )
        if due_date_str:
            new_ticket.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        
        db.session.add(new_ticket)
        db.session.commit()
        flash(f"チケット「{title}」を追加しました。", "success")
    except Exception as error:
        print("チケットの追加中にエラー:", error)
        db.session.rollback()
        flash("チケットの追加中にエラーが発生しました。", "danger")
    
    return redirect(url_for('index'))

@app.route('/ticket/<int:ticket_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_ticket(ticket_id):
    ticket_to_edit = Ticket.query.filter_by(id=ticket_id, organization_id=current_user.organization_id).first_or_404()
    
    if request.method == 'POST':
        # 権限チェック (管理者、担当者、依頼者のみ編集可能)
        if not (current_user.is_admin() or 
                ticket_to_edit.assignee_id == current_user.id or 
                ticket_to_edit.requester_id == current_user.id):
            flash("このチケットを編集する権限がありません。", "danger")
            return redirect(url_for('index'))
            
        new_title = request.form.get('title')
        new_due_date_str = request.form.get('due_date')
        new_priority = request.form.get('priority', type=int)
        new_status = request.form.get('status')
        new_assignee_id = request.form.get('assignee_id', type=int)

        if new_title:
            try:
                ticket_to_edit.title = new_title
                ticket_to_edit.priority = new_priority
                ticket_to_edit.status = new_status
                ticket_to_edit.assignee_id = new_assignee_id if new_assignee_id != 0 else None
                
                if new_due_date_str:
                    ticket_to_edit.due_date = datetime.strptime(new_due_date_str, '%Y-%m-%d').date()
                else:
                    ticket_to_edit.due_date = None
                
                db.session.commit()
                flash(f"チケットID {ticket_id} を更新しました。", "success")
            except Exception as error:
                print(f"チケットID {ticket_id} の更新中にエラー: {error}")
                db.session.rollback()
                flash(f"チケットID {ticket_id} の更新中にエラーが発生しました。", "danger")
        else:
            flash("チケットのタイトルは必須です。", "warning")
        return redirect(url_for('index'))

    organization_users = User.query.filter_by(organization_id=current_user.organization_id).all()
    return render_template('edit.html', ticket=ticket_to_edit, organization_users=organization_users, ticket_statuses=TICKET_STATUSES, priorities=PRIORITIES)

@app.route('/ticket/<int:ticket_id>/delete')
@login_required
@admin_required # 管理者のみ削除可能
def delete_ticket(ticket_id):
    try:
        ticket = Ticket.query.filter_by(id=ticket_id, organization_id=current_user.organization_id).first()
        if ticket:
            db.session.delete(ticket)
            db.session.commit()
            flash(f"チケットID {ticket_id} を削除しました。", "success")
        else:
            flash(f"チケットID {ticket_id} が見つからないか、権限がありません。", "warning")
    except Exception as error:
        print(f"チケット {ticket_id} の削除中にエラー: {error}")
        db.session.rollback()
        flash(f"チケットID {ticket_id} の削除中にエラーが発生しました。", "danger")
    return redirect(url_for('index'))

# サブチケット関連のルート（変更点はモデル名のみ）
@app.route('/subticket/add/<int:ticket_id>', methods=['POST'])
@login_required
def add_subticket(ticket_id):
    # 親チケットの存在確認と権限確認
    ticket = Ticket.query.filter_by(id=ticket_id, organization_id=current_user.organization_id).first_or_404()
    title = request.form.get('subticket_title')

    if not title:
        flash("サブチケットのタイトルを入力してください。", "warning")
        return redirect(url_for('index', _anchor=f'ticket-{ticket.id}'))

    try:
        new_subticket = SubTicket(title=title, ticket_id=ticket.id)
        db.session.add(new_subticket)
        db.session.commit()
        flash(f"サブチケット「{title}」をチケット「{ticket.title}」に追加しました。", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"サブチケットの追加中にエラー: {e}", "danger")
    return redirect(url_for('index', _anchor=f'ticket-{ticket.id}'))

@app.route('/subticket/toggle/<int:subticket_id>', methods=['POST'])
@login_required
def toggle_subticket(subticket_id):
    subticket = SubTicket.query.get_or_404(subticket_id)
    # 権限チェック：サブチケットが所属する親チケットが、ログインユーザーの組織のものか確認
    if subticket.ticket.organization_id != current_user.organization_id:
        abort(403) # Forbidden

    try:
        subticket.completed = not subticket.completed
        db.session.commit()
        flash(f"サブチケット「{subticket.title}」の状態を更新しました。", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"サブチケットの状態更新中にエラー: {e}", "danger")
    return redirect(url_for('index', _anchor=f'ticket-{subticket.ticket_id}'))


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')

        if not check_password_hash(current_user.password_hash, current_password):
            flash('現在のパスワードが正しくありません。', 'danger')
            return redirect(url_for('edit_profile'))
        if not new_password:
            flash('新しいパスワードを入力してください。', 'warning')
            return redirect(url_for('edit_profile'))
        if new_password != confirm_new_password:
            flash('新しいパスワードと確認用パスワードが一致しません。', 'danger')
            return redirect(url_for('edit_profile'))

        try:
            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash('パスワードが正常に更新されました。', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'パスワード更新中にエラーが発生しました: {e}', 'danger')

    return render_template('edit_profile.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
