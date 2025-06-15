# TaskFlow-app

TaskFlow-app は、Flask と Docker で構築されたシンプルなToDoアプリケーションです。ユーザー認証、タスクのCRUD操作、データベースマイグレーションなどの基本的な機能を備えています。

## ✨ 主な機能
ユーザー認証:
  - 安全なサインアップ、ログイン、ログアウト機能
  - ユーザープロフィールの編集（パスワード変更）
タスク管理 (CRUD): タスクの追加、一覧表示、編集、削除

タスク状態管理: タスクの完了・未完了の切り替え

データベースマイグレーション: Flask-Migrateによるスキーマ変更管理
## 🛠️ 技術スタック
バックエンド: Flask

フロントエンド: HTML, Tailwind CSS

データベース: PostgreSQL

コンテナ化: Docker, Docker Compose

CI: GitHub Actions

Pythonライブラリ: Flask-SQLAlchemy, Flask-Login, Flask-Migrateなど（詳細はrequirements.txtを参照）

## 🚀 はじめに (Getting Started)

### 前提条件

- Docker Engine
- Docker Compose (Docker Desktop for Mac/Windows には含まれています)

1. リポジトリをクローン
```bash
git clone https://github.com/cosbytoru/TaskFlow-app.git
cd taskflow-app
```

2. コンテナのビルドと起動

以下のコマンドで、Dockerコンテナをビルドし、バックグラウンドで起動します。
```bash
docker compose up --build -d
```
初回起動時にはイメージのビルドに数分かかることがあります。

3. データベースのマイグレーション

以下のコマンドを実行してデータベースのマイグレーション（テーブル作成や更新）を行います。初回起動時やモデル変更後に実行してください。
```bash
docker compose exec web flask db upgrade
```

4. アプリケーションへのアクセス

ブラウザで `http://localhost:5001` にアクセスしてください。

## 🔧 開発者向け情報 (For Developers)

### データベースのスキーマ更新

`app.py` 内のモデル（`User`クラスや`Task`クラス）に変更を加えた場合は、以下の手順でデータベースのスキーマを更新します。

1. **マイグレーションファイルの自動生成:** モデルの変更点を検出し、更新用のマイグレーションファイルを生成します。
   ```bash
   docker compose exec web flask db migrate -m "変更内容の要約（例: Add due_date to Task）"
   ```
2. **データベースへの適用:** 生成されたファイルを元に、データベースのテーブル構造を更新します。
   ```bash
   docker compose exec web flask db upgrade
   ```

   
### 静的解析 (Linting)

`flake8` を使用してコードの静的解析を実行できます。
```bash
docker compose run --rm web flake8 .
```

### テスト実行 (Testing)
`pytest` を使用してテストを実行できます。
```bash
docker compose run --rm web pytest
```
# taskflow
