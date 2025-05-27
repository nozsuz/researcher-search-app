"""
GCP認証とクライアント初期化の改善版
環境変数から認証情報を読み込み、クライアントを初期化
"""

import os
import json
import base64
import logging
from google.cloud import bigquery
from google.cloud import aiplatform
import google.auth
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

class GCPClientManager:
    """GCP クライアント管理クラス"""
    
    def __init__(self):
        self.project_id = os.getenv("PROJECT_ID", "apt-rope-217206")
        self.location = os.getenv("LOCATION", "us-central1")
        self.table_id = os.getenv("BIGQUERY_TABLE", "apt-rope-217206.researcher_data.rd_250524")
        
        # クライアント
        self.credentials = None
        self.bq_client = None
        self.ai_platform_initialized = False
        self.initialized = False
        
    def _get_credentials(self):
        """認証情報を取得（個別環境変数対応）"""
        try:
            # 方法1: 個別の環境変数からサービスアカウント情報を構築
            service_account_email = os.getenv("GCP_SERVICE_ACCOUNT_EMAIL")
            private_key = os.getenv("GCP_PRIVATE_KEY")
            private_key_id = os.getenv("GCP_PRIVATE_KEY_ID")
            client_id = os.getenv("GCP_CLIENT_ID")
            client_x509_cert_url = os.getenv("GCP_CLIENT_X509_CERT_URL")
            
            if service_account_email and private_key:
                logger.info("🔑 個別環境変数からサービスアカウント情報を構築")
                
                # private_keyの改行文字を置換
                if "\\n" in private_key:
                    private_key = private_key.replace("\\n", "\n")
                
                credentials_info = {
                    "type": "service_account",
                    "project_id": self.project_id,
                    "private_key_id": private_key_id or "dummy_key_id",
                    "private_key": private_key,
                    "client_email": service_account_email,
                    "client_id": client_id or "dummy_client_id",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": client_x509_cert_url or f"https://www.googleapis.com/robot/v1/metadata/x509/{service_account_email}"
                }
                
                credentials = service_account.Credentials.from_service_account_info(credentials_info)
                logger.info("✅ 個別環境変数からの認証情報構築成功")
                return credentials
            
            # 方法2: GOOGLE_APPLICATION_CREDENTIALS_JSON から読み込み
            credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
            if credentials_json:
                logger.info("🔑 JSON形式の認証情報を検出")
                credentials_info = json.loads(credentials_json)
                credentials = service_account.Credentials.from_service_account_info(credentials_info)
                return credentials
            
            # 方法3: Base64エンコードされた認証情報から読み込み
            credentials_base64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_BASE64")
            if credentials_base64:
                logger.info("🔑 Base64形式の認証情報を検出")
                credentials_json = base64.b64decode(credentials_base64).decode('utf-8')
                credentials_info = json.loads(credentials_json)
                credentials = service_account.Credentials.from_service_account_info(credentials_info)
                return credentials
            
            # 方法4: デフォルトの認証情報を使用
            logger.info("🔑 デフォルト認証情報を試行")
            credentials, project = google.auth.default()
            return credentials
            
        except Exception as e:
            logger.error(f"❌ 認証情報の取得に失敗: {e}")
            return None
    
    def initialize_clients(self):
        """GCPクライアントを初期化"""
        if self.initialized:
            return True
            
        try:
            logger.info("🔧 GCPクライアント初期化開始...")
            
            # 認証情報を取得
            self.credentials = self._get_credentials()
            if not self.credentials:
                raise Exception("認証情報が見つかりません")
            
            # BigQueryクライアント
            logger.info("📊 BigQueryクライアント初期化...")
            self.bq_client = bigquery.Client(
                project=self.project_id,
                credentials=self.credentials
            )
            
            # 接続テスト
            test_query = f"SELECT COUNT(*) as total FROM `{self.table_id}` LIMIT 1"
            query_job = self.bq_client.query(test_query)
            results = list(query_job.result())
            total_count = results[0].total if results else 0
            
            logger.info(f"✅ BigQuery接続確認: {total_count}件のデータを検出")
            
            # Vertex AI初期化
            logger.info("🤖 Vertex AI初期化...")
            aiplatform.init(
                project=self.project_id,
                location=self.location,
                credentials=self.credentials
            )
            self.ai_platform_initialized = True
            logger.info("✅ Vertex AI初期化完了")
            
            self.initialized = True
            logger.info("🎉 すべてのGCPクライアント初期化完了")
            return True
            
        except Exception as e:
            logger.error(f"❌ GCPクライアント初期化失敗: {e}")
            self.initialized = False
            return False
    
    def get_bigquery_client(self):
        """BigQueryクライアントを取得"""
        if not self.initialized:
            if not self.initialize_clients():
                return None
        return self.bq_client
    
    def is_vertex_ai_ready(self):
        """Vertex AIが利用可能かチェック"""
        return self.initialized and self.ai_platform_initialized
    
    def get_status(self):
        """現在のステータスを取得"""
        return {
            "initialized": self.initialized,
            "bigquery_ready": self.bq_client is not None,
            "vertex_ai_ready": self.ai_platform_initialized,
            "project_id": self.project_id,
            "location": self.location,
            "credentials_available": self.credentials is not None
        }

# グローバルクライアントマネージャー
gcp_manager = GCPClientManager()

def initialize_gcp_on_startup():
    """起動時のGCP初期化"""
    enable_init = os.getenv("ENABLE_GCP_INITIALIZATION", "false").lower() == "true"
    if enable_init:
        logger.info("🚀 起動時GCP初期化を実行...")
        return gcp_manager.initialize_clients()
    else:
        logger.info("⏸️ GCP初期化をスキップ（ENABLE_GCP_INITIALIZATION=false）")
        return False

def get_gcp_status():
    """GCPステータスを取得"""
    return gcp_manager.get_status()

def get_bigquery_client():
    """BigQueryクライアントを取得（初期化も実行）"""
    return gcp_manager.get_bigquery_client()

def is_vertex_ai_ready():
    """Vertex AIが利用可能かチェック"""
    return gcp_manager.is_vertex_ai_ready()
