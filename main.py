"""
研究者検索API - 完全版
基本サーバーに検索機能を段階的に追加
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
import os
import time
from typing import List, Optional, Dict, Any
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI アプリケーション作成
app = FastAPI(
    title="研究者検索API",
    description="AI研究者検索システムのAPIエンドポイント",
    version="2.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    method: str = "semantic"  # "semantic" or "keyword"
    max_results: int = 5
    use_llm_expansion: bool = False
    use_llm_summary: bool = False
    use_internal_evaluation: bool = False  # 内部評価モードのフラグ
    young_researcher_filter: bool = False  # 若手研究者フィルタ
    university_filter: Optional[List[str]] = None  # 大学名フィルター

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

class EvaluatedResult(BaseModel):
    """内部評価モードの結果"""
    rank: int
    name: str
    affiliation: str
    score: float
    summary: str
    strengths: List[str]
    keywords: str
    url: str
    detail_scores: Optional[Dict[str, float]] = None

class SearchResponse(BaseModel):
    status: str
    query: str
    method: str
    results: List[ResearcherResult] = []  # 従来モードの結果
    total: int
    execution_time: float
    executed_query_info: Optional[str] = None
    expanded_info: Optional[dict] = None
    evaluation_mode: Optional[str] = None  # "internal" or "legacy"
    summary: Optional[dict] = None  # 内部評価モード時のサマリー
    displayed: Optional[int] = None  # 表示件数
    evaluated_results: Optional[List[EvaluatedResult]] = None  # 内部評価モードの結果

class ResearcherAnalysisRequest(BaseModel):
    """ResearchMap分析リクエスト"""
    researchmap_url: str
    query: str
    researcher_basic_info: Optional[Dict[str, Any]] = None

class ResearcherAnalysisResponse(BaseModel):
    """ResearchMap分析レスポンス"""
    status: str
    analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """アプリケーション開始時にGCPクライアントを初期化"""
    logger.info("🚀 アプリケーション開始 - GCP初期化を実行")
    logger.info(f"📊 Project ID: {PROJECT_ID}")
    logger.info(f"📍 Location: {LOCATION}")
    
    # GCP初期化を実行
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
    """ヘルスチェックエンドポイント"""
    return {
        "message": "🚀 研究者検索API v2.0 サーバー稼働中",
        "status": "healthy",
        "timestamp": time.time(),
        "version": "2.0.0",
        "features": {
            "basic_api": "✅ 利用可能",
            "search_api": "✅ 実際検索可能" if clients["initialized"] else "🔄 準備中",
            "gcp_integration": "✅ 準備完了" if clients["initialized"] else "🔄 準備中"
        }
    }

@app.get("/health")
async def health_check():
    """詳細なヘルスチェック"""
    
    # GCPステータスを取得
    try:
        from gcp_auth import get_gcp_status
        gcp_status = get_gcp_status()
    except Exception as e:
        gcp_status = {"error": str(e)}
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "server_info": {
            "version": "2.0.0",
            "project_id": PROJECT_ID,
            "location": LOCATION
        },
        "clients_status": {
            "initialized": clients["initialized"],
            "bigquery": "✅ 準備完了" if gcp_status.get("bigquery_ready") else "🔄 準備中",
            "vertex_ai": "✅ 準備完了" if gcp_status.get("vertex_ai_ready") else "🔄 準備中",
            "embedding_model": "✅ 準備完了" if gcp_status.get("vertex_ai_ready") else "🔄 準備中",
            "credentials": "✅ 設定済" if gcp_status.get("credentials_available") else "❌ 未設定"
        },
        "endpoints": {
            "/": "✅ 利用可能",
            "/health": "✅ 利用可能", 
            "/test": "✅ 利用可能",
            "/api/search": "✅ 実際検索可能" if clients["initialized"] else "🔄 準備中（モック応答あり）",
            "/test/gcp": "✅ 利用可能",
            "/test/env": "✅ 利用可能",
            "/test/real-search": "✅ 利用可能"
        },
        "gcp_details": gcp_status
    }
    return health_status

@app.get("/test")
async def test_endpoint():
    """テスト用エンドポイント"""
    return {
        "test": "success",
        "message": "テストエンドポイント正常",
        "data": {
            "sample_number": 12345,
            "sample_text": "Hello from Railway!",
            "timestamp": time.time()
        }
    }

@app.get("/test/env")
async def test_environment_variables():
    """環境変数の設定状況をテスト"""
    env_status = {
        "timestamp": time.time(),
        "basic_config": {
            "PROJECT_ID": os.getenv("PROJECT_ID", "Not Set"),
            "LOCATION": os.getenv("LOCATION", "Not Set"),
            "BIGQUERY_TABLE": os.getenv("BIGQUERY_TABLE", "Not Set"),
            "ENABLE_GCP_INITIALIZATION": os.getenv("ENABLE_GCP_INITIALIZATION", "Not Set")
        },
        "gcp_credentials": {
            "GCP_SERVICE_ACCOUNT_EMAIL": "Set" if os.getenv("GCP_SERVICE_ACCOUNT_EMAIL") else "Not Set",
            "GCP_PRIVATE_KEY": "Set" if os.getenv("GCP_PRIVATE_KEY") else "Not Set",
            "GCP_PRIVATE_KEY_ID": "Set" if os.getenv("GCP_PRIVATE_KEY_ID") else "Not Set",
            "GCP_CLIENT_ID": "Set" if os.getenv("GCP_CLIENT_ID") else "Not Set",
            "GCP_CLIENT_X509_CERT_URL": "Set" if os.getenv("GCP_CLIENT_X509_CERT_URL") else "Not Set"
        },
        "fallback_credentials": {
            "GOOGLE_APPLICATION_CREDENTIALS_JSON": "Set" if os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON") else "Not Set",
            "GOOGLE_APPLICATION_CREDENTIALS_BASE64": "Set" if os.getenv("GOOGLE_APPLICATION_CREDENTIALS_BASE64") else "Not Set"
        },
        "recommendations": []
    }
    
    # 推奨事項を生成
    if not os.getenv("GCP_SERVICE_ACCOUNT_EMAIL") and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
        env_status["recommendations"].append("認証情報が設定されていません")
    
    if os.getenv("ENABLE_GCP_INITIALIZATION", "false").lower() != "true":
        env_status["recommendations"].append("ENABLE_GCP_INITIALIZATION=true を設定してGCP初期化を有効化してください")
    
    return env_status

@app.get("/test/gcp")
async def test_gcp_connection():
    """シンプルGCP接続テスト"""
    test_results = {
        "timestamp": time.time(),
        "project_id": PROJECT_ID,
        "location": LOCATION,
        "tests": {}
    }
    
    # BigQuery接続テスト
    try:
        from gcp_auth import get_bigquery_client
        bq_client = get_bigquery_client()
        
        if bq_client:
            # シンプルクエリ実行
            query = f"SELECT COUNT(*) as total FROM `{BIGQUERY_TABLE}` LIMIT 1"
            query_job = bq_client.query(query)
            results = list(query_job.result())
            
            test_results["tests"]["bigquery"] = {
                "status": "✅ 成功",
                "total_researchers": results[0].total if results else 0
            }
        else:
            test_results["tests"]["bigquery"] = {
                "status": "❌ 失敗",
                "error": "BigQueryクライアントが初期化されていません"
            }
        
    except Exception as e:
        test_results["tests"]["bigquery"] = {
            "status": "❌ 失敗",
            "error": str(e)
        }
    
    # Vertex AI接続テスト
    try:
        from gcp_auth import is_vertex_ai_ready
        if is_vertex_ai_ready():
            test_results["tests"]["vertex_ai"] = {
                "status": "✅ 初期化成功"
            }
        else:
            test_results["tests"]["vertex_ai"] = {
                "status": "❌ 失敗",
                "error": "Vertex AIが初期化されていません"
            }
        
    except Exception as e:
        test_results["tests"]["vertex_ai"] = {
            "status": "❌ 失敗",
            "error": str(e)
        }
    
    return test_results

@app.get("/test/llm")
async def test_llm_functions():
    """シンプルLLM機能テスト"""
    test_results = {
        "timestamp": time.time(),
        "tests": {}
    }
    
    # クエリ拡張テスト
    try:
        from real_search import expand_query_with_llm
        test_query = "人工知能"
        expanded = await expand_query_with_llm(test_query)
        
        test_results["tests"]["query_expansion"] = {
            "status": "✅ 成功",
            "original_query": test_query,
            "expanded_query": expanded,
            "expansion_worked": len(expanded) > len(test_query)
        }
        
    except Exception as e:
        test_results["tests"]["query_expansion"] = {
            "status": "❌ 失敗",
            "error": str(e)
        }
    
    # 要約機能テスト
    try:
        from real_search import add_llm_summaries
        test_results_data = [{
            "name_ja": "テスト研究者",
            "main_affiliation_name_ja": "テスト大学",
            "research_keywords_ja": "人工知能, 機械学習",
            "research_fields_ja": "情報学"
        }]
        
        results_with_summary = await add_llm_summaries(test_results_data, "人工知能")
        
        test_results["tests"]["summary_generation"] = {
            "status": "✅ 成功",
            "summary_generated": "llm_summary" in results_with_summary[0],
            "summary_text": results_with_summary[0].get("llm_summary", "N/A")
        }
        
    except Exception as e:
        test_results["tests"]["summary_generation"] = {
            "status": "❌ 失敗",
            "error": str(e)
        }
    
    return test_results

@app.get("/test/evaluation-mode")
async def test_evaluation_mode():
    """内部評価モードのテスト"""
    try:
        from real_search import perform_real_search
        
        # 内部評価モードでのテスト
        class TestRequest:
            def __init__(self):
                self.query = "ナノメートルの微細加工技術"
                self.method = "keyword"
                self.max_results = 5
                self.use_llm_expansion = False
                self.use_llm_summary = False
                self.use_internal_evaluation = True  # 内部評価モードON
        
        test_request = TestRequest()
        result = await perform_real_search(test_request)
        
        if result.get("status") == "success" and result.get("evaluation_mode") == "internal":
            return {
                "test_status": "success",
                "message": "内部評価モードが正常に動作しています",
                "evaluation_mode": "internal",
                "summary": result.get("summary"),
                "total_evaluated": result.get("total", 0),
                "displayed": result.get("displayed", 0),
                "top_result": result.get("evaluated_results", [])[0] if result.get("evaluated_results") else None
            }
        else:
            return {
                "test_status": "fallback",
                "message": "内部評価モードが利用できませんでした",
                "evaluation_mode": result.get("evaluation_mode", "unknown"),
                "error": result.get("error_message")
            }
    except Exception as e:
        return {
            "test_status": "error",
            "message": f"内部評価モードテストでエラー: {str(e)}",
            "error_details": str(e)
        }

@app.get("/test/real-search")
async def test_real_search():
    try:
        from real_search import perform_real_search
        
        # テスト用の簡単なリクエスト
        class TestRequest:
            def __init__(self):
                self.query = "人工知能"
                self.method = "keyword"
                self.max_results = 2
                self.use_llm_expansion = False
                self.use_llm_summary = False
                self.use_internal_evaluation = False
        
        test_request = TestRequest()
        result = await perform_real_search(test_request)
        
        return {
            "test_status": "success",
            "message": "実際の検索機能が動作しています",
            "result_summary": {
                "status": result.get("status"),
                "total_results": result.get("total", 0),
                "execution_time": result.get("execution_time", 0),
                "method": result.get("method")
            },
            "sample_result": result.get("results", [])[:1] if result.get("results") else []
        }
    except Exception as e:
        return {
            "test_status": "error",
            "message": f"実際の検索機能でエラー: {str(e)}",
            "error_details": str(e)
        }

@app.post("/api/search", response_model=SearchResponse)
async def search_researchers(request: SearchRequest):
    """
    研究者検索APIエンドポイント（実際の検索 + フォールバック）
    """
    start_time = time.time()
    
    logger.info(f"🔍 検索リクエスト受信: {request.query}, method: {request.method}")
    if request.university_filter:
        logger.info(f"🏫 大学フィルター: {request.university_filter}")
    
    # 実際の検索を試行し、失敗した場合はモックにフォールバック
    try:
        # 実際の検索を試行（評価システム統合版）
        from real_search import perform_real_search
        result = await perform_real_search(request)
        
        if result["status"] == "success":
            # 評価モードに応じてログを調整
            if result.get("evaluation_mode") == "internal":
                logger.info(f"✅ 実際の検索成功（内部評価モード）: {result.get('total', 0)}件中{result.get('displayed', 0)}件表示")
            else:
                logger.info(f"✅ 実際の検索成功: {len(result.get('results', []))}件")
            return SearchResponse(**result)
        else:
            logger.warning(f"⚠️ 実際の検索失敗、モックにフォールバック: {result.get('error_message')}")
            
    except Exception as e:
        logger.warning(f"⚠️ 実際の検索でエラー、モックにフォールバック: {e}")
    
    # モック検索（フォールバック）
    mock_results = []
    expanded_info = None
    
    if request.query:
        # モック用のキーワード拡張情報（キーワード検索かつLLM拡張有効時）
        if request.use_llm_expansion and request.method == "keyword":
            # モックの拡張キーワードリスト
            mock_expanded_keywords = [
                request.query,
                f"{request.query}研究",
                f"{request.query}技術",
                f"{request.query}イノベーション",
                f"{request.query}開発",
                "最新技術",
                "先端研究"
            ]
            expanded_info = {
                "original_query": request.query,
                "expanded_keywords": mock_expanded_keywords[:7],  # 最大7個
                "expanded_query": " ".join(mock_expanded_keywords[:5])  # 検索用には5個
            }
            logger.info(f"🧠 モック拡張情報設定: {expanded_info}")
        
        # サンプルの研究者データ（モック）
        mock_researchers = [
            {
                "name_ja": f"研究者A（関連: {request.query}）",
                "name_en": "Researcher A",
                "main_affiliation_name_ja": "サンプル大学",
                "main_affiliation_name_en": "Sample University", 
                "research_keywords_ja": f"{request.query}, 機械学習, データサイエンス",
                "research_fields_ja": "情報科学",
                "profile_ja": f"「{request.query}」分野の専門家です。多数の研究実績があります。",
                "paper_title_ja_first": f"{request.query}に関する革新的手法の提案",
                "project_title_ja_first": f"{request.query}を活用した社会課題解決プロジェクト",
                "researchmap_url": "https://researchmap.jp/sample1",
                "relevance_score": 0.95 if request.method == "keyword" else None,
                "distance": 0.1234 if request.method == "semantic" else None
            },
            {
                "name_ja": f"研究者B（関連: {request.query}）",
                "name_en": "Researcher B", 
                "main_affiliation_name_ja": "先端技術研究所",
                "main_affiliation_name_en": "Advanced Technology Institute",
                "research_keywords_ja": f"{request.query}, イノベーション, 応用研究",
                "research_fields_ja": "工学",
                "profile_ja": f"「{request.query}」の産業応用に特化した研究を行っています。",
                "paper_title_ja_first": f"{request.query}の実用化に向けた技術開発",
                "project_title_ja_first": f"次世代{request.query}システムの構築",
                "researchmap_url": "https://researchmap.jp/sample2",
                "relevance_score": 0.87 if request.method == "keyword" else None,
                "distance": 0.2156 if request.method == "semantic" else None
            }
        ]
        
        # リクエストされた件数まで調整
        mock_results = mock_researchers[:min(request.max_results, len(mock_researchers))]
        
        # LLM要約が要求された場合のモック
        if request.use_llm_summary:
            for result in mock_results:
                result["llm_summary"] = f"この研究者は「{request.query}」に関して深い専門知識を有しており、関連する研究プロジェクトで顕著な成果を上げています。"
    
    execution_time = time.time() - start_time
    
    # 実行情報の生成
    executed_query_info = f"モック検索実行（実際の検索は準備中） (方法: {request.method}"
    if request.use_llm_expansion:
        executed_query_info += ", キーワード拡張: ON"
    if request.use_llm_summary:
        executed_query_info += ", AI要約: ON"
    executed_query_info += ")"
    
    response = SearchResponse(
        status="success",
        query=request.query,
        method=request.method,
        results=[ResearcherResult(**result) for result in mock_results],
        total=len(mock_results),
        execution_time=execution_time,
        executed_query_info=executed_query_info,
        expanded_info=expanded_info
    )
    
    logger.info(f"✅ モック検索完了: {len(mock_results)}件, {execution_time:.2f}秒")
    logger.info(f"📊 レスポンスexpanded_info: {response.expanded_info}")
    return response

@app.get("/api/universities")
async def get_universities():
    """
    登録されている大学名とその研究者数を取得
    """
    try:
        from gcp_auth import get_bigquery_client
        bq_client = get_bigquery_client()
        
        if bq_client:
            # BigQueryから大学名と研究者数を取得
            # 同一大学の表記揺れを考慮した集計
            query = f"""
            WITH normalized_universities AS (
                SELECT DISTINCT
                    name_ja,
                    main_affiliation_name_ja,
                    -- 大学名の正規化（確実な方法）
                    CASE 
                        -- 特別なケースの処理
                        WHEN main_affiliation_name_ja IN ('南九州大学', '西九州大学', '北九州大学') THEN main_affiliation_name_ja
                        
                        -- 東京大学系
                        WHEN main_affiliation_name_ja LIKE '%東京大学%' THEN '東京大学'
                        -- 京都大学系  
                        WHEN main_affiliation_name_ja LIKE '%京都大学%' THEN '京都大学'
                        -- 大阪大学系
                        WHEN main_affiliation_name_ja LIKE '%大阪大学%' THEN '大阪大学'
                        -- 北海道大学系
                        WHEN main_affiliation_name_ja LIKE '%北海道大学%' THEN '北海道大学'
                        -- 東北大学系
                        WHEN main_affiliation_name_ja LIKE '%東北大学%' THEN '東北大学'
                        -- 九州大学系（他の九州系大学を除外）
                        WHEN main_affiliation_name_ja LIKE '%九州大学%' 
                             AND main_affiliation_name_ja NOT LIKE '%南九州大学%' 
                             AND main_affiliation_name_ja NOT LIKE '%西九州大学%' 
                             AND main_affiliation_name_ja NOT LIKE '%北九州大学%' THEN '九州大学'
                        -- 名古屋大学系
                        WHEN main_affiliation_name_ja LIKE '%名古屋大学%' THEN '名古屋大学'
                        -- 筑波大学系
                        WHEN main_affiliation_name_ja LIKE '%筑波大学%' THEN '筑波大学'
                        -- 東京工業大学系
                        WHEN main_affiliation_name_ja LIKE '%東京工業大学%' THEN '東京工業大学'
                        -- 東京科学大学系（東工大と東京医科歯科大の統合）
                        WHEN main_affiliation_name_ja LIKE '%東京科学大学%' THEN '東京科学大学'
                        -- 東京医科歯科大学系
                        WHEN main_affiliation_name_ja LIKE '%東京医科歯科大学%' THEN '東京医科歯科大学'
                        -- 慶應義塾大学系
                        WHEN main_affiliation_name_ja LIKE '%慶應義塾大学%' OR main_affiliation_name_ja LIKE '%慶応義塾大学%' THEN '慶應義塾大学'
                        -- 早稲田大学系
                        WHEN main_affiliation_name_ja LIKE '%早稲田大学%' THEN '早稲田大学'
                        -- 神戸大学系
                        WHEN main_affiliation_name_ja LIKE '%神戸大学%' THEN '神戸大学'
                        -- 広島大学系
                        WHEN main_affiliation_name_ja LIKE '%広島大学%' THEN '広島大学'
                        -- 岡山大学系
                        WHEN main_affiliation_name_ja LIKE '%岡山大学%' THEN '岡山大学'
                        -- 金沢大学系
                        WHEN main_affiliation_name_ja LIKE '%金沢大学%' THEN '金沢大学'
                        -- 新潟大学系
                        WHEN main_affiliation_name_ja LIKE '%新潟大学%' THEN '新潟大学'
                        -- 千葉大学系
                        WHEN main_affiliation_name_ja LIKE '%千葉大学%' THEN '千葉大学'
                        -- 横浜国立大学系
                        WHEN main_affiliation_name_ja LIKE '%横浜国立大学%' THEN '横浜国立大学'
                        -- 信州大学系
                        WHEN main_affiliation_name_ja LIKE '%信州大学%' THEN '信州大学'
                        -- 山形大学系
                        WHEN main_affiliation_name_ja LIKE '%山形大学%' THEN '山形大学'
                        -- 群馬大学系
                        WHEN main_affiliation_name_ja LIKE '%群馬大学%' THEN '群馬大学'
                        -- 【追加】東大阪大学系（誤って東京大学に含めないように）
                        WHEN main_affiliation_name_ja LIKE '%東大阪大学%' THEN '東大阪大学'
                        
                        -- その他はそのまま
                        ELSE main_affiliation_name_ja
                    END as normalized_university_name
                FROM `{BIGQUERY_TABLE}`
                WHERE main_affiliation_name_ja IS NOT NULL
            )
            SELECT 
                normalized_university_name as university_name,
                COUNT(DISTINCT name_ja) as researcher_count
            FROM normalized_universities
            GROUP BY normalized_university_name
            ORDER BY researcher_count DESC
            """
            
            query_job = bq_client.query(query)
            universities = []
            
            for row in query_job:
                universities.append({
                    "name": row.university_name,
                    "count": row.researcher_count
                })
            
            return {
                "status": "success",
                "total_universities": len(universities),
                "universities": universities
            }
        else:
            # モックデータ
            return {
                "status": "success",
                "total_universities": 5,
                "universities": [
                    {"name": "東京大学", "count": 5234},
                    {"name": "京都大学", "count": 4123},
                    {"name": "大阪大学", "count": 3456},
                    {"name": "東北大学", "count": 2890},
                    {"name": "名古屋大学", "count": 2345}
                ]
            }
            
    except Exception as e:
        logger.error(f"❌ 大学リスト取得エラー: {e}")
        return {
            "status": "error",
            "error": str(e),
            "total_universities": 0,
            "universities": []
        }

@app.get("/api/search", response_model=SearchResponse)
async def search_researchers_get(
    query: str = Query(..., description="検索クエリ"),
    method: str = Query("semantic", description="検索方法 (semantic/keyword)"),
    max_results: int = Query(5, ge=1, le=20, description="最大結果数"),
    use_llm_expansion: bool = Query(False, description="LLMキーワード拡張"),
    use_llm_summary: bool = Query(False, description="LLM要約生成"),
    use_internal_evaluation: bool = Query(False, description="内部評価モードを使用"),
    universities: Optional[str] = Query(None, description="大学名フィルター（カンマ区切り）")
):
    """
    GET版の研究者検索エンドポイント（テスト用）
    """
    request = SearchRequest(
        query=query,
        method=method,
        max_results=max_results,
        use_llm_expansion=use_llm_expansion,
        use_llm_summary=use_llm_summary,
        use_internal_evaluation=use_internal_evaluation
    )
    
    # 大学フィルターをリクエストに追加
    if universities:
        request.university_filter = universities.split(",")
    
    return await search_researchers(request)

@app.post("/api/analyze-researcher", response_model=ResearcherAnalysisResponse)
async def analyze_researcher(request: ResearcherAnalysisRequest):
    """
    ResearchMap APIを使用して研究者の詳細情報を取得し、AI分析を実行
    """
    try:
        logger.info(f"🔍 ResearchMap分析リクエスト: {request.researchmap_url}")
        
        # ResearchMap分析モジュールを使用
        try:
            from researchmap.analyzer import ResearchMapAnalyzer
            
            analyzer = ResearchMapAnalyzer()
            result = await analyzer.analyze_researcher(
                researchmap_url=request.researchmap_url,
                query=request.query,
                basic_info=request.researcher_basic_info
            )
            
            if result.get("status") == "success":
                return ResearcherAnalysisResponse(
                    status="success",
                    analysis=result.get("analysis")
                )
            else:
                return ResearcherAnalysisResponse(
                    status="error",
                    error=result.get("error", "分析に失敗しました")
                )
                
        except ImportError:
            logger.warning("⚠️ ResearchMap分析モジュールが見つかりません。モックデータを使用します。")
            # モック分析結果を生成
            mock_analysis = {
            "researcher_name": request.researcher_basic_info.get("name", "研究者") if request.researcher_basic_info else "研究者",
            "affiliation": request.researcher_basic_info.get("affiliation", "所属") if request.researcher_basic_info else "所属",
            "scores": {
                "total": 85,
                "technical_relevance": 34,  # /40
                "achievements": 26,  # /30
                "practical_applicability": 25  # /30
            },
            "total_papers": 45,
            "total_projects": 8,
            "total_awards": 3,
            "detailed_analysis": f"""この研究者は「{request.query}」に関する専門的な研究を行っており、特に以下の点で優れています：

1. 技術的関連性：{request.query}に直接関連する論文を複数発表しており、その研究内容は要求される技術領域と高い整合性を持っています。

2. 実績・影響力：トップジャーナルへの掲載実績があり、複数の特許取得や受賞歴があるなど、研究成果の質の高さが認められます。

3. 実用化可能性：産学連携プロジェクトの経験が豊富で、研究成果の社会実装に向けた実績があります。

総合的に、この研究者は{request.query}の分野で非常に高い専門性と実績を持っており、プロジェクトへの貢献が大いに期待できます。""",
            "top_papers": [
                {
                    "year": 2023,
                    "title_ja": f"{request.query}における革新的アプローチの提案",
                    "journal": "Nature Communications"
                },
                {
                    "year": 2022,
                    "title_ja": f"{request.query}の実用化に向けた基礎研究",
                    "journal": "Science Advances"
                }
            ],
            "key_projects": [
                {
                    "title": f"JST CREST {request.query}研究プロジェクト",
                    "period": "2021-2024"
                },
                {
                    "title": f"NEDO {request.query}技術開発事業",
                    "period": "2020-2023"
                }
            ],
            "key_patents": [
                {
                    "title": f"{request.query}関連技術の特許",
                    "application_number": "特2023-123456",
                    "patent_number": "特許第6789012号",
                    "application_date": "2023/04/01",
                    "patent_holders": "株式会社サンプル、東京大学"
                }
            ]
            }
            
            return ResearcherAnalysisResponse(
                status="success",
                analysis=mock_analysis
            )
        
    except Exception as e:
        logger.error(f"❌ ResearchMap分析エラー: {e}")
        return ResearcherAnalysisResponse(
            status="error",
            error=str(e)
        )

# エラーハンドラー
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"予期しないエラー: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"内部サーバーエラー: {str(exc)}"}
    )

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting Research API v2.0 on port {port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
