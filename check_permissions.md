# Google Cloud Console での権限確認スクリプト

# 1. Google Cloud Console にアクセス
# https://console.cloud.google.com/

# 2. プロジェクト選択
# プロジェクト ID: apt-rope-217206

# 3. IAM と管理 > IAM ページにアクセス
# https://console.cloud.google.com/iam-admin/iam?project=apt-rope-217206

# 4. サービスアカウントを検索
# メールアドレス: streamlit-app@apt-rope-217206.iam.gserviceaccount.com
# または他のサービスアカウント

# 5. 現在の権限を確認
# クリックして詳細を表示

# 6. 必要に応じて権限を追加
# 「編集」ボタンをクリック
# 「ロールを追加」で以下を追加：
# - BigQuery データ閲覧者
# - BigQuery ユーザー  
# - Vertex AI ユーザー
# - サービス使用量コンシューマー
