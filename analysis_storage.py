"""
分析結果の保存・取得機能
"""
import os
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional
from google.cloud import bigquery
import logging

logger = logging.getLogger(__name__)

BIGQUERY_ANALYSIS_TABLE = os.getenv(
    "BIGQUERY_ANALYSIS_TABLE", 
    "apt-rope-217206.researcher_data.researcher_analysis_results"
)

class AnalysisStorage:
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """BigQueryクライアントの初期化"""
        try:
            from gcp_auth import get_bigquery_client
            self.client = get_bigquery_client()
            logger.info("✅ AnalysisStorage: BigQueryクライアント初期化成功")
        except Exception as e:
            logger.error(f"❌ AnalysisStorage: BigQueryクライアント初期化失敗: {e}")
    
    async def save_analysis(
        self,
        researchmap_url: str,
        researcher_name: str,
        query: str,
        analysis_result: dict,
        relevance_score: Optional[float] = None,
        affiliation: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, any]:
        """分析結果を保存"""
        try:
            analysis_id = str(uuid.uuid4())
            
            # データの準備
            row = {
                "analysis_id": analysis_id,
                "researchmap_url": researchmap_url,
                "researcher_name": researcher_name,
                "affiliation": affiliation,
                "query": query,
                "analysis_result": json.dumps(analysis_result, ensure_ascii=False),
                "relevance_score": relevance_score,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id
            }
            
            # BigQueryに挿入
            table = self.client.get_table(BIGQUERY_ANALYSIS_TABLE)
            errors = self.client.insert_rows_json(table, [row])
            
            if errors:
                logger.error(f"❌ BigQuery挿入エラー: {errors}")
                return {
                    "status": "error",
                    "message": "保存に失敗しました",
                    "errors": errors
                }
            
            logger.info(f"✅ 分析結果保存成功: {analysis_id}")
            return {
                "status": "success",
                "analysis_id": analysis_id,
                "message": "分析結果を保存しました"
            }
            
        except Exception as e:
            logger.error(f"❌ 分析結果保存エラー: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def get_analyses(
        self,
        session_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """保存済み分析を取得"""
        try:
            # クエリ構築
            conditions = []
            if session_id:
                conditions.append(f"session_id = '{session_id}'")
            if query:
                conditions.append(f"query LIKE '%{query}%'")
            
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            
            sql_query = f"""
            SELECT 
                analysis_id,
                researchmap_url,
                researcher_name,
                affiliation,
                query,
                analysis_result,
                relevance_score,
                created_at,
                session_id
            FROM `{BIGQUERY_ANALYSIS_TABLE}`
            {where_clause}
            ORDER BY created_at DESC
            LIMIT {limit}
            """
            
            query_job = self.client.query(sql_query)
            results = []
            
            for row in query_job:
                result = dict(row)
                # JSON文字列をパース
                if result.get('analysis_result'):
                    result['analysis_result'] = json.loads(result['analysis_result'])
                results.append(result)
            
            logger.info(f"✅ {len(results)}件の分析結果を取得")
            return results
            
        except Exception as e:
            logger.error(f"❌ 分析結果取得エラー: {e}")
            return []
    
    async def delete_analysis(self, analysis_id: str, session_id: str) -> Dict[str, any]:
        """分析結果を削除（セッション確認付き）"""
        try:
            # まず所有権を確認
            check_query = f"""
            SELECT session_id 
            FROM `{BIGQUERY_ANALYSIS_TABLE}`
            WHERE analysis_id = '{analysis_id}'
            """
            
            query_job = self.client.query(check_query)
            results = list(query_job)
            
            if not results:
                return {
                    "status": "error",
                    "message": "分析結果が見つかりません"
                }
            
            if results[0].session_id != session_id:
                return {
                    "status": "error", 
                    "message": "削除権限がありません"
                }
            
            # 削除実行
            delete_query = f"""
            DELETE FROM `{BIGQUERY_ANALYSIS_TABLE}`
            WHERE analysis_id = '{analysis_id}'
            """
            
            query_job = self.client.query(delete_query)
            query_job.result()  # 完了を待つ
            
            logger.info(f"✅ 分析結果削除成功: {analysis_id}")
            return {
                "status": "success",
                "message": "分析結果を削除しました"
            }
            
        except Exception as e:
            logger.error(f"❌ 分析結果削除エラー: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
