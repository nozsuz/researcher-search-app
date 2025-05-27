#!/bin/bash
# ローカルテスト用スクリプト

echo "🔍 Local Test Starting..."
echo "PORT=8000" > .env.local

# 仮想環境がない場合は作成
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# 仮想環境をアクティブ化
source venv/bin/activate || venv\Scripts\activate

# 依存関係をインストール
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# サーバーを起動
echo "🚀 Starting local server..."
export PORT=8000
python start_server.py