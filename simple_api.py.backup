"""
シンプルなAPIサーバー（テスト用）
複雑な依存関係なしで起動確認
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import time

# シンプルなFastAPIアプリ
app = FastAPI(
    title="研究者検索API (シンプル版)",
    description="テスト用のシンプルAPIエンドポイント",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "研究者検索API (シンプル版) サーバー稼働中",
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "message": "サーバー正常稼働中",
        "timestamp": time.time(),
        "environment": {
            "PORT": os.environ.get("PORT", "8000"),
            "PYTHON_VERSION": os.environ.get("PYTHON_VERSION", "unknown")
        }
    }

@app.get("/test")
async def test_endpoint():
    """テスト用エンドポイント"""
    return {
        "test": "success",
        "message": "テストエンドポイント正常",
        "data": {
            "sample_number": 12345,
            "sample_text": "Hello from Railway!"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting Simple API server on port {port}")
    
    uvicorn.run(
        "simple_api:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
