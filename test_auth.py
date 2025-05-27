"""
認証テスト用スクリプト
Railway デプロイ前のローカルテスト用
"""

import os
import sys
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_environment_variables():
    """環境変数の確認"""
    print("🔍 環境変数確認...")
    
    required_vars = [
        'PROJECT_ID',
        'LOCATION', 
        'BIGQUERY_TABLE',
        'GOOGLE_PROJECT_ID',
        'GOOGLE_PRIVATE_KEY_ID',
        'GOOGLE_PRIVATE_KEY',
        'GOOGLE_CLIENT_EMAIL',
        'GOOGLE_CLIENT_ID'
    ]
    
    missing_vars = []
    set_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            set_vars.append(var)
            # 機密情報は一部のみ表示
            if 'PRIVATE_KEY' in var:
                display_value = f"{value[:30]}..." if len(value) > 30 else value
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            missing_vars.append(var)
            print(f"  ❌ {var}: 未設定")
    
    if missing_vars:
        print(f"\n⚠️ 不足している環境変数: {missing_vars}")
        return False
    else:
        print(f"\n🎉 すべての環境変数が設定されています ({len(set_vars)}/{len(required_vars)})")
        return True

def test_gcp_authentication():
    """GCP認証テスト"""
    print("\n🔧 GCP認証テスト開始...")
    
    try:
        from gcp_auth import test_authentication
        results = test_authentication()
        
        print("\n📊 認証テスト結果:")
        print(f"  認証情報作成: {'✅' if results['credentials_creation'] else '❌'}")
        print(f"  BigQuery接続: {'✅' if results['bigquery_connection'] else '❌'}")
        print(f"  Vertex AI初期化: {'✅' if results['vertex_ai_initialization'] else '❌'}")
        
        if results['errors']:
            print("\n❌ エラー詳細:")
            for error in results['errors']:
                print(f"    {error}")
            return False
        else:
            print("\n🎉 すべての認証テストが成功しました！")
            return True
            
    except ImportError as e:
        print(f"❌ gcp_auth モジュールのインポートエラー: {e}")
        return False
    except Exception as e:
        print(f"❌ 認証テスト中にエラー: {e}")
        return False

def main():
    """メインテスト実行"""
    print("=" * 60)
    print("🧪 研究者検索アプリ - 認証テスト")
    print("=" * 60)
    
    # 1. 環境変数テスト
    env_ok = test_environment_variables()
    
    if not env_ok:
        print("\n❌ 環境変数が不足しているため、認証テストをスキップします")
        sys.exit(1)
    
    # 2. GCP認証テスト
    auth_ok = test_gcp_authentication()
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📋 テスト結果サマリー")
    print("=" * 60)
    print(f"環境変数設定: {'✅ OK' if env_ok else '❌ NG'}")
    print(f"GCP認証: {'✅ OK' if auth_ok else '❌ NG'}")
    
    if env_ok and auth_ok:
        print("\n🎉 すべてのテストが成功しました！")
        print("Railway にデプロイする準備ができました。")
        sys.exit(0)
    else:
        print("\n❌ テストに失敗しました。設定を確認してください。")
        sys.exit(1)

if __name__ == "__main__":
    main()
