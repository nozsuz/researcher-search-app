# デプロイメントガイド

## 更新履歴

### Version 2.1.0 (2024-12-XX)
- **新機能**: 内部評価モードの追加
  - 7つの観点から研究者を評価する汎用的な評価システム
  - 1-10のスケールで関連度をスコアリング
  - バッチ処理による効率的な評価
- **改善**: 検索結果の表示形式を最適化
  - 評価モード時は要約と主要情報のみ表示
  - 詳細スコアはオプションで表示可能
- **追加**: 新しいテストエンドポイント
  - `/test/evaluation-mode`: 内部評価モードの動作確認

## GitHubへのデプロイ手順

### 1. コミット前の確認
```bash
# 変更されたファイルを確認
git status

# 新しいファイルを追加
git add evaluation_system.py
git add real_search_with_evaluation.py

# 更新されたファイルを追加  
git add main.py
git add README.md
git add DEPLOYMENT_GUIDE.md

# 不要なファイルを削除
git rm real_search_original.py
```

### 2. コミットとプッシュ
```bash
# コミット
git commit -m "feat: 内部評価モードの実装

- 7つの観点による研究者評価システムを追加
- バッチ処理による効率的な評価を実現
- 評価結果の要約表示機能を追加
- テストエンドポイントを追加"

# プッシュ
git push origin main
```

### 3. Railwayでの自動デプロイ
GitHubへのプッシュ後、Railwayが自動的にデプロイを開始します。

## 動作確認

### 1. 基本的な動作確認
```bash
# ヘルスチェック
curl https://your-app.railway.app/

# GCP接続確認
curl https://your-app.railway.app/test/gcp
```

### 2. 新機能の確認
```bash
# 内部評価モードのテスト
curl https://your-app.railway.app/test/evaluation-mode

# 実際の検索（内部評価モード）
curl -X POST https://your-app.railway.app/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "機械学習",
    "method": "keyword", 
    "max_results": 5,
    "use_internal_evaluation": true
  }'
```

## トラブルシューティング

### エラー: LLMモデルが利用できない
- Vertex AI の初期化が完了しているか確認
- 環境変数 `ENABLE_GCP_INITIALIZATION=true` が設定されているか確認

### エラー: 評価がタイムアウトする
- バッチサイズを調整（evaluation_system.py の batch_size を小さくする）
- API制限に達している場合は時間をおいて再試行

### エラー: 内部評価モードが動作しない
- `/test/evaluation-mode` で詳細なエラーを確認
- ログで LLM モデルの初期化状況を確認

## パフォーマンス最適化

### 推奨設定
- `max_results`: 10以下（内部評価モード使用時）
- `use_llm_expansion`: false（セマンティック検索時）
- バッチサイズ: 5（デフォルト）

### キャッシング
将来的な実装予定：
- 評価結果のキャッシング
- クエリ拡張結果のキャッシング
