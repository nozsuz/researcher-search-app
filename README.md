# 研究者検索アプリケーション

AI技術を活用した研究者検索システム

## 概要

このアプリケーションは、BigQuery と Vertex AI を使用して、研究者情報を効率的に検索・評価するシステムです。

## 主な機能

### 1. 検索機能
- **セマンティック検索**: ベクトル埋め込みを使用した意味的な類似性に基づく検索
- **キーワード検索**: 従来型の全文検索
- **クエリ拡張**: LLMを使用して検索クエリを自動的に拡張

### 2. 評価システム（新機能）
- **内部評価モード**: 7つの観点から研究者と検索クエリの関連性を数値評価
  - キーワード一致度
  - 研究の直接性
  - 専門性の深さ
  - 具体的実績
  - 研究の質
  - 学際性
  - 研究の最新性
- **総合スコア**: 1-10のスケールで関連度を表示
- **要約生成**: 各研究者の強みを簡潔に表示

### 3. LLM統合
- **要約生成**: 検索結果に対してAIが関連性の説明を生成
- **バッチ処理**: 効率的な評価のための一括処理

## API エンドポイント

### 基本エンドポイント
- `GET /`: ヘルスチェック
- `GET /health`: 詳細なシステムステータス

### 検索エンドポイント
- `POST /api/search`: 研究者検索（メイン）
- `GET /api/search`: 研究者検索（テスト用）

### テストエンドポイント
- `GET /test/gcp`: GCP接続テスト
- `GET /test/llm`: LLM機能テスト
- `GET /test/evaluation-mode`: 内部評価モードテスト

## 使用方法

### 基本的な検索
```bash
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "人工知能",
    "method": "keyword",
    "max_results": 5
  }'
```

### 内部評価モードを使用した検索
```bash
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ナノメートルの微細加工技術",
    "method": "keyword",
    "max_results": 10,
    "use_internal_evaluation": true
  }'
```

### パラメータ説明
- `query`: 検索クエリ（必須）
- `method`: 検索方法（"semantic" または "keyword"）
- `max_results`: 最大結果数（1-20）
- `use_llm_expansion`: LLMによるクエリ拡張（true/false）
- `use_llm_summary`: LLMによる要約生成（true/false）
- `use_internal_evaluation`: 内部評価モード（true/false）

## 環境設定

### 必要な環境変数
```bash
# GCPプロジェクト設定
PROJECT_ID=your-project-id
LOCATION=us-central1
BIGQUERY_TABLE=your-dataset.your-table

# GCP認証情報
GCP_SERVICE_ACCOUNT_EMAIL=your-service-account@project.iam.gserviceaccount.com
GCP_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
GCP_PRIVATE_KEY_ID=your-key-id
GCP_CLIENT_ID=your-client-id
GCP_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...

# 機能フラグ
ENABLE_GCP_INITIALIZATION=true
```

## インストール

```bash
# リポジトリのクローン
git clone https://github.com/yourusername/researcher-search-app.git
cd researcher-search-app

# 依存関係のインストール
pip install -r requirements.txt

# アプリケーションの起動
python main.py
```

## 開発

### プロジェクト構造
```
researcher-search-app/
├── main.py                         # FastAPIアプリケーション
├── real_search_with_evaluation.py  # 検索・評価機能
├── evaluation_system.py            # 評価システム
├── gcp_auth.py                     # GCP認証
├── requirements.txt                # 依存関係
└── README.md                       # このファイル
```

### テスト実行
```bash
# 基本的な動作確認
curl http://localhost:8000/

# GCP接続テスト
curl http://localhost:8000/test/gcp

# 評価モードテスト
curl http://localhost:8000/test/evaluation-mode
```

## デプロイ

このアプリケーションは Railway や他のクラウドプラットフォームにデプロイ可能です。

### Railway でのデプロイ
1. Railway プロジェクトを作成
2. 環境変数を設定
3. GitHub リポジトリを接続
4. 自動デプロイを有効化

## ライセンス

[ライセンス情報を追加]

## 貢献

[貢献ガイドラインを追加]
