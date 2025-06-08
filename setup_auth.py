"""
Google Cloud 認証設定ヘルパー
サービスアカウントキーの設定をガイドします
"""

import os
import json
from pathlib import Path

def check_current_auth():
    """現在の認証設定を確認"""
    print("🔍 現在の認証設定確認...")
    
    # .envファイルの確認
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        print("\n📄 .envファイルの内容:")
        for line in content.split('\n'):
            if line.strip() and not line.startswith('#'):
                key = line.split('=')[0] if '=' in line else line
                print(f"  ✅ {key}")
    
    # 環境変数の確認
    print("\n🔧 環境変数の確認:")
    auth_vars = [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GCP_SERVICE_ACCOUNT_EMAIL",
        "GCP_PRIVATE_KEY",
        "ENABLE_GCP_INITIALIZATION"
    ]
    
    for var in auth_vars:
        value = os.getenv(var)
        if value:
            if var == "GCP_PRIVATE_KEY":
                print(f"  ✅ {var}: ***設定済み***")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: 未設定")

def setup_service_account():
    """サービスアカウント設定をガイド"""
    print("\n🔑 サービスアカウント設定ガイド")
    print("="*50)
    
    print("\n1. Google Cloud Consoleでサービスアカウントキーを作成:")
    print("   - https://console.cloud.google.com/iam-admin/serviceaccounts")
    print("   - プロジェクト: apt-rope-217206")
    print("   - 新しいサービスアカウントを作成")
    print("   - 必要な権限:")
    print("     * BigQuery データビューアー")
    print("     * BigQuery ユーザー") 
    print("     * Vertex AI ユーザー")
    
    print("\n2. キーファイルをダウンロード:")
    print("   - JSON形式でキーを作成・ダウンロード")
    print("   - ファイル名例: service-account-key.json")
    
    print("\n3. キーファイルを安全な場所に配置:")
    suggested_path = Path.home() / "gcp" / "service-account-key.json"
    print(f"   - 推奨パス: {suggested_path}")
    
    print("\n4. .envファイルにパスを設定:")
    print(f"   GOOGLE_APPLICATION_CREDENTIALS={suggested_path}")
    print("   ENABLE_GCP_INITIALIZATION=true")
    
    # ディレクトリ作成を提案
    gcp_dir = Path.home() / "gcp"
    if not gcp_dir.exists():
        create = input(f"\n📁 {gcp_dir} ディレクトリを作成しますか？ (y/n): ")
        if create.lower() == 'y':
            gcp_dir.mkdir(exist_ok=True)
            print(f"✅ ディレクトリ作成完了: {gcp_dir}")

def test_connection():
    """接続テスト"""
    print("\n🧪 接続テスト")
    print("="*30)
    
    try:
        from gcp_auth import get_gcp_status, get_bigquery_client
        
        # ステータス確認
        status = get_gcp_status()
        print("\n📊 GCPステータス:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        # BigQuery接続テスト
        bq_client = get_bigquery_client()
        if bq_client:
            print("\n✅ BigQuery接続: 成功")
            
            # 簡単なクエリでテスト
            table_id = os.getenv("BIGQUERY_TABLE", "apt-rope-217206.researcher_data.rd_250524")
            query = f"SELECT COUNT(*) as total FROM `{table_id}` LIMIT 1"
            
            try:
                query_job = bq_client.query(query)
                results = list(query_job.result())
                total = results[0].total if results else 0
                print(f"  データ件数: {total:,}件")
            except Exception as e:
                print(f"  ❌ クエリエラー: {e}")
        else:
            print("\n❌ BigQuery接続: 失敗")
            
    except Exception as e:
        print(f"\n❌ 接続テストエラー: {e}")

def main():
    """メイン関数"""
    print("🚀 Google Cloud 認証設定ヘルパー")
    print("="*40)
    
    while True:
        print("\n📋 メニュー:")
        print("1. 現在の認証設定を確認")
        print("2. サービスアカウント設定ガイド")
        print("3. 接続テスト")
        print("4. 終了")
        
        choice = input("\n選択してください (1-4): ").strip()
        
        if choice == "1":
            check_current_auth()
        elif choice == "2":
            setup_service_account()
        elif choice == "3":
            test_connection()
        elif choice == "4":
            print("\n👋 設定完了後、サーバーを再起動してください")
            break
        else:
            print("❌ 無効な選択です")

if __name__ == "__main__":
    main()
