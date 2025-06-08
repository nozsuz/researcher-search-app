"""
Railway環境変数確認・設定ガイド
デプロイされたRailway環境で必要な環境変数をチェック
"""

def railway_env_checklist():
    """Railway環境変数チェックリスト"""
    print("🚂 Railway環境変数設定チェックリスト")
    print("="*50)
    
    required_vars = {
        "基本設定": {
            "PROJECT_ID": "apt-rope-217206",
            "LOCATION": "us-central1", 
            "BIGQUERY_TABLE": "apt-rope-217206.researcher_data.rd_250524",
            "ENABLE_GCP_INITIALIZATION": "true"
        },
        "GCP認証（個別変数方式）": {
            "GCP_SERVICE_ACCOUNT_EMAIL": "your-service-account@apt-rope-217206.iam.gserviceaccount.com",
            "GCP_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
            "GCP_PRIVATE_KEY_ID": "your-private-key-id",
            "GCP_CLIENT_ID": "your-client-id",
            "GCP_CLIENT_X509_CERT_URL": "https://www.googleapis.com/robot/v1/metadata/x509/..."
        },
        "代替認証（JSON方式）": {
            "GOOGLE_APPLICATION_CREDENTIALS_JSON": "{'type':'service_account',...}",
            "GOOGLE_APPLICATION_CREDENTIALS_BASE64": "base64-encoded-json"
        }
    }
    
    print("\n📋 設定が必要な環境変数:")
    for category, vars_dict in required_vars.items():
        print(f"\n【{category}】")
        for var_name, example_value in vars_dict.items():
            if "PRIVATE_KEY" in var_name and len(example_value) > 50:
                display_value = example_value[:30] + "..."
            elif len(example_value) > 50:
                display_value = example_value[:47] + "..."
            else:
                display_value = example_value
            print(f"  {var_name} = {display_value}")
    
    print("\n🔧 Railway環境変数設定手順:")
    print("1. Railway Dashboard にログイン")
    print("2. プロジェクト 'researcher-search-app' を選択")
    print("3. 'Variables' タブをクリック")
    print("4. 上記の環境変数を設定")
    print("5. デプロイメントを再実行")
    
    print("\n⚠️  重要な注意事項:")
    print("- GCP_PRIVATE_KEY は改行文字を \\n で置換してください")
    print("- JSON文字列は適切にエスケープしてください")
    print("- 最低限必要: 基本設定 + いずれか一つの認証方式")

def check_deployment_issues():
    """デプロイメント問題のチェックリスト"""
    print("\n🔍 よくあるデプロイメント問題")
    print("="*40)
    
    issues = [
        {
            "問題": "認証情報が消えた",
            "原因": "環境変数の設定ミス、または設定後にリセットされた",
            "解決策": "Railway Dashboardで環境変数を再確認・再設定"
        },
        {
            "問題": "古いコードが動いている", 
            "原因": "railway.jsonが古い設定を指している",
            "解決策": "railway.jsonを修正してmain.pyを指すよう変更"
        },
        {
            "問題": "検索がモックになる",
            "原因": "ENABLE_GCP_INITIALIZATION=true が未設定",
            "解決策": "環境変数でGCP初期化を有効化"
        },
        {
            "問題": "Vertex AIエラー",
            "原因": "サービスアカウントの権限不足",
            "解決策": "Vertex AI User 権限を追加"
        }
    ]
    
    for i, issue in enumerate(issues, 1):
        print(f"\n{i}. {issue['問題']}")
        print(f"   原因: {issue['原因']}")
        print(f"   解決策: {issue['解決策']}")

def railway_commands():
    """便利なRailwayコマンド"""
    print("\n💻 便利なRailwayコマンド")
    print("="*30)
    
    commands = [
        "railway login",
        "railway list",
        "railway variables",
        "railway logs", 
        "railway deploy",
        "railway open"
    ]
    
    for cmd in commands:
        print(f"  {cmd}")
    
    print("\n📖 Railway CLI インストール:")
    print("  npm install -g @railway/cli")
    print("  または: https://railway.app/cli")

def main():
    """メイン関数"""
    print("🚂 Railway環境設定診断ツール")
    print("="*35)
    
    railway_env_checklist()
    check_deployment_issues() 
    railway_commands()
    
    print("\n🎯 次のステップ:")
    print("1. Railway Dashboardで環境変数を確認")
    print("2. 認証情報を再設定")
    print("3. railway.jsonの修正をコミット・プッシュ") 
    print("4. デプロイメントの確認")
    print("5. /health エンドポイントで動作確認")

if __name__ == "__main__":
    main()
