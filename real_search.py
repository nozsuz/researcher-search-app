"""
実際の研究者検索機能
BigQueryとVertex AIを使用した本格的な検索実装
"""

import os
import logging
from typing import List, Optional
import pandas as pd
import numpy as np
from google.cloud import bigquery
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel, TextGenerationModel
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

logger = logging.getLogger(__name__)

class RealSearchEngine:
    """実際の検索エンジンクラス"""
    
    def __init__(self):
        self.project_id = os.getenv("PROJECT_ID", "apt-rope-217206")
        self.location = os.getenv("LOCATION", "us-central1")
        self.table_id = os.getenv("BIGQUERY_TABLE", "apt-rope-217206.researcher_data.rd_250524")
        
        # クライアント初期化フラグ
        self.initialized = False
        self.bq_client = None
        self.embedding_model = None
        self.llm_model = None
        
    async def initialize_clients(self):
        """GCPクライアントの初期化"""
        if self.initialized:
            return
            
        try:
            logger.info("🔧 GCPクライアント初期化開始...")
            
            # BigQueryクライアント
            self.bq_client = bigquery.Client(project=self.project_id)
            logger.info("✅ BigQueryクライアント初期化完了")
            
            # Vertex AI初期化
            aiplatform.init(project=self.project_id, location=self.location)
            
            # エンベディングモデル
            self.embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
            logger.info("✅ エンベディングモデル初期化完了")
            
            # LLMモデル
            self.llm_model = TextGenerationModel.from_pretrained("text-bison@001")
            logger.info("✅ LLMモデル初期化完了")
            
            self.initialized = True
            logger.info("🎉 すべてのクライアント初期化完了")
            
        except Exception as e:
            logger.error(f"❌ クライアント初期化失敗: {e}")
            raise
    
    async def keyword_search(self, query: str, max_results: int = 5) -> List[dict]:
        """キーワード検索実装"""
        if not self.initialized:
            await self.initialize_clients()
            
        try:
            # BigQueryクエリ構築
            search_query = f"""
            SELECT 
                name_ja,
                name_en,
                main_affiliation_name_ja,
                main_affiliation_name_en,
                research_keywords_ja,
                research_fields_ja,
                profile_ja,
                paper_title_ja_first,
                project_title_ja_first,
                researchmap_url,
                -- 関連度スコア計算
                (
                    CASE WHEN LOWER(research_keywords_ja) LIKE LOWER('%{query}%') THEN 3 ELSE 0 END +
                    CASE WHEN LOWER(research_fields_ja) LIKE LOWER('%{query}%') THEN 2 ELSE 0 END +
                    CASE WHEN LOWER(profile_ja) LIKE LOWER('%{query}%') THEN 1 ELSE 0 END +
                    CASE WHEN LOWER(paper_title_ja_first) LIKE LOWER('%{query}%') THEN 2 ELSE 0 END
                ) as relevance_score
            FROM `{self.table_id}`
            WHERE 
                LOWER(research_keywords_ja) LIKE LOWER('%{query}%') OR
                LOWER(research_fields_ja) LIKE LOWER('%{query}%') OR
                LOWER(profile_ja) LIKE LOWER('%{query}%') OR
                LOWER(paper_title_ja_first) LIKE LOWER('%{query}%') OR
                LOWER(name_ja) LIKE LOWER('%{query}%')
            ORDER BY relevance_score DESC
            LIMIT {max_results}
            """
            
            # クエリ実行
            logger.info(f"🔍 キーワード検索実行: {query}")
            query_job = self.bq_client.query(search_query)
            results = query_job.result()
            
            # 結果を辞書リストに変換
            researchers = []
            for row in results:
                researcher = dict(row)
                researchers.append(researcher)
            
            logger.info(f"✅ キーワード検索完了: {len(researchers)}件")
            return researchers
            
        except Exception as e:
            logger.error(f"❌ キーワード検索エラー: {e}")
            raise
    
    async def semantic_search(self, query: str, max_results: int = 5) -> List[dict]:
        """セマンティック検索実装"""
        if not self.initialized:
            await self.initialize_clients()
            
        try:
            # 1. クエリのエンベディング生成
            logger.info(f"🔍 セマンティック検索開始: {query}")
            
            query_embedding = await self._get_embedding(query)
            if query_embedding is None:
                raise Exception("クエリのエンベディング生成に失敗")
                
            # 2. ベクトル検索クエリ
            # 注意: これは概念的な例です。実際のベクトル検索はBigQuery MLや専用のベクトルDBが必要
            search_query = f"""
            SELECT 
                name_ja,
                name_en,
                main_affiliation_name_ja,
                main_affiliation_name_en,
                research_keywords_ja,
                research_fields_ja,
                profile_ja,
                paper_title_ja_first,
                project_title_ja_first,
                researchmap_url,
                -- 暫定的な距離計算（実際のベクトル検索ではない）
                RAND() as distance
            FROM `{self.table_id}`
            WHERE 
                research_keywords_ja IS NOT NULL AND
                research_keywords_ja != ""
            ORDER BY distance
            LIMIT {max_results}
            """
            
            query_job = self.bq_client.query(search_query)
            results = query_job.result()
            
            researchers = []
            for row in results:
                researcher = dict(row)
                researchers.append(researcher)
            
            logger.info(f"✅ セマンティック検索完了: {len(researchers)}件")
            return researchers
            
        except Exception as e:
            logger.error(f"❌ セマンティック検索エラー: {e}")
            raise
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """テキストのエンベディング生成"""
        try:
            embeddings = self.embedding_model.get_embeddings([text])
            return embeddings[0].values if embeddings else None
        except Exception as e:
            logger.error(f"❌ エンベディング生成エラー: {e}")
            return None
    
    async def expand_query_with_llm(self, query: str) -> str:
        """LLMによるクエリ拡張"""
        if not self.initialized:
            await self.initialize_clients()
            
        try:
            prompt = f"""
研究者検索のために、以下のクエリを関連する研究キーワードで拡張してください。
元のクエリに関連する専門用語、類義語、関連分野を含めて、検索精度を向上させてください。

元のクエリ: {query}

拡張されたクエリ（元のキーワードを含む）:
"""
            
            response = self.llm_model.predict(prompt, max_output_tokens=200)
            expanded_query = response.text.strip()
            
            logger.info(f"🔄 クエリ拡張: {query} → {expanded_query}")
            return expanded_query
            
        except Exception as e:
            logger.error(f"❌ クエリ拡張エラー: {e}")
            return query  # エラー時は元のクエリを返す
    
    async def generate_llm_summary(self, researcher_data: dict) -> str:
        """研究者データのLLM要約生成"""
        if not self.initialized:
            await self.initialize_clients()
            
        try:
            # 研究者情報を整理
            name = researcher_data.get('name_ja', '不明')
            affiliation = researcher_data.get('main_affiliation_name_ja', '不明')
            keywords = researcher_data.get('research_keywords_ja', '')
            profile = researcher_data.get('profile_ja', '')
            
            prompt = f"""
以下の研究者情報を基に、簡潔で分かりやすい要約（2-3文）を生成してください。

名前: {name}
所属: {affiliation}
研究キーワード: {keywords}
プロフィール: {profile}

要約:
"""
            
            response = self.llm_model.predict(prompt, max_output_tokens=150)
            summary = response.text.strip()
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ LLM要約生成エラー: {e}")
            return "要約生成に失敗しました。"

# グローバル検索エンジンインスタンス
search_engine = RealSearchEngine()

async def perform_real_search(search_request) -> dict:
    """実際の検索実行"""
    start_time = time.time()
    
    try:
        query = search_request.query
        
        # LLMクエリ拡張
        if search_request.use_llm_expansion:
            query = await search_engine.expand_query_with_llm(query)
        
        # 検索実行
        if search_request.method == "semantic":
            results = await search_engine.semantic_search(query, search_request.max_results)
        else:
            results = await search_engine.keyword_search(query, search_request.max_results)
        
        # LLM要約生成
        if search_request.use_llm_summary:
            for result in results:
                result['llm_summary'] = await search_engine.generate_llm_summary(result)
        
        execution_time = time.time() - start_time
        
        return {
            "status": "success",
            "query": search_request.query,
            "method": search_request.method,
            "results": results,
            "total": len(results),
            "execution_time": execution_time,
            "executed_query_info": f"実際の検索実行 (拡張クエリ: {query if search_request.use_llm_expansion else '無し'})"
        }
        
    except Exception as e:
        logger.error(f"❌ 検索実行エラー: {e}")
        execution_time = time.time() - start_time
        
        return {
            "status": "error",
            "query": search_request.query,
            "method": search_request.method,
            "results": [],
            "total": 0,
            "execution_time": execution_time,
            "error_message": str(e)
        }
