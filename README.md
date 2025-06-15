# TaskFlow-app

TaskFlow-app は、Flask と Docker で構築された組織・チーム向けのチケット管理アプリケーションです。ユーザー認証、組織管理、チケットのCRUD操作、役割ベースのアクセス制御、データベースマイグレーションなどの機能を備えています。

## ✨ 主な機能
組織・チーム管理:
  - 組織の作成とユーザーの所属
  - (将来的にチーム機能拡張予定)
ユーザー認証:
  - 安全なサインアップ、ログイン、ログアウト機能
  - ユーザープロフィールの編集（パスワード変更）
役割ベースアクセス制御 (RBAC):
  - 管理者、メンバーなどの役割に基づいた操作権限の制御
チケット管理 (CRUD):
  - チケットの追加、一覧表示、編集、削除
  - ステータス管理（新規、対応中、解決済みなど）
  - 優先度、期限日の設定
  - 担当者の割り当て
サブチケット管理:
  - チケットに紐づくサブチケットの作成と完了状態管理
データベースマイグレーション: Flask-Migrateによるスキーマ変更管理
## 🛠️ 技術スタック
バックエンド: Flask

フロントエンド: HTML, Tailwind CSS (基本的なFlaskテンプレート)

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

以下のコマンドを実行してデータベースのマイグレーション（テーブル作成や更新）と、基本的なロールの初期作成を行います。初回起動時やモデル変更後に実行してください。
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
