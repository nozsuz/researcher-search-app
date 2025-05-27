#!/usr/bin/env python3
"""
Railway用エントリーポイント
"""

import os
import sys

# 環境変数の確認
print("🔍 Environment Check:")
print(f"PORT: {os.environ.get('PORT', 'Not set')}")
print(f"PYTHON_VERSION: {sys.version}")
print(f"Working Directory: {os.getcwd()}")

# 必要なモジュールが利用可能か確認
try:
    import fastapi
    print(f"✅ FastAPI: {fastapi.__version__}")
except ImportError:
    print("❌ FastAPI not available")
    sys.exit(1)

try:
    import uvicorn
    print(f"✅ Uvicorn: {uvicorn.__version__}")
except ImportError:
    print("❌ Uvicorn not available")
    sys.exit(1)

# シンプルAPIサーバーを起動
print("🚀 Starting FastAPI server...")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(
        "simple_api:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
