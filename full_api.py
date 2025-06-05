"""
研究者検索API - 完全版
基本サーバーに検索機能を段階的に追加
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
from pydantic import BaseModel
import pandas as pd
import os
import time
from typing import List, Optional
import logging
from analysis_storage import AnalysisStorage

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

# AnalysisStorageインスタンス
analysis_storage = AnalysisStorage()

class SearchRequest(BaseModel):
    query: str
    method: str = "semantic"  # "semantic" or "keyword"
    max_results: int = 5
    use_llm_expansion: bool = False
    use_llm_summary: bool = False
    young_researcher_filter: bool = False

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
    results: List[ResearcherResult]
    total: int
    execution_time: float
    executed_query_info: Optional[str] = None
    expanded_info: Optional[dict] = None

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

@app.post("/api/search")
async def search_researchers(request: SearchRequest):
    """
    研究者検索APIエンドポイント（実際の検索 + フォールバック）
    """
    start_time = time.time()
    
    logger.info(f"🔍 検索リクエスト受信: {request.query}, method: {request.method}")
    
    # 実際の検索を試行し、失敗した場合はモックにフォールバック
    try:
        # 実際の検索を試行
        from real_search import perform_real_search
        result = await perform_real_search(request)
        
        if result["status"] == "success":
            logger.info(f"✅ 実際の検索成功: {len(result['results'])}件")
            
            # デバッグ：最初の結果の若手研究者フィールドを確認
            if result['results'] and len(result['results']) > 0:
                first_result = result['results'][0]
                logger.info(f"🔍 API返却前の最初の結果:")
                logger.info(f"  - name_ja: {first_result.get('name_ja', 'NOT FOUND')}")
                logger.info(f"  - is_young_researcher: {first_result.get('is_young_researcher', 'NOT FOUND')}")
                logger.info(f"  - young_researcher_reasons: {first_result.get('young_researcher_reasons', 'NOT FOUND')}")
            
            # JSONResponseを使用して明示的に返す
            logger.info(f"📦 JSONResponseで返します")
            
            # デバッグ：JSONシリアライズテスト
            try:
                json_str = json.dumps(result, ensure_ascii=False)
                logger.info(f"📝 JSONシリアライズ成功")
            except Exception as e:
                logger.error(f"❌ JSONシリアライズエラー: {e}")
            
            return JSONResponse(content=result)
        else:
            logger.warning(f"⚠️ 実際の検索失敗、モックにフォールバック: {result.get('error_message')}")
            
    except Exception as e:
        logger.warning(f"⚠️ 実際の検索でエラー、モックにフォールバック: {e}")
    
    # モック検索（フォールバック）
    mock_results = []
    
    if request.query:
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
        
        # モックデータにも若手研究者情報を追加
        for i, result in enumerate(mock_results):
            result["is_young_researcher"] = i % 2 == 0  # モックでは偶数番目を若手とする
            result["young_researcher_reasons"] = ["モックデータ"] if result["is_young_researcher"] else []
    
    execution_time = time.time() - start_time
    
    # 実行情報の生成
    executed_query_info = f"モック検索実行（実際の検索は準備中） (方法: {request.method}"
    if request.use_llm_expansion:
        executed_query_info += ", キーワード拡張: ON"
    if request.use_llm_summary:
        executed_query_info += ", AI要約: ON"
    executed_query_info += ")"
    
    # 辞書形式で直接返す
    response = {
        "status": "success",
        "query": request.query,
        "method": request.method,
        "results": mock_results,
        "total": len(mock_results),
        "execution_time": execution_time,
        "executed_query_info": executed_query_info
    }
    
    logger.info(f"✅ モック検索完了: {len(mock_results)}件, {execution_time:.2f}秒")
    return response

@app.get("/api/search")
async def search_researchers_get(
    query: str = Query(..., description="検索クエリ"),
    method: str = Query("semantic", description="検索方法 (semantic/keyword)"),
    max_results: int = Query(5, ge=1, le=20, description="最大結果数"),
    use_llm_expansion: bool = Query(False, description="LLMキーワード拡張"),
    use_llm_summary: bool = Query(False, description="LLM要約生成")
):
    """
    GET版の研究者検索エンドポイント（テスト用）
    """
    request = SearchRequest(
        query=query,
        method=method,
        max_results=max_results,
        use_llm_expansion=use_llm_expansion,
        use_llm_summary=use_llm_summary
    )
    return await search_researchers(request)

# ResearchMap詳細分析のためのモデル
class ResearchMapAnalysisRequest(BaseModel):
    researchmap_url: str
    query: str
    researcher_basic_info: Optional[dict] = None

class ResearchMapAnalysisResponse(BaseModel):
    status: str
    analysis: Optional[dict] = None
    error: Optional[str] = None

# 分析結果保存用のモデル
class SaveAnalysisRequest(BaseModel):
    researchmap_url: str
    researcher_name: str
    query: str
    analysis_result: dict
    relevance_score: Optional[float] = None
    affiliation: Optional[str] = None
    session_id: Optional[str] = None

class GetAnalysesRequest(BaseModel):
    session_id: Optional[str] = None
    query: Optional[str] = None
    limit: int = 50

@app.post("/api/analyze-researcher", response_model=ResearchMapAnalysisResponse)
async def analyze_researcher_detail(request: ResearchMapAnalysisRequest):
    """
    ResearchMap APIから詳細情報を取得してLLMで分析
    """
    try:
        # ResearchMapAnalyzerを使用
        from researchmap.analyzer import ResearchMapAnalyzer
        
        analyzer = ResearchMapAnalyzer()
        
        # 分析を実行
        result = await analyzer.analyze_researcher(
            researchmap_url=request.researchmap_url,
            query=request.query,
            basic_info=request.researcher_basic_info
        )
        
        if result["status"] == "success":
            return ResearchMapAnalysisResponse(
                status="success",
                analysis=result["analysis"]
            )
        else:
            return ResearchMapAnalysisResponse(
                status="error",
                error=result.get("error", "不明なエラー")
            )

        
    except Exception as e:
        logger.error(f"❌ ResearchMap分析エラー: {e}")
        return ResearchMapAnalysisResponse(
            status="error",
            error=str(e)
        )

# 分析結果保存エンドポイント
@app.post("/api/save-analysis")
async def save_analysis(request: SaveAnalysisRequest):
    """分析結果を保存"""
    result = await analysis_storage.save_analysis(
        researchmap_url=request.researchmap_url,
        researcher_name=request.researcher_name,
        query=request.query,
        analysis_result=request.analysis_result,
        relevance_score=request.relevance_score,
        affiliation=request.affiliation,
        session_id=request.session_id
    )
    return result

@app.post("/api/get-saved-analyses")
async def get_saved_analyses(request: GetAnalysesRequest):
    """保存済み分析を取得"""
    results = await analysis_storage.get_analyses(
        session_id=request.session_id,
        query=request.query,
        limit=request.limit
    )
    return {
        "status": "success",
        "analyses": results,
        "total": len(results)
    }

@app.delete("/api/delete-analysis/{analysis_id}")
async def delete_analysis(analysis_id: str, session_id: str = Query(...)):
    """分析結果を削除"""
    result = await analysis_storage.delete_analysis(analysis_id, session_id)
    return result

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
        "full_api:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
