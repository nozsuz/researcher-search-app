"""
研究者検索API - v2.1.1 (パラメータ名修正版)
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import pandas as pd
import os
import time
import asyncio
from typing import List, Optional, Dict, Any
import logging

# 新しいインポートを追加
from project_manager import (
    project_manager, 
    ProjectCreateRequest, 
    ResearcherSelectionRequest, 
    MatchingRequest,
    TempProject
)

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI アプリケーション作成
app = FastAPI(
    title="研究者検索API",
    description="AI研究者検索システムのAPIエンドポイント",
    version="2.1.1"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 環境変数
PROJECT_ID = os.getenv("PROJECT_ID", "apt-rope-217206")
LOCATION = os.getenv("LOCATION", "us-central1")
BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE", "apt-rope-217206.researcher_data.rd_250524")

# グローバル変数でクライアントを保持
clients = {
    "initialized": False,
    "bq_client": None,
    "main_llm_model": None,
    "summary_llm_model": None,
    "embedding_model": None
}

class SearchRequest(BaseModel):
    query: str
    method: str = "semantic"
    # Fieldとaliasを使って、JSからのキャメルケース(maxResults)をPythonのスネークケース(max_results)にマッピング
    max_results: int = Field(5, alias='maxResults')
    exclude_keywords: Optional[List[str]] = Field(None, alias='excludeKeywords')
    use_llm_expansion: bool = Field(False, alias='useLlmExpansion')
    use_llm_summary: bool = Field(False, alias='useLlmSummary')
    use_internal_evaluation: bool = Field(False, alias='useInternalEvaluation')
    young_researcher_filter: bool = Field(False, alias='youngResearcherFilter')
    university_filter: Optional[List[str]] = Field(None, alias='universityFilter')

    class Config:
        # FastAPIがaliasを正しく使えるように設定
        allow_population_by_field_name = True

class ResearcherResult(BaseModel):
    name_ja: Optional[str] = None
    name_en: Optional[str] = None
    main_affiliation_name_ja: Optional[str] = None
    main_affiliation_name_en: Optional[str] = None
    main_affiliation_job_ja: Optional[str] = None
    main_affiliation_job_title_ja: Optional[str] = None
    main_affiliation_job_en: Optional[str] = None
    main_affiliation_job_title_en: Optional[str] = None
    research_keywords_ja: Optional[str] = None
    research_fields_ja: Optional[str] = None
    profile_ja: Optional[str] = None
    paper_title_ja_first: Optional[str] = None
    project_title_ja_first: Optional[str] = None
    researchmap_url: Optional[str] = None
    relevance_score: Optional[float] = None
    distance: Optional[float] = None
    llm_summary: Optional[str] = None
    is_young_researcher: Optional[bool] = None
    young_researcher_reasons: Optional[List[str]] = None

class SearchResponse(BaseModel):
    status: str
    query: str
    method: str
    results: List[ResearcherResult] = []
    total: int
    execution_time: float
    executed_query_info: Optional[str] = None
    expanded_info: Optional[dict] = None

class AnalyzeRequest(BaseModel):
    researchmap_url: str
    query: str
    researcher_basic_info: Optional[Dict[str, Any]] = None

class AnalysisResponse(BaseModel):
    status: str
    analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """アプリケーション開始時にGCPクライアントを初期化"""
    logger.info("🚀 アプリケーション開始 - GCP初期化を実行")
    logger.info(f"📊 Project ID: {PROJECT_ID}")
    logger.info(f"📍 Location: {LOCATION}")
    
    try:
        from gcp_auth import initialize_gcp_on_startup, get_gcp_status
        success = initialize_gcp_on_startup()
        status = get_gcp_status()
        
        if success:
            logger.info("✅ GCPクライアント初期化成功")
            clients["initialized"] = True
        else:
            logger.warning("⚠️ GCPクライアント初期化失敗 - モックモードで継続")
            clients["initialized"] = False
            
        logger.info(f"📊 GCPステータス: {status}")
        
    except Exception as e:
        logger.error(f"❌ GCP初期化中にエラー: {e}")
        clients["initialized"] = False

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "🚀 研究者検索API v2.1.1 サーバー稼働中（プロジェクト管理統合・パラメータ修正版）",
        "status": "healthy",
        "timestamp": time.time(),
        "version": "2.1.1",
        "endpoints": {
            "/health": "ヘルスチェック",
            "/api/universities": "大学リスト",
            "/api/search": "研究者検索",
            "/api/analyze-researcher": "研究者詳細分析",
            "/api/temp-projects": "仮プロジェクト管理",
            "/test_api.html": "テストツール"
        },
        "features": {
            "search_api": "✅ 利用可能" if clients["initialized"] else "🔄 準備中",
            "gcp_integration": "✅ 準備完了" if clients["initialized"] else "🔄 準備中",
            "researchmap_analysis": "✅ 利用可能",
            "project_management": "✅ 利用可能",
            "matching_system": "✅ 利用可能"
        }
    }

@app.get("/test_api.html")
async def test_api_page():
    """テストAPIページ"""
    return FileResponse("test_api.html")

@app.get("/health")
async def health_check():
    """詳細なヘルスチェック"""
    try:
        from gcp_auth import get_gcp_status
        gcp_status = get_gcp_status()
    except Exception as e:
        gcp_status = {"error": str(e)}
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "server_info": {
            "version": "2.1.1",
            "project_id": PROJECT_ID,
            "location": LOCATION
        },
        "clients_status": {
            "initialized": clients["initialized"],
            "bigquery": "✅ 準備完了" if gcp_status.get("bigquery_ready") else "🔄 準備中",
            "vertex_ai": "✅ 準備完了" if gcp_status.get("vertex_ai_ready") else "🔄 準備中",
            "credentials": "✅ 設定済" if gcp_status.get("credentials_available") else "❌ 未設定"
        },
        "endpoints": {
            "/": "✅ 利用可能",
            "/health": "✅ 利用可能",
            "/api/search": "✅ 実際検索可能" if clients["initialized"] else "🔄 準備中（モック応答あり）",
            "/api/universities": "✅ 利用可能",
            "/api/analyze-researcher": "✅ ResearchMap分析可能",
            "/api/temp-projects": "✅ プロジェクト管理可能",
            "/test_api.html": "✅ 利用可能"
        },
        "gcp_details": gcp_status
    }
    return health_status

def get_simple_university_query(table_name: str) -> str:
    """
    【最終改善版】特殊な統合ルールと、一般的な正規化を組み合わせたクエリ
    """
    return f"""
    WITH base_data AS (
      SELECT 
        main_affiliation_name_ja,
        name_ja
      FROM `{table_name}`
      WHERE main_affiliation_name_ja IS NOT NULL AND main_affiliation_name_ja LIKE '%大学%'
    ),
    
    cleaned_names AS (
      SELECT
        CASE
          -- STEP 1: 【最優先】特殊な統合ルールを先に定義
          WHEN main_affiliation_name_ja LIKE '%東京工業大学%' THEN '東京科学大学'
          WHEN main_affiliation_name_ja LIKE '%東京医科歯科大学%' THEN '東京科学大学'
          WHEN main_affiliation_name_ja LIKE '%東海国立大学%' THEN '名古屋大学'
          WHEN main_affiliation_name_ja LIKE '%東海国立大学機構%' THEN '名古屋大学'
          
          -- STEP 2: 上記の特殊ルールに当てはまらない場合に、一般的な正規化を適用
          ELSE
            TRIM(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(
                            main_affiliation_name_ja,
                            '^(国立大学法人|学校法人|公立大学法人)\\\\s*', ''
                        ),
                        '／.*$', ''
                    ),
                    '\\\\s*(大学院|大学病院|病院|研究院|研究センター|研究科|学部|附属|特任准教授|教授|准教授|客員|機構|センター).*$', ''
                )
            )
        END AS university_name,
        name_ja,
        main_affiliation_name_ja as original_name
      FROM base_data
    ),

    validated_universities AS (
      SELECT 
        university_name,
        name_ja,
        original_name
      FROM cleaned_names
      WHERE university_name IS NOT NULL
        AND university_name LIKE '%大学'
        AND LENGTH(university_name) >= 3
    )
    
    SELECT 
      university_name,
      COUNT(DISTINCT name_ja) as researcher_count,
      ARRAY_AGG(DISTINCT original_name ORDER BY original_name LIMIT 5) as original_names
    FROM validated_universities
    GROUP BY university_name
    HAVING COUNT(DISTINCT name_ja) >= 5
    ORDER BY researcher_count DESC
    LIMIT 100
    """
    
@app.get("/api/universities")
async def get_universities():
    """
    登録されている大学名とその研究者数を取得
    """
    start_time = time.time()
    
    try:
        logger.info("🏫 大学リスト取得開始")
        
        try:
            from gcp_auth import get_bigquery_client
            get_bigquery_client() # 存在チェック
        except ImportError as e:
            logger.error(f"❌ モジュールインポートエラー: {e}")
            return await get_universities_fallback("module_import_error", str(e))
        
        bq_client = get_bigquery_client()
        
        if not bq_client:
            logger.warning("⚠️ BigQueryクライアントが利用できません - フォールバックモード")
            return await get_universities_fallback("bigquery_unavailable", "BigQueryクライアントが初期化されていません")
        
        try:
            query = get_simple_university_query(BIGQUERY_TABLE)
            query_job = bq_client.query(query)
            
            universities = []
            for row in query_job:
                universities.append({
                    "name": row.university_name,
                    "count": row.researcher_count
                })
            
            execution_time = time.time() - start_time
            logger.info(f"✅ 大学リスト取得完了: {len(universities)}校 ({execution_time:.2f}秒)")
            
            return {
                "status": "success",
                "total_universities": len(universities),
                "universities": universities,
                "execution_time": execution_time,
            }
            
        except Exception as e:
            logger.error(f"❌ BigQueryクエリ実行エラー: {e}")
            import traceback
            logger.error(f"📋 エラーの詳細: {traceback.format_exc()}")
            return await get_universities_fallback("bigquery_execution_error", str(e))
            
    except Exception as e:
        logger.error(f"❌ 大学リスト取得で予期しないエラー: {e}")
        import traceback
        logger.error(f"📋 エラーの詳細: {traceback.format_exc()}")
        return await get_universities_fallback("unexpected_error", str(e))

async def get_universities_fallback(error_type: str, error_message: str):
    """
    大学リスト取得のフォールバック機能
    """
    logger.warning(f"🔄 フォールバックモード実行: {error_type}")
    
    mock_universities = [
        {"name": "京都大学", "count": 6264},
        {"name": "東京大学", "count": 5113},
        {"name": "大阪大学", "count": 4542},
        {"name": "東京科学大学", "count": 3503},
        {"name": "北海道大学", "count": 3515},
    ]
    
    return {
        "status": "fallback",
        "total_universities": len(mock_universities),
        "universities": mock_universities,
        "fallback_info": {
            "reason": error_type,
            "error_message": error_message,
        }
    }

class SummaryRequest(BaseModel):
    researchmap_url: str = Field(..., alias='researchmapUrl')
    query: str

    class Config:
        allow_population_by_field_name = True

@app.post("/api/generate-summary")
async def generate_single_summary(request: SummaryRequest):
    logger.info(f"🤖 AI要約生成リクエスト受信: {request.researchmap_url} (Query: {request.query})")
    
    # (実装は省略)
    # ...

@app.post("/api/search", response_model=SearchResponse)
async def search_researchers(request: SearchRequest):
    """
    研究者検索APIエンドポイント
    """
    start_time = time.time()
    
    logger.info(f"🔍 検索リクエスト受信: query={request.query}, method={request.method}, max_results={request.max_results}")
    if request.university_filter:
        logger.info(f"🏫 大学フィルター: {request.university_filter}")
    if request.exclude_keywords:
        logger.info(f"🚫 除外キーワード: {request.exclude_keywords}")

    try:
        from real_search import perform_real_search
        result = await perform_real_search(request)
        
        if result["status"] == "success":
            logger.info(f"✅ 実際の検索成功: {len(result.get('results', []))}件")
            return SearchResponse(**result)
        else:
            logger.warning(f"⚠️ 実際の検索失敗、モックにフォールバック: {result.get('error_message')}")
            
    except Exception as e:
        import traceback
        logger.error(f"⚠️ 実際の検索でエラー、モックにフォールバック: {e}\n{traceback.format_exc()}")

    # フォールバック用のモック応答
    return SearchResponse(
        status="fallback",
        query=request.query,
        method=request.method,
        results=[],
        total=0,
        execution_time=(time.time() - start_time),
        executed_query_info="モック検索実行（エラー発生）",
    )

@app.post("/api/analyze-researcher", response_model=AnalysisResponse)
async def analyze_researcher(request: AnalyzeRequest):
    # (実装は省略)
    # ...

# =============================================================================
# プロジェクト管理API エンドポイント (変更なし)
# =============================================================================
@app.post("/api/temp-projects", response_model=TempProject)
async def create_temp_project(request: ProjectCreateRequest):
    # (実装は省略)
    pass
# ... (他のプロジェクト管理エンドポイントも同様に省略)

# エラーハンドラー
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"予期しないエラー: {exc}")
    import traceback
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": f"内部サーバーエラー: {str(exc)}"}
    )

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting Research API v2.1.1 (パラメータ修正版) on port {port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
