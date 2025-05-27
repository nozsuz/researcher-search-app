# Streamlit用のAPIエンドポイント設定
import streamlit as st
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import threading
import time

# FastAPI アプリケーションの作成
api_app = FastAPI()

# CORS設定
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切なドメインを指定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@api_app.get("/api/search")
async def search_researchers(query: str, method: str = "semantic", max_results: int = 5):
    """
    研究者検索APIエンドポイント
    """
    try:
        # ここでメインアプリの検索ロジックを呼び出し
        if method == "semantic":
            # セマンティック検索
            results = perform_semantic_search(query, max_results)
        else:
            # キーワード検索
            results = perform_keyword_search(query, max_results)
        
        return {
            "status": "success",
            "query": query,
            "method": method,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def perform_semantic_search(query, max_results):
    # セマンティック検索の実装
    # （メインアプリから移植）
    pass

def perform_keyword_search(query, max_results):
    # キーワード検索の実装
    # （メインアプリから移植）
    pass

# バックグラウンドでFastAPIを実行
def run_api():
    uvicorn.run(api_app, host="0.0.0.0", port=8001)

if __name__ == "__main__":
    # APIサーバーをバックグラウンドで開始
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    # Streamlitアプリを実行
    exec(open('researcher_search_app.py').read())
