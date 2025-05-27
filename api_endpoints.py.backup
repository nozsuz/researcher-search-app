"""
研究者検索アプリのAPIエンドポイント
フロントエンドから直接呼び出し可能なFastAPI実装
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
import os
import time
from typing import List, Optional
import logging

# 既存の検索ロジックをインポート
from researcher_search_app import (
    initialize_clients,
    search_researchers_in_bigquery_where_clause,
    search_researchers_semantic,
    expand_keywords_with_llm,
    get_embedding,
    SEARCH_TARGET_COLUMNS_KEYWORD,
    DISPLAY_COLUMNS
)

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI アプリケーション作成
app = FastAPI(
    title="研究者検索API",
    description="AI研究者検索システムのAPIエンドポイント",
    version="1.0.0"
)

# CORS設定（プロダクション環境では適切なoriginを指定）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切なドメインを指定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# グローバル変数でクライアントを保持
clients = {}

class SearchRequest(BaseModel):
    query: str
    method: str = "semantic"  # "semantic" or "keyword"
    max_results: int = 5
    use_llm_expansion: bool = False
    use_llm_summary: bool = False

class ResearcherResult(BaseModel):
    name_ja: Optional[str] = None
    name_en: Optional[str] = None
    main_affiliation_name_ja: Optional[str] = None
    main_affiliation_name_en: Optional[str] = None
    research_keywords_ja: Optional[str] = None
    research_fields_ja: Optional[str] = None
    profile_ja: Optional[str] = None
    paper_title_ja_first: Optional[str] = None
    project_title_ja_first: Optional[str] = None
    researchmap_url: Optional[str] = None
    relevance_score: Optional[float] = None
    distance: Optional[float] = None
    llm_summary: Optional[str] = None

class SearchResponse(BaseModel):
    status: str
    query: str
    method: str
    results: List[ResearcherResult]
    total: int
    execution_time: float
    executed_query_info: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """アプリケーション開始時にクライアントを初期化"""
    try:
        logger.info("クライアントを初期化中...")
        bq_client, main_llm_model, summary_llm_model, embedding_model = initialize_clients()
        
        if all([bq_client, main_llm_model, summary_llm_model, embedding_model]):
            clients['bq_client'] = bq_client
            clients['main_llm_model'] = main_llm_model
            clients['summary_llm_model'] = summary_llm_model
            clients['embedding_model'] = embedding_model
            logger.info("✅ クライアント初期化完了")
        else:
            logger.error("❌ クライアント初期化失敗")
            raise Exception("クライアント初期化に失敗しました")
    except Exception as e:
        logger.error(f"初期化エラー: {e}")
        # 本番環境では適切なエラーハンドリングを実装
        raise

@app.get("/")
async def root():
    """ヘルスチェックエンドポイント"""
    return {"message": "研究者検索API サーバー稼働中", "status": "healthy"}

@app.get("/health")
async def health_check():
    """詳細なヘルスチェック"""
    health_status = {
        "status": "healthy",
        "clients_initialized": bool(clients),
        "available_clients": list(clients.keys()),
        "timestamp": time.time()
    }
    return health_status

@app.post("/api/search", response_model=SearchResponse)
async def search_researchers(request: SearchRequest):
    """
    研究者検索APIエンドポイント
    """
    start_time = time.time()
    
    try:
        # クライアントの確認
        if not clients:
            raise HTTPException(status_code=500, detail="システムが初期化されていません")
        
        logger.info(f"検索開始: {request.query}, 方法: {request.method}")
        
        results_df = pd.DataFrame()
        executed_query_info = ""
        
        if request.method == "keyword":
            # キーワード検索
            search_terms = [request.query.strip()]
            
            if request.use_llm_expansion:
                try:
                    search_target_cols_hint = ', '.join(SEARCH_TARGET_COLUMNS_KEYWORD)
                    expanded_keywords = expand_keywords_with_llm(
                        request.query, 
                        clients['main_llm_model'], 
                        search_target_cols_hint
                    )
                    if expanded_keywords and set(expanded_keywords) != {request.query}:
                        search_terms = expanded_keywords
                        executed_query_info = f"拡張キーワード: {', '.join(expanded_keywords)}"
                except Exception as e:
                    logger.warning(f"キーワード拡張エラー: {e}")
                    executed_query_info = "キーワード拡張失敗、元のキーワードで検索"
            
            results_df, search_query_info = search_researchers_in_bigquery_where_clause(
                search_terms,
                target_columns=SEARCH_TARGET_COLUMNS_KEYWORD,
                bq_client=clients['bq_client'],
                max_results=request.max_results
            )
            
            if not executed_query_info:
                executed_query_info = search_query_info
        
        elif request.method == "semantic":
            # セマンティック検索
            query_emb = get_embedding(request.query, clients['embedding_model'])
            
            if query_emb:
                results_df = search_researchers_semantic(
                    query_emb,
                    embedding_column_name="embedding",
                    bq_client=clients['bq_client'],
                    max_results=request.max_results
                )
                executed_query_info = f"ベクトル次元: {len(query_emb)}"
            else:
                raise HTTPException(status_code=500, detail="エンベディング生成に失敗しました")
        
        else:
            raise HTTPException(status_code=400, detail="不正な検索方法です")
        
        # 結果をAPIレスポンス形式に変換
        researchers = []
        for _, row in results_df.iterrows():
            researcher = ResearcherResult()
            
            # 基本情報の設定
            for col in DISPLAY_COLUMNS:
                if col in row and pd.notna(row[col]):
                    setattr(researcher, col, str(row[col]).strip())
            
            # スコア情報の設定
            if 'relevance_score' in row and pd.notna(row['relevance_score']):
                researcher.relevance_score = float(row['relevance_score'])
            
            if 'distance' in row and pd.notna(row['distance']):
                researcher.distance = float(row['distance'])
            
            # LLM要約（オプション）
            if request.use_llm_summary and 'summary_llm_model' in clients:
                try:
                    from researcher_search_app import summarize_researcher_profile_llm_lite
                    summary = summarize_researcher_profile_llm_lite(
                        row.to_dict(), 
                        request.query, 
                        clients['summary_llm_model']
                    )
                    researcher.llm_summary = summary
                    time.sleep(0.5)  # レート制限対策
                except Exception as e:
                    logger.warning(f"LLM要約エラー: {e}")
                    researcher.llm_summary = "要約生成中にエラーが発生しました"
            
            researchers.append(researcher)
        
        execution_time = time.time() - start_time
        
        response = SearchResponse(
            status="success",
            query=request.query,
            method=request.method,
            results=researchers,
            total=len(researchers),
            execution_time=execution_time,
            executed_query_info=executed_query_info
        )
        
        logger.info(f"検索完了: {len(researchers)}件, {execution_time:.2f}秒")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"検索エラー: {e}")
        raise HTTPException(status_code=500, detail=f"検索処理中にエラーが発生しました: {str(e)}")

@app.get("/api/search", response_model=SearchResponse)
async def search_researchers_get(
    query: str = Query(..., description="検索クエリ"),
    method: str = Query("semantic", description="検索方法 (semantic/keyword)"),
    max_results: int = Query(5, ge=1, le=20, description="最大結果数"),
    use_llm_expansion: bool = Query(False, description="LLMキーワード拡張"),
    use_llm_summary: bool = Query(False, description="LLM要約生成")
):
    """
    GET版の研究者検索エンドポイント（簡易テスト用）
    """
    request = SearchRequest(
        query=query,
        method=method,
        max_results=max_results,
        use_llm_expansion=use_llm_expansion,
        use_llm_summary=use_llm_summary
    )
    return await search_researchers(request)

# エラーハンドラー
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"予期しないエラー: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "内部サーバーエラーが発生しました"}
    )

if __name__ == "__main__":
    import uvicorn
    import os
    
    # 環境変数からポートを取得（Railwayで自動設定される）
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🚀 Starting FastAPI server on port {port}")
    print(f"📊 Project ID: {PROJECT_ID}")
    print(f"📍 Location: {LOCATION}")
    
    uvicorn.run(
        "api_endpoints:app",
        host="0.0.0.0", 
        port=port,
        reload=False,  # 本番環境ではreloadを無効化
        log_level="info"
    )
