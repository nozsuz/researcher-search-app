"""
超シンプルAPI - Railway デプロイテスト用
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# FastAPI アプリケーション
app = FastAPI(title="Research API Test")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "message": "🚀 Research API Server is running!",
        "status": "success",
        "port": os.environ.get("PORT", "8000")
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "research-api",
        "version": "1.0.0"
    }

@app.get("/test")
def test_endpoint():
    return {
        "test": "OK",
        "message": "Test endpoint working"
    }

# Railway 用のエントリーポイント
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
