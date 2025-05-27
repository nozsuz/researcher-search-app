# GCP認証用の環境変数設定
# Railway管理画面のVariablesタブで以下を設定

# 必須環境変数
PROJECT_ID=apt-rope-217206
LOCATION=us-central1
BIGQUERY_TABLE=apt-rope-217206.researcher_data.rd_250524

# GCP認証（サービスアカウントキー）
# 注意: 実際のキーファイルは安全に管理してください
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# または、Railway でのサービスアカウントキー設定
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type": "service_account", "project_id": "..."}
