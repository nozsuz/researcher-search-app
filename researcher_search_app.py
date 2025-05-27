import streamlit as st
import pandas as pd
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from vertexai.language_models import TextEmbeddingModel
import os
import time
import json
from google.oauth2 import service_account

# ページ設定
st.set_page_config(
    page_title="🔬 研究者検索アプリ（デュアルモデル版）",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",  # iframe内での表示を最適化
)

# セッション状態の初期化
if 'initialized' not in st.session_state:
    st.session_state.initialized = False

# 設定定数
PROJECT_ID = os.getenv("PROJECT_ID", "apt-rope-217206")
LOCATION = os.getenv("LOCATION", "us-central1")
BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE", "apt-rope-217206.researcher_data.rd_250524")
MAIN_LLM_MODEL_NAME = os.getenv("MAIN_LLM_MODEL_NAME", "gemini-2.0-flash-001")
SUMMARY_LLM_MODEL_NAME = os.getenv("SUMMARY_LLM_MODEL_NAME", "gemini-2.0-flash-lite-001")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-multilingual-embedding-002")

# 検索対象カラム
SEARCH_TARGET_COLUMNS_KEYWORD = [
    'name_ja', 'name_en', 'research_keywords_ja', 'research_keywords_en',
    'research_fields_ja', 'research_fields_en', 'profile_ja',
    'paper_title_ja_first', 'paper_title_en_first',
    'project_title_ja_first', 'project_title_en_first'
]

DISPLAY_COLUMNS = [
    'name_ja', 'name_en', 'main_affiliation_name_ja', 'main_affiliation_name_en',
    'research_keywords_ja', 'research_fields_ja', 'profile_ja',
    'paper_title_ja_first', 'project_title_ja_first', 'researchmap_url'
]

@st.cache_resource
def initialize_clients():
    """Google Cloud クライアントの初期化（キャッシュ化）"""
    try:
        # Google Cloud認証の設定
        credentials = None
        
        # 方法1: 環境変数からJSON文字列を取得
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
            try:
                credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
                
                # デバッグ：JSON文字列の詳細確認
                json_length = len(credentials_json)
                json_preview = credentials_json[:50] + "..." + credentials_json[-50:]
                st.write(f"📊 JSON長さ: {json_length} 文字")
                st.write(f"📋 JSON プレビュー: {json_preview}")
                
                # 不要な引用符の除去（三重引用符対応）
                credentials_json = credentials_json.strip()
                if credentials_json.startswith('"""') and credentials_json.endswith('"""'):
                    credentials_json = credentials_json[3:-3]
                    st.info("🔧 三重引用符を削除しました")
                elif credentials_json.startswith('"') and credentials_json.endswith('"'):
                    credentials_json = credentials_json[1:-1]
                    st.info("🔧 引用符を削除しました")
                
                # JSON形式の基本チェック
                credentials_json = credentials_json.strip()
                if not credentials_json.startswith('{') or not credentials_json.endswith('}'):
                    st.error("❌ JSON形式エラー: 開始または終了括弧が不正です")
                    st.write(f"開始文字: '{credentials_json[:10]}'")
                    st.write(f"終了文字: '{credentials_json[-10:]}'")
                    return None, None, None, None
                
                # 改行文字の処理
                # \\n → \n の変換（Streamlit Secrets形式と同じ）
                if '\\n' in credentials_json:
                    credentials_json = credentials_json.replace('\\n', '\n')
                    st.info("🔧 改行文字を変換しました (\\\\n → \\n)")
                
                # JSONパース
                credentials_dict = json.loads(credentials_json)
                
                # 必須フィールドの確認
                required_fields = ['type', 'project_id', 'private_key', 'client_email']
                missing_fields = [field for field in required_fields if field not in credentials_dict]
                if missing_fields:
                    st.error(f"❌ 必須フィールドが不足: {missing_fields}")
                    return None, None, None, None
                
                # private_keyの形式確認
                private_key = credentials_dict.get('private_key', '')
                if '-----BEGIN PRIVATE KEY-----' not in private_key:
                    st.error("❌ private_keyの形式が不正です")
                    return None, None, None, None
                
                # 認証情報の作成
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=[
                        "https://www.googleapis.com/auth/cloud-platform",
                        "https://www.googleapis.com/auth/bigquery"
                    ]
                )
                st.success("✅ 環境変数から認証情報を読み込みました")
                st.write(f"🏢 プロジェクトID: {credentials_dict.get('project_id')}")
                st.write(f"📧 サービスアカウント: {credentials_dict.get('client_email')}")
                
            except json.JSONDecodeError as je:
                st.error(f"❌ JSONパースエラー: {je}")
                st.write("💡 JSONの形式を確認してください（改行、引用符、カンマなど）")
                # エラー箇所を表示
                if hasattr(je, 'pos') and os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON'):
                    error_context = credentials_json[max(0, je.pos-30):je.pos+30]
                    st.code(f"エラー箇所付近: ...{error_context}...")
                return None, None, None, None
            except Exception as e:
                st.error(f"❌ 認証情報読み込みエラー: {e}")
                return None, None, None, None
        
        # 方法2: 秘密鍵を別の環境変数で設定
        elif all([os.getenv("GCP_PROJECT_ID"), os.getenv("GCP_PRIVATE_KEY"), os.getenv("GCP_CLIENT_EMAIL")]):
            try:
                import base64
                # Base64デコードした秘密鍵を使用
                private_key = base64.b64decode(os.getenv("GCP_PRIVATE_KEY")).decode('utf-8')
                
                credentials_dict = {
                    "type": "service_account",
                    "project_id": os.getenv("GCP_PROJECT_ID"),
                    "private_key_id": os.getenv("GCP_PRIVATE_KEY_ID", ""),
                    "private_key": private_key,
                    "client_email": os.getenv("GCP_CLIENT_EMAIL"),
                    "client_id": os.getenv("GCP_CLIENT_ID", ""),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "universe_domain": "googleapis.com"
                }
                
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=[
                        "https://www.googleapis.com/auth/cloud-platform",
                        "https://www.googleapis.com/auth/bigquery"
                    ]
                )
                st.success("✅ 分割した環境変数から認証情報を読み込みました")
            except Exception as e:
                st.error(f"分割環境変数からの認証情報読み込みエラー: {e}")
        
        # Vertex AI 初期化
        if credentials:
            vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)
        else:
            vertexai.init(project=PROJECT_ID, location=LOCATION)
        
        # BigQuery クライアント初期化
        if credentials:
            bq_client = bigquery.Client(project=PROJECT_ID, credentials=credentials)
        else:
            bq_client = bigquery.Client(project=PROJECT_ID)
        
        # LLM モデル初期化
        main_llm_model = GenerativeModel(MAIN_LLM_MODEL_NAME)
        summary_llm_model = GenerativeModel(SUMMARY_LLM_MODEL_NAME)
        
        # エンベディングモデル初期化
        embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_NAME)
        
        return bq_client, main_llm_model, summary_llm_model, embedding_model
    except Exception as e:
        st.error(f"初期化エラー: {e}")
        # デバッグ情報を表示
        st.write("**デバッグ情報:**")
        st.write(f"PROJECT_ID: {PROJECT_ID}")
        st.write(f"LOCATION: {LOCATION}")
        st.write(f"GOOGLE_APPLICATION_CREDENTIALS_JSON が設定されているか: {'Yes' if os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON') else 'No'}")
        if os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON'):
            json_preview = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')[:100] + "..."
            st.write(f"JSONプレビュー: {json_preview}")
        if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            st.write(f"GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
        return None, None, None, None

def test_permissions(bq_client, embedding_model):
    """権限テスト用の関数"""
    st.write("## 🔍 権限テスト")
    
    # BigQuery権限テスト
    try:
        # シンプルなクエリでテーブルアクセスをテスト
        test_query = f"SELECT COUNT(*) as total_records FROM `{BIGQUERY_TABLE}` LIMIT 1"
        result = bq_client.query(test_query).to_dataframe()
        st.success(f"✅ BigQueryアクセス成功: {result['total_records'].iloc[0]:,}件のレコード")
    except Exception as e:
        st.error(f"❌ BigQueryアクセスエラー: {e}")
    
    # Vertex AI 権限テスト
    try:
        # シンプルなエンベディングテスト
        test_embedding = embedding_model.get_embeddings(["テスト"])
        if test_embedding and len(test_embedding) > 0:
            st.success(f"✅ Vertex AIアクセス成功: エンベディング次元数 {len(test_embedding[0].values)}")
        else:
            st.error("❌ Vertex AI: エンベディング取得失敗")
    except Exception as e:
        st.error(f"❌ Vertex AIアクセスエラー: {e}")
    
    st.write("---")

def expand_keywords_with_llm(original_keyword, model, search_target_columns_hint=""):
    """メインLLMを使って検索キーワードを拡張する"""
    if not model:
        return [original_keyword]
    try:
        columns_hint_text = ""
        if search_target_columns_hint:
            columns_hint_text = f"特に以下の情報源に関連するキーワードを意識してください: {search_target_columns_hint}"

        prompt = f"""
        あなたは学術研究データベースの検索アシスタントです。
        ユーザーが入力した「元のキーワード」について、そのキーワードを含む研究情報をより効果的に見つけるために、
        関連性の高い類義語、上位/下位概念語、英語の対応語（もしあれば）、具体的な技術名や物質名などを考慮し、
        検索に有効そうなキーワードを最大10個提案してください。
        {columns_hint_text}
        提案は日本語の単語または短いフレーズで、カンマ区切りで出力してください。元のキーワード自体も提案に含めてください。

        元のキーワード: 「{original_keyword}」

        提案:
        """
        response = model.generate_content(
            [Part.from_text(prompt)],
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 200
            }
        )
        if response.candidates and response.candidates[0].content.parts:
            expanded_text = response.candidates[0].content.parts[0].text
            expanded = [kw.strip() for kw in expanded_text.split(',') if kw.strip()]
            # 重複を削除しつつ順序をある程度保持し、元のキーワードがなければ先頭に追加
            final_keywords = []
            if original_keyword not in expanded:
                final_keywords.append(original_keyword)
            for kw in expanded:
                if kw not in final_keywords:
                    final_keywords.append(kw)
            return final_keywords
        else:
            st.warning("キーワード拡張でLLMから期待した形式のレスポンスが得られませんでした。")
            return [original_keyword]
    except Exception as e:
        st.error(f"キーワード拡張中にエラーが発生しました: {e}")
        return [original_keyword]

def get_embedding(text_content, model):
    """指定されたテキストのエンベディングを取得する (多言語対応)"""
    if not model or not text_content:
        st.error("エンベディングモデルが利用不可か、テキストが空です。")
        return None

    try:
        response = model.get_embeddings([text_content])
        if response and len(response) > 0:
            return response[0].values
        else:
            st.error("エンベディング取得でモデルから期待した形式のレスポンスが得られませんでした。")
            return None
    except Exception as e:
        st.error(f"エンベディング取得中にエラーが発生しました: {e}")
        return None

def summarize_researcher_profile_llm_lite(researcher_data, query, model):
    """軽量LLMを使って研究者の情報を検索クエリとの関連で要約する（レート制限対策版）"""
    if not model:
        return "軽量LLMモデルが利用できません。"
    try:
        # シンプルなプロンプトでトークン数を削減
        name = researcher_data.get('name_ja', '')
        affiliation = researcher_data.get('main_affiliation_name_ja', '')
        keywords = researcher_data.get('research_keywords_ja', '')
        profile = str(researcher_data.get('profile_ja', ''))[:200]  # 短縮

        prompt = f"""
        検索クエリ: 「{query}」
        研究者: {name} ({affiliation})
        研究キーワード: {keywords}
        プロフィール概要: {profile}

        この研究者と検索クエリとの関連性を200字以内で簡潔に説明してください:
        """

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 200
            }
        )
        if response.candidates and response.candidates[0].content.parts:
            return response.candidates[0].content.parts[0].text.strip()
        else:
            return "軽量LLMによる要約中にエラーが発生しました。"

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Resource exhausted" in error_msg:
            return "⚠️ API制限のため要約をスキップしました（軽量モデル使用中）"
        else:
            return f"軽量LLM要約エラー: {error_msg}"

def search_researchers_in_bigquery_where_clause(search_terms_list, target_columns, bq_client, max_results=10):
    """BigQueryでキーワード検索 (SEARCH関数修正版)"""
    if not search_terms_list or not target_columns:
        return pd.DataFrame(), ""

    safe_bigquery_table = f"`{BIGQUERY_TABLE.replace('`', '')}`"

    # 検索タームの処理
    processed_terms = ['"' + term.replace('"', '') + '"' for term in search_terms_list if term.strip()]
    if not processed_terms:
        st.error("有効な検索タームがありません。")
        return pd.DataFrame(), ""
    search_query_for_search_function = " OR ".join(processed_terms)

    where_conditions = [f"SEARCH({col}, @search_text)" for col in target_columns]

    # 関連度スコアを手動計算
    sql_query_final = f"""
    SELECT
        {', '.join(DISPLAY_COLUMNS)},
        (
          CASE WHEN SEARCH(name_ja, @search_text) THEN 10 ELSE 0 END +
          CASE WHEN SEARCH(name_en, @search_text) THEN 10 ELSE 0 END +
          CASE WHEN SEARCH(research_keywords_ja, @search_text) THEN 8 ELSE 0 END +
          CASE WHEN SEARCH(research_keywords_en, @search_text) THEN 8 ELSE 0 END +
          CASE WHEN SEARCH(research_fields_ja, @search_text) THEN 6 ELSE 0 END +
          CASE WHEN SEARCH(research_fields_en, @search_text) THEN 6 ELSE 0 END +
          CASE WHEN SEARCH(profile_ja, @search_text) THEN 4 ELSE 0 END +
          CASE WHEN SEARCH(paper_title_ja_first, @search_text) THEN 5 ELSE 0 END +
          CASE WHEN SEARCH(paper_title_en_first, @search_text) THEN 5 ELSE 0 END +
          CASE WHEN SEARCH(project_title_ja_first, @search_text) THEN 5 ELSE 0 END +
          CASE WHEN SEARCH(project_title_en_first, @search_text) THEN 5 ELSE 0 END
        ) AS relevance_score
    FROM
        {safe_bigquery_table}
    WHERE
        {' OR '.join(where_conditions)}
    ORDER BY
        relevance_score DESC
    LIMIT @limit_param
    """

    try:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("search_text", "STRING", search_query_for_search_function),
                bigquery.ScalarQueryParameter("limit_param", "INT64", max_results),
            ]
        )
        
        df = bq_client.query(sql_query_final, job_config=job_config).to_dataframe()
        return df, search_query_for_search_function
    except Exception as e:
        st.error(f"BigQueryキーワード検索中にエラーが発生しました: {e}")
        return pd.DataFrame(), search_query_for_search_function

def search_researchers_semantic(query_embedding, embedding_column_name, bq_client, max_results=10):
    """BigQueryでセマンティック検索 (VECTOR_SEARCH関数) - ネスト構造対応版"""
    if query_embedding is None or not embedding_column_name:
        st.error("クエリエンベディングまたはカラム名が不正です。")
        return pd.DataFrame()

    # 次元数を768に調整（テーブルのエンベディング次元数に合わせる）
    expected_dimensions = 768
    if len(query_embedding) != expected_dimensions:
        st.info(f"次元数調整: {len(query_embedding)} → {expected_dimensions}")
        if len(query_embedding) > expected_dimensions:
            query_embedding = query_embedding[:expected_dimensions]
        else:
            query_embedding = query_embedding + [0.0] * (expected_dimensions - len(query_embedding))

    query_embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    sql_query_semantic = f"""
    SELECT
      *
    FROM
      VECTOR_SEARCH(
        (SELECT * FROM `{BIGQUERY_TABLE.replace('`', '')}`
         WHERE ARRAY_LENGTH({embedding_column_name}) > 0),
        '{embedding_column_name}',
        (SELECT {query_embedding_str} AS query_vector),
        top_k => @top_k_param,
        distance_type => 'COSINE'
      )
    ORDER BY distance ASC
    """

    try:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("top_k_param", "INT64", max_results),
            ]
        )
        
        df = bq_client.query(sql_query_semantic, job_config=job_config).to_dataframe()

        if len(df) > 0:
            # ネスト構造を展開
            expanded_rows = []
            for idx, row in df.iterrows():
                new_row = {}
                # distance は直接コピー
                new_row['distance'] = row.get('distance')
                # base カラムから実際のデータを抽出
                base_data = row.get('base', {})
                if isinstance(base_data, dict):
                    for key, value in base_data.items():
                        new_row[key] = value
                expanded_rows.append(new_row)
            
            expanded_df = pd.DataFrame(expanded_rows)
            return expanded_df
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"BigQueryセマンティック検索中にエラーが発生しました: {e}")
        return pd.DataFrame()

def display_search_results(df, original_query, executed_search_query_info, search_method, use_llm_summary, summary_model):
    """検索結果表示関数"""
    if df.empty:
        st.warning("該当する研究者は見つかりませんでした。")
        return

    query_info_str = f"`{executed_search_query_info}`" if executed_search_query_info else ""
    st.success(f"「{original_query}」({search_method}結果 {query_info_str}): {len(df)}件")

    for index, row in df.iterrows():
        # 安全な値取得関数
        def safe_get(column_name, default='N/A'):
            value = row.get(column_name)
            if pd.isna(value) or value is None:
                return default
            str_val = str(value).strip()
            return str_val if str_val else default

        # 各値を安全に取得
        name_ja = safe_get('name_ja')
        affiliation = safe_get('main_affiliation_name_ja')
        keywords = safe_get('research_keywords_ja')
        fields = safe_get('research_fields_ja')
        profile = safe_get('profile_ja')
        paper = safe_get('paper_title_ja_first')
        project = safe_get('project_title_ja_first')

        # スコア表示
        score_text = ""
        if search_method == 'キーワード検索' and 'relevance_score' in row and pd.notna(row['relevance_score']):
            score_text = f" (関連度: {row['relevance_score']:.0f})"
        elif search_method == 'セマンティック検索' and 'distance' in row and pd.notna(row['distance']):
            score_text = f" (距離: {row['distance']:.4f})"

        # URL処理
        researchmap_url = safe_get('researchmap_url', '#')
        if researchmap_url == 'N/A':
            researchmap_url = safe_get('permalink', '#')

        with st.expander(f"👨‍🔬 {name_ja} ({affiliation}){score_text}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if keywords != 'N/A':
                    st.write(f"**研究キーワード:** {keywords}")
                if fields != 'N/A':
                    st.write(f"**研究分野:** {fields}")
                if profile != 'N/A':
                    profile_short = profile[:200] + "..." if len(profile) > 200 else profile
                    st.write(f"**プロフィール:** {profile_short}")
                if paper != 'N/A':
                    st.write(f"**主要論文:** {paper}")
                if project != 'N/A':
                    st.write(f"**主要プロジェクト:** {project}")
            
            with col2:
                if researchmap_url != '#':
                    st.link_button("ResearchMapで詳細を見る", researchmap_url)

            # 軽量LLM要約の処理
            if use_llm_summary and summary_model:
                with st.spinner("⚡ 軽量LLMによる関連性分析中..."):
                    time.sleep(0.5)  # レート制限対策
                    try:
                        summary = summarize_researcher_profile_llm_lite(row.to_dict(), original_query, summary_model)
                        st.info(f"**⚡ 軽量LLM分析 ({SUMMARY_LLM_MODEL_NAME}):** {summary}")
                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg or "Resource exhausted" in error_msg:
                            st.warning("⚠️ 軽量モデルもAPI制限: しばらく待ってから再試行してください。")
                        else:
                            st.error(f"軽量LLM要約エラー: {error_msg}")

# メインアプリ
def main():
    st.title("🔬 研究者検索アプリ（デュアルモデル版）")
    st.markdown("---")
    
    # 初期化
    if not st.session_state.initialized:
        with st.spinner("🔄 システムを初期化中..."):
            bq_client, main_llm_model, summary_llm_model, embedding_model = initialize_clients()
            if all([bq_client, main_llm_model, summary_llm_model, embedding_model]):
                st.session_state.bq_client = bq_client
                st.session_state.main_llm_model = main_llm_model
                st.session_state.summary_llm_model = summary_llm_model
                st.session_state.embedding_model = embedding_model
                st.session_state.initialized = True
                st.success("✅ 初期化完了！")
                
                # 権限テストを実行
                with st.expander("🔍 権限テスト結果を表示"):
                    test_permissions(bq_client, embedding_model)
            else:
                st.error("❌ 初期化に失敗しました。設定を確認してください。")
                return
    
    # サイドバー設定
    st.sidebar.header("🔧 検索設定")
    
    # モデル情報表示
    with st.sidebar.expander("🧠 使用モデル情報"):
        st.write(f"**メインLLM:** {MAIN_LLM_MODEL_NAME}")
        st.write(f"**軽量要約:** {SUMMARY_LLM_MODEL_NAME}")
        st.write(f"**エンベディング:** {EMBEDDING_MODEL_NAME}")
    
    search_method = st.sidebar.selectbox(
        "検索方法",
        options=["セマンティック検索", "キーワード検索"],
        index=0,  # セマンティック検索をデフォルトに
        help="セマンティック検索: 意味的類似性、キーワード検索: 完全一致・部分一致"
    )
    
    use_llm_expansion = st.sidebar.checkbox(
        "🧠 LLMでキーワードを拡張する", 
        value=False,  # セマンティック検索がデフォルトなのでFalse
        disabled=search_method == "セマンティック検索",
        help="メインLLMを使用してキーワードを拡張（キーワード検索時のみ）"
    )
    
    use_llm_summary = st.sidebar.checkbox(
        "⚡ 軽量LLMで関連性を要約する", 
        value=False,
        help="軽量LLMを使用して各研究者との関連性を分析（API制限対策済み）"
    )
    
    max_results = st.sidebar.slider("最大表示件数", min_value=1, max_value=20, value=5)
    
    # 検索フォーム
    col1, col2 = st.columns([4, 1])
    with col1:
        search_query = st.text_input(
            "🔍 検索キーワード", 
            value="ナノ材料", 
            placeholder="例: 人工知能、再生医療、がん治療"
        )
    with col2:
        search_button = st.button("🚀 検索開始", type="primary", use_container_width=True)
    
    # 検索実行
    if search_button and search_query.strip():
        start_time = time.time()
        
        with st.spinner(f"🔍 {search_method}を実行中..."):
            if search_method == "キーワード検索":
                search_terms = [search_query.strip()]
                search_target_cols_hint = ', '.join(SEARCH_TARGET_COLUMNS_KEYWORD)

                if use_llm_expansion:
                    with st.status("🧠 メインLLMによるキーワード拡張...") as status:
                        expanded_keywords = expand_keywords_with_llm(
                            search_query, 
                            st.session_state.main_llm_model, 
                            search_target_cols_hint
                        )
                        if set(expanded_keywords) != {search_query}:
                            st.info(f"✅ 拡張されたキーワード: {', '.join(expanded_keywords)}")
                            search_terms = expanded_keywords
                        else:
                            st.info("ℹ️ 新たなキーワードは生成されませんでした。")
                        status.update(label="🧠 キーワード拡張完了", state="complete")

                # キーワード検索実行
                results_df, executed_query_info = search_researchers_in_bigquery_where_clause(
                    search_terms,
                    target_columns=SEARCH_TARGET_COLUMNS_KEYWORD,
                    bq_client=st.session_state.bq_client,
                    max_results=max_results
                )

            elif search_method == "セマンティック検索":
                # エンベディング生成
                query_emb = get_embedding(search_query, st.session_state.embedding_model)
                
                if query_emb:
                    # セマンティック検索実行
                    results_df = search_researchers_semantic(
                        query_emb,
                        embedding_column_name="embedding",
                        bq_client=st.session_state.bq_client,
                        max_results=max_results
                    )
                    executed_query_info = f"クエリベクトル次元: {len(query_emb)}"
                else:
                    st.error("❌ エンベディング生成に失敗しました。")
                    return

        # 結果表示
        display_search_results(
            results_df, 
            search_query, 
            executed_query_info, 
            search_method, 
            use_llm_summary, 
            st.session_state.summary_llm_model
        )
        
        end_time = time.time()
        st.caption(f"⏱️ 検索処理時間: {end_time - start_time:.2f} 秒")

    # 使用方法の説明
    with st.expander("📖 使用方法とヒント"):
        st.markdown("""
        ### 🔍 検索方法の選択
        - **セマンティック検索（推奨）**: AIによる意味的類似性検索
        - **キーワード検索**: 完全一致・部分一致による高精度検索
        
        ### 🧠 LLM機能
        - **キーワード拡張**: メインLLMが関連キーワードを自動生成
        - **関連性要約**: 軽量LLMが各研究者との関連性を分析
        
        ### 💡 検索のコツ
        - セマンティック検索で「ナノ材料」「人工知能」「がん治療」を試してみてください
        - キーワード検索では具体的な技術名や専門用語が効果的です
        - LLM要約機能でより詳細な関連性分析が可能です
        """)

if __name__ == "__main__":
    main()