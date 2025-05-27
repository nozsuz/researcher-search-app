# Railway 環境変数設定ガイド（個別設定版）

## 基本設定
PROJECT_ID=apt-rope-217206
LOCATION=us-central1
BIGQUERY_TABLE=apt-rope-217206.researcher_data.rd_250524

## GCP初期化有効化
ENABLE_GCP_INITIALIZATION=true

## サービスアカウント認証情報（個別設定）
# Google Cloud Console でダウンロードしたJSONキーから以下の値を個別に設定

GCP_SERVICE_ACCOUNT_EMAIL=railway-researcher-search@apt-rope-217206.iam.gserviceaccount.com
GCP_PRIVATE_KEY_ID=【private_key_idの値】
GCP_PRIVATE_KEY=【private_keyの値（-----BEGIN PRIVATE KEY-----から-----END PRIVATE KEY-----まで全体）】
GCP_CLIENT_ID=【client_idの値】
GCP_CLIENT_X509_CERT_URL=【client_x509_cert_urlの値】

## 重要な注意事項
1. GCP_PRIVATE_KEY は改行文字を含む長い文字列です
2. Railwayで設定する際は、改行文字（\n）がエスケープされて \\n になる場合があります
3. コードで自動的に \\n を \n に置換する処理を追加済みです

## 設定後の確認方法
1. デプロイ後、以下のエンドポイントで設定状況を確認:
   https://【Railway URL】/test/env

2. GCP接続テスト:
   https://【Railway URL】/test/gcp

3. ヘルスチェック:
   https://【Railway URL】/health

## サービスアカウント作成手順
1. Google Cloud Console → IAM と管理 → サービスアカウント
2. 「サービスアカウントを作成」
3. 名前: railway-researcher-search
4. 役割を追加:
   - BigQuery データ閲覧者
   - BigQuery ジョブユーザー
   - Vertex AI ユーザー
   - AI Platform ユーザー
5. 「キー」→「キーを追加」→「JSON」でキーをダウンロード
6. ダウンロードしたJSONから個別の値を抽出してRailwayに設定
