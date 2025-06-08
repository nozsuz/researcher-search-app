#!/bin/bash

echo "🚂 Railway修正のためのGit操作"
echo "================================"

echo "📝 現在の状況確認..."
git status

echo -e "\n📦 変更をステージング..."
git add railway.json
git add .env
git add railway_fix.py

echo -e "\n💾 コミット..."
git commit -m "Fix: Railway設定修正とGCP認証修復

- railway.jsonをmain.pyに修正
- .envにGCP初期化フラグ追加
- Railway環境変数診断ツール追加
- 検索機能の実際のAPI化を修復"

echo -e "\n🚀 Railwayにプッシュ..."
git push origin main

echo -e "\n✅ デプロイ完了！"
echo "🔗 Railway Dashboard で環境変数を設定してください"
echo "📊 デプロイ状況: railway logs で確認"
