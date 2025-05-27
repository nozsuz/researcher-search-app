"""
Google Cloud Platform 認証ユーティリティ
個別の環境変数から認証情報を構築
"""

import os
import json
import tempfile
from google.cloud import bigquery
from google.cloud import aiplatform
from google.oauth2 import service_account
import logging

logger = logging.getLogger(__name__)

def create_credentials_from_env():
    """
    環境変数から Google Cloud 認証情報を作成
    """
    try:
        # 必要な環境変数の確認
        required_env_vars = [
            'GOOGLE_PROJECT_ID',
            'GOOGLE_PRIVATE_KEY_ID', 
            'GOOGLE_PRIVATE_KEY',
            'GOOGLE_CLIENT_EMAIL',
            'GOOGLE_CLIENT_ID'
        ]
        
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"必要な環境変数が設定されていません: {missing_vars}")
        
        # 認証情報辞書を構築
        credentials_dict = {
            "type": "service_account",
            "project_id": os.getenv('GOOGLE_PROJECT_ID'),
            "private_key_id": os.getenv('GOOGLE_PRIVATE_KEY_ID'),
            "private_key": os.getenv('GOOGLE_PRIVATE_KEY').replace('\\n', '\n'),
            "client_email": os.getenv('GOOGLE_CLIENT_EMAIL'),
            "client_id": os.getenv('GOOGLE_CLIENT_ID'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('GOOGLE_CLIENT_EMAIL')}",
            "universe_domain": "googleapis.com"
        }
        
        # 認証情報オブジェクトを作成
        credentials = service_account.Credentials.from_service_account_info(credentials_dict)
        
        logger.info("✅ 環境変数から認証情報を正常に作成しました")
        return credentials
        
    except Exception as e:
        logger.error(f"❌ 認証情報の作成に失敗: {e}")
        raise

def get_bigquery_client():
    """
    BigQuery クライアントを取得
    """
    try:
        credentials = create_credentials_from_env()
        project_id = os.getenv('PROJECT_ID', os.getenv('GOOGLE_PROJECT_ID'))
        
        client = bigquery.Client(credentials=credentials, project=project_id)
        logger.info("✅ BigQuery クライアントを作成しました")
        return client
        
    except Exception as e:
        logger.error(f"❌ BigQuery クライアントの作成に失敗: {e}")
        raise

def initialize_vertex_ai():
    """
    Vertex AI を初期化
    """
    try:
        credentials = create_credentials_from_env()
        project_id = os.getenv('PROJECT_ID', os.getenv('GOOGLE_PROJECT_ID'))
        location = os.getenv('LOCATION', 'us-central1')
        
        aiplatform.init(
            project=project_id,
            location=location,
            credentials=credentials
        )
        
        logger.info("✅ Vertex AI を初期化しました")
        return True
        
    except Exception as e:
        logger.error(f"❌ Vertex AI の初期化に失敗: {e}")
        raise

def test_authentication():
    """
    認証のテスト
    """
    test_results = {
        "credentials_creation": False,
        "bigquery_connection": False,
        "vertex_ai_initialization": False,
        "errors": []
    }
    
    try:
        # 1. 認証情報作成テスト
        credentials = create_credentials_from_env()
        test_results["credentials_creation"] = True
        logger.info("✅ 認証情報作成テスト成功")
        
    except Exception as e:
        test_results["errors"].append(f"認証情報作成エラー: {e}")
        logger.error(f"❌ 認証情報作成テスト失敗: {e}")
        return test_results
    
    try:
        # 2. BigQuery接続テスト
        bq_client = get_bigquery_client()
        
        # 簡単なクエリでテスト
        query = "SELECT 1 as test_value"
        query_job = bq_client.query(query)
        results = list(query_job.result())
        
        if results and results[0].test_value == 1:
            test_results["bigquery_connection"] = True
            logger.info("✅ BigQuery接続テスト成功")
        
    except Exception as e:
        test_results["errors"].append(f"BigQuery接続エラー: {e}")
        logger.error(f"❌ BigQuery接続テスト失敗: {e}")
    
    try:
        # 3. Vertex AI初期化テスト
        initialize_vertex_ai()
        test_results["vertex_ai_initialization"] = True
        logger.info("✅ Vertex AI初期化テスト成功")
        
    except Exception as e:
        test_results["errors"].append(f"Vertex AI初期化エラー: {e}")
        logger.error(f"❌ Vertex AI初期化テスト失敗: {e}")
    
    return test_results

if __name__ == "__main__":
    # 直接実行時のテスト
    print("🔧 Google Cloud Platform 認証テスト開始...")
    results = test_authentication()
    
    print("\n📊 テスト結果:")
    print(f"認証情報作成: {'✅' if results['credentials_creation'] else '❌'}")
    print(f"BigQuery接続: {'✅' if results['bigquery_connection'] else '❌'}")
    print(f"Vertex AI初期化: {'✅' if results['vertex_ai_initialization'] else '❌'}")
    
    if results['errors']:
        print("\n❌ エラー詳細:")
        for error in results['errors']:
            print(f"  - {error}")
    else:
        print("\n🎉 すべてのテストが成功しました！")
