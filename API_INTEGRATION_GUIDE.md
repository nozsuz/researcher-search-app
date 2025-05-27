# 🚀 API連携実装の完了手順

## 📁 プロジェクト構成

### researcher-search-app (バックエンド)
```
researcher-search-app/
├── api_endpoints.py       # ✅ 新しいAPIエンドポイント
├── researcher_search_app.py # 既存のStreamlitアプリ
├── requirements.txt       # ✅ FastAPI依存関係を追加
├── Procfile              # ✅ RailwayデプロイメントのためのProcfile
├── .env                  # 環境変数
└── runtime.txt           # Python バージョン
```

### research-partner-dashboard (フロントエンド)
```
research-partner-dashboard/
├── index.html            # ✅ API機能を統合
├── api-client.js         # ✅ 新しいAPIクライアント
├── config.js             # 既存の設定
└── vercel.json           # Vercelデプロイメント設定
```

## 🛠️ 次のデプロイメント手順

### ステップ1: バックエンドをRailwayにデプロイ

```bash
cd C:\Users\nozsu\researcher-search-app
git add .
git commit -m "Add FastAPI endpoints for direct API access"
git push origin main
```

**Railwayでの設定:**
1. Railway管理画面でプロジェクトを開く
2. Variables タブで以下を確認:
   - `PORT=8000`
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON=...` (既存)
   - その他のGCP環境変数
3. Deployments タブでデプロイ完了を確認
4. **重要**: デプロイ後のURLをメモ（例: `https://your-app-production-xxxx.up.railway.app`）

### ステップ2: フロントエンドのAPI URLを更新

デプロイ後、実際のRailway URLを取得して更新:

```javascript
// api-client.js の baseURL を実際のRailway URLに更新
this.baseURL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : 'https://【実際のRailway URL】';  // ← ここを更新
```

### ステップ3: フロントエンドをVercelにデプロイ

```bash
cd C:\Users\nozsu\research-partner-dashboard
git add .
git commit -m "Add API client for direct backend communication"
git push origin main
```

## 🔧 API連携機能の使用方法

### 1. APIで直接検索モード
- **🚀 APIで直接検索**ボタンをクリック
- 検索オプションを設定:
  - セマンティック検索 or キーワード検索
  - AIキーワード拡張（オプション）
  - AI関連性要約（オプション）
  - 最大表示件数（1-20件）
- キーワードを入力して「API検索実行」

### 2. 検索結果の表示
- 成功時: 研究者カードが表示され、スコアや要約も表示
- エラー時: エラーメッセージとトラブルシューティング情報を表示

### 3. API接続テスト
- **🚀 API連携デモ**ページでヘルスチェック
- 簡易検索テストで動作確認

## 🛡️ エラー対応

### よくあるエラーと対策

1. **CORS エラー**
   ```
   Access to fetch at 'https://...' from origin 'https://...' has been blocked by CORS policy
   ```
   → バックエンドのCORS設定を確認（api_endpoints.pyで設定済み）

2. **ネットワークエラー**
   ```
   TypeError: Failed to fetch
   ```
   → Railway URLが正しいかapi-client.jsで確認

3. **認証エラー**
   ```
   {"detail": "システムが初期化されていません"}
   ```
   → Railway環境変数（GCP認証情報）を確認

4. **タイムアウトエラー**
   → BigQueryクエリが重い場合があるため、maxResultsを少なくして試行

## 📊 API仕様

### エンドポイント一覧

#### GET /
- ヘルスチェック
- レスポンス: `{"message": "研究者検索API サーバー稼働中", "status": "healthy"}`

#### GET /health
- 詳細なヘルスチェック
- レスポンス: クライアント初期化状況と稼働情報

#### POST /api/search
- 研究者検索（メイン機能）
- リクエスト:
  ```json
  {
    "query": "人工知能",
    "method": "semantic", // "semantic" or "keyword"
    "max_results": 5,
    "use_llm_expansion": false,
    "use_llm_summary": false
  }
  ```
- レスポンス:
  ```json
  {
    "status": "success",
    "query": "人工知能",
    "method": "semantic",
    "results": [...],
    "total": 5,
    "execution_time": 2.34,
    "executed_query_info": "ベクトル次元: 768"
  }
  ```

#### GET /api/search
- GETパラメータ版（テスト用）
- パラメータ: query, method, max_results, use_llm_expansion, use_llm_summary

## 🎯 テスト手順

### ローカルテスト

1. **バックエンド起動**
   ```bash
   cd researcher-search-app
   python api_endpoints.py
   # → http://localhost:8000 で起動
   ```

2. **フロントエンド確認**
   ```bash
   cd research-partner-dashboard
   # ローカルサーバーで index.html を開く
   ```

3. **API接続テスト**
   - ブラウザで http://localhost:3000 (または適切なポート)
   - 「🚀 APIで直接検索」を選択
   - ヘルスチェックが🟢になることを確認
   - 「人工知能」で検索テスト

### 本番テスト

1. **Railway デプロイ確認**
   - https://【Railway URL】/health にアクセス
   - 正常なレスポンスが返ることを確認

2. **Vercel デプロイ確認**
   - フロントエンドにアクセス
   - API検索機能が動作することを確認

## 🔄 今後の拡張予定

### 追加予定機能
- [ ] 検索履歴の保存
- [ ] お気に入り研究者の管理
- [ ] バッチ検索（複数キーワード一括）
- [ ] エクスポート機能（CSV/PDF）
- [ ] 高度な検索フィルター

### パフォーマンス改善
- [ ] 検索結果のキャッシュ
- [ ] レスポンス圧縮
- [ ] ページネーション実装

## 📝 トラブルシューティング

### デプロイエラー

**Railway ビルドエラー**
```bash
# 依存関係の問題の場合
pip install -r requirements.txt  # ローカルでテスト
```

**Vercel デプロイエラー**
```bash
# 静的ファイルの問題の場合
vercel --prod  # 手動デプロイ
```

### ランタイムエラー

**BigQuery 接続エラー**
- GCP認証情報を確認
- BigQueryテーブルの存在を確認
- 権限設定を確認

**LLM API制限エラー**
- リクエスト頻度を下げる
- use_llm_summaryをfalseに設定

## 🎉 完了確認リスト

- [ ] バックエンドAPIが正常にデプロイ済み
- [ ] フロントエンドが正常にデプロイ済み
- [ ] API検索機能が動作する
- [ ] セマンティック検索が動作する
- [ ] キーワード検索が動作する
- [ ] エラーハンドリングが適切に機能する
- [ ] ヘルスチェックが正常に応答する

これですべてのAPI連携機能が完成です！🚀