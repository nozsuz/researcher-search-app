# Railway環境変数設定ガイド

## 🔧 必要な環境変数

Railwayダッシュボードで以下の環境変数を設定してください。

### 基本設定（必須）

```bash
# プロジェクトID
PROJECT_ID=apt-rope-217206

# リージョン
LOCATION=us-central1

# BigQueryテーブル
BIGQUERY_TABLE=apt-rope-217206.researcher_data.rd_250524

# GCP初期化を有効化（実際の検索を使用する場合）
ENABLE_GCP_INITIALIZATION=false
```

### GCP認証情報（実際の検索を使用する場合のみ）

#### 方法1: 個別の環境変数（推奨）

```bash
# サービスアカウントのメールアドレス
GCP_SERVICE_ACCOUNT_EMAIL=your-service-account@apt-rope-217206.iam.gserviceaccount.com

# プライベートキー（改行は\nで表現）
GCP_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nMIIEv...\n-----END PRIVATE KEY-----

# プライベートキーID
GCP_PRIVATE_KEY_ID=your-private-key-id

# クライアントID
GCP_CLIENT_ID=your-client-id

# 証明書URL
GCP_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40apt-rope-217206.iam.gserviceaccount.com
```

#### 方法2: JSON形式（代替）

```bash
# サービスアカウントキーのJSON全体
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account","project_id":"apt-rope-217206",...}
```

#### 方法3: Base64形式（代替）

```bash
# Base64エンコードされたサービスアカウントキー
GOOGLE_APPLICATION_CREDENTIALS_BASE64=ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIs...
```

## 📋 設定手順

### 1. Railwayダッシュボードにログイン
https://railway.app にアクセスしてログイン

### 2. プロジェクトを選択
`researcher-search-app` プロジェクトを選択

### 3. Variables タブに移動
プロジェクトの設定から Variables タブを開く

### 4. 環境変数を追加
上記の環境変数を一つずつ追加

### 5. デプロイを再実行
環境変数を設定後、自動的に再デプロイされます

## 🔍 動作モード

### モックモード（デフォルト）
```bash
ENABLE_GCP_INITIALIZATION=false
```
- GCP認証不要
- サンプルデータを返す
- 開発・デモ用

### 本番モード
```bash
ENABLE_GCP_INITIALIZATION=true
# + GCP認証情報の設定
```
- BigQueryから実際のデータを検索
- Vertex AIを使用したセマンティック検索
- LLMによるクエリ拡張と要約

## ✅ 動作確認

### 1. ヘルスチェック
```bash
curl https://researcher-search-app-production.up.railway.app/health
```

期待される応答（モックモード）:
```json
{
  "status": "healthy",
  "clients_status": {
    "initialized": false,
    "bigquery": "🔄 準備中",
    "vertex_ai": "🔄 準備中"
  }
}
```

### 2. 検索テスト
```bash
curl -X POST https://researcher-search-app-production.up.railway.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "人工知能", "method": "keyword", "max_results": 5}'
```

## 🚨 トラブルシューティング

### エラー: 認証情報が見つかりません
- 環境変数が正しく設定されているか確認
- プライベートキーの改行が`\n`で表現されているか確認

### エラー: BigQuery接続失敗
- PROJECT_IDとBIGQUERY_TABLEが正しいか確認
- サービスアカウントにBigQueryの権限があるか確認

### エラー: Vertex AI初期化失敗
- LOCATIONが正しいか確認
- サービスアカウントにVertex AIの権限があるか確認

## 📝 注意事項

1. **セキュリティ**: プライベートキーは絶対に公開しないでください
2. **コスト**: 本番モードではGCPの使用料金が発生します
3. **レート制限**: Vertex AIのAPIにはレート制限があります
4. **デフォルト**: 安全のため、デフォルトはモックモードです
