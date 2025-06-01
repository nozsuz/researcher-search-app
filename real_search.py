"""
実際の研究者検索機能（評価システム統合版）
BigQuery + Vertex AI + 評価システムを使用した本格的な検索システム
"""

import logging
import time
from typing import Dict, List, Optional, Any
from google.cloud import bigquery
from vertexai.language_models import TextGenerationModel, TextEmbeddingModel
from vertexai.generative_models import GenerativeModel
import numpy as np
from evaluation_system import UniversalResearchEvaluator

logger = logging.getLogger(__name__)

# 評価システムのインスタンスをグローバルに保持
evaluator = UniversalResearchEvaluator()

async def perform_real_search(request) -> Dict[str, Any]:
    """
    実際の研究者検索を実行（評価システム統合版）
    """
    start_time = time.time()
    
    try:
        logger.info(f"🔍 実際の検索開始: {request.query}, method: {request.method}")
        logger.info(f"📊 全パラメータ: query={request.query}, method={request.method}, max_results={request.max_results}, use_llm_expansion={request.use_llm_expansion}, use_llm_summary={request.use_llm_summary}, use_internal_evaluation={getattr(request, 'use_internal_evaluation', 'NONE')}")
        
        # 内部評価モードの設定を確認
        use_internal_evaluation = getattr(request, 'use_internal_evaluation', False)
        logger.info(f"📊 評価モード: {'内部評価' if use_internal_evaluation else '従来方式'}")
        logger.info(f"🔍 リクエストオブジェクト: {request}")
        logger.info(f"🔍 use_internal_evaluation値: {use_internal_evaluation}")
        logger.info(f"🔍 リクエスト属性: {dir(request)}")
        
        # GCPクライアントを取得
        from gcp_auth import get_bigquery_client, is_vertex_ai_ready
        
        bq_client = get_bigquery_client()
        if not bq_client:
            raise Exception("BigQueryクライアントが利用できません")
        
        # Vertex AIが必要な機能のチェック
        vertex_ai_required = request.method == "semantic" or request.use_llm_expansion or request.use_llm_summary
        vertex_ai_available = is_vertex_ai_ready()
        
        if vertex_ai_required and not vertex_ai_available:
            logger.warning("⚠️ Vertex AIが利用できません。代替手法を使用します。")
            # Vertex AIが必要な機能を無効化
            if request.method == "semantic":
                logger.info("🔄 セマンティック検索 → 高度キーワード検索に変更")
                request.method = "keyword"
            request.use_llm_expansion = False
            request.use_llm_summary = False
        
        # セマンティック検索時はクエリ拡張を無効化
        if request.method == "semantic":
            request.use_llm_expansion = False
            logger.info("🔄 セマンティック検索時はクエリ拡張を無効化")
        
        # 検索クエリの前処理
        search_query = request.query.strip()
        expanded_info = None  # 拡張情報を保存
        
        if request.use_llm_expansion and vertex_ai_available:
            try:
                expansion_result = await expand_query_with_llm(search_query)
                if expansion_result:
                    expanded_info = {
                        "original_query": expansion_result["original_query"],
                        "expanded_keywords": expansion_result["expanded_keywords"],
                        "expanded_query": expansion_result["expanded_query"]
                    }
                    # 検索用には拡張されたクエリを使用
                    search_query = expansion_result["expanded_query"]
                    logger.info(f"🔄 LLMクエリ拡張結果: {search_query}")
                    logger.info(f"🧠 拡張キーワード: {expansion_result['expanded_keywords']}")
                else:
                    logger.info("🔄 LLMクエリ拡張: 変更なし")
            except Exception as e:
                logger.warning(f"⚠️ LLMクエリ拡張失敗: {e}")
                search_query = request.query.strip()
        
        # 検索方法に応じて実行
        if request.method == "semantic" and vertex_ai_available:
            results = await semantic_search_with_embedding(bq_client, search_query, request.max_results)
        else:  # keyword
            results = await keyword_search(bq_client, search_query, request.max_results)
        
        logger.info(f"📊 検索結果: {len(results)}件")
        
        # 評価システムによる処理
        if use_internal_evaluation and results:
            try:
                # 内部評価モードで研究者を評価
                evaluations = await evaluator.evaluate_researchers(
                    results, 
                    request.query,  # 元のクエリを使用
                    use_internal_evaluation=True
                )
                
                # UI用にフォーマット
                formatted_result = evaluator.format_for_ui(evaluations, request.max_results)
                
                execution_time = time.time() - start_time
                
                # 内部評価モードのレスポンス
                return {
                    "status": "success",
                    "query": request.query,
                    "method": request.method,
                    "evaluation_mode": "internal",
                    "summary": formatted_result["summary"],
                    "results": [],  # 従来形式の結果は空
                    "evaluated_results": formatted_result["results"],  # 評価済み結果
                    "total": formatted_result["metadata"]["total_found"],
                    "displayed": formatted_result["metadata"]["displayed"],
                    "execution_time": execution_time,
                    "executed_query_info": f"内部評価モード実行 (方法: {request.method}, 実行時間: {execution_time:.2f}秒)",
                    "expanded_info": expanded_info
                }
                
            except Exception as e:
                logger.error(f"❌ 内部評価モードでエラー: {e}")
                import traceback
                logger.error(f"スタックトレース: {traceback.format_exc()}")
                # エラー時は従来方式にフォールバック
                use_internal_evaluation = False
        
        # 従来方式の処理
        if not use_internal_evaluation:
            # LLM要約の生成（従来方式）
            if request.use_llm_summary and results and vertex_ai_available:
                try:
                    results = await add_llm_summaries(results, request.query)  # 元のクエリを使用
                    logger.info("🤖 LLM要約を追加完了")
                except Exception as e:
                    logger.warning(f"⚠️ LLM要約生成失敗: {e}")
        
        execution_time = time.time() - start_time
        
        # 実行情報を生成
        executed_query_info = f"実際のGCP検索実行 (方法: {request.method}"
        if use_internal_evaluation:
            executed_query_info += ", 評価モード: 内部評価"
        if request.use_llm_expansion and vertex_ai_available and request.method != "semantic":
            executed_query_info += ", キーワード拡張: ON"
        if request.use_llm_summary and vertex_ai_available and not use_internal_evaluation:
            executed_query_info += ", AI要約: ON"
        executed_query_info += f", 実行時間: {execution_time:.2f}秒)"
        
        # 拡張情報のデバッグ出力
        if expanded_info:
            logger.info(f"🏷️ レスポンスに拡張情報を含めます: {expanded_info}")
        else:
            logger.info("🏷️ 拡張情報なし")
        
        return {
            "status": "success",
            "query": request.query,
            "method": request.method,
            "evaluation_mode": "legacy",
            "results": results,
            "total": len(results),
            "execution_time": execution_time,
            "executed_query_info": executed_query_info,
            "expanded_info": expanded_info  # 拡張情報を追加
        }
        
    except Exception as e:
        logger.error(f"❌ 実際の検索でエラー: {e}")
        return {
            "status": "error",
            "error_message": str(e),
            "execution_time": time.time() - start_time
        }

# 以下、既存の関数はそのまま維持
async def semantic_search_with_embedding(bq_client: bigquery.Client, query: str, max_results: int) -> List[Dict]:
    """
    実際のセマンティック検索（VECTOR_SEARCH関数を使用）
    """
    try:
        logger.info(f"🔍 セマンティック検索（VECTOR_SEARCH）実行: {query}")
        
        # 1. クエリのベクトル化
        embedding_model = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")
        query_embeddings = embedding_model.get_embeddings([query])
        query_embedding = query_embeddings[0].values
        
        logger.info(f"📊 クエリベクトル次元: {len(query_embedding)}")
        
        # 次元数を768に調整（テーブルのエンベディング次元数に合わせる）
        expected_dimensions = 768
        if len(query_embedding) != expected_dimensions:
            logger.info(f"次元数調整: {len(query_embedding)} → {expected_dimensions}")
            if len(query_embedding) > expected_dimensions:
                query_embedding = query_embedding[:expected_dimensions]
            else:
                query_embedding = query_embedding + [0.0] * (expected_dimensions - len(query_embedding))
        
        # クエリベクトルを文字列形式に変換
        query_embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        # 2. VECTOR_SEARCH関数を使用してセマンティック検索
        sql_query_semantic = f"""
        SELECT
          *
        FROM
          VECTOR_SEARCH(
            (SELECT * FROM `apt-rope-217206.researcher_data.rd_250524`
             WHERE ARRAY_LENGTH(embedding) > 0),
            'embedding',
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
            logger.info(f"BigQueryでセマンティック検索を実行中... (次元: {len(query_embedding)})")
            
            df = bq_client.query(sql_query_semantic, job_config=job_config).to_dataframe()
            
            if len(df) > 0:
                logger.info(f"✅ 検索成功: {len(df)}件")
                logger.info(f"原始DataFrame shape: {df.shape}")
                logger.info(f"原始Columns: {list(df.columns)}")
                
                # ネスト構造を展開
                results = []
                
                for idx, row in df.iterrows():
                    result = {}
                    
                    # distance は直接コピー
                    result['distance'] = row.get('distance')
                    
                    # base カラムから実際のデータを抽出
                    base_data = row.get('base', {})
                    if isinstance(base_data, dict):
                        # base内のすべてのキーをトップレベルにコピー
                        for key, value in base_data.items():
                            result[key] = value
                    else:
                        # baseがネストされていない場合は、直接カラムから取得
                        for col in df.columns:
                            if col != 'distance':
                                result[col] = row[col]
                    
                    results.append(result)
                
                logger.info(f"✅ セマンティック検索完了: {len(results)}件")
                if results:
                    logger.info(f"📊 最小距離: {results[0]['distance']:.4f}")
                
                return results
            else:
                logger.info("検索結果が空です。")
                return []
                
        except Exception as e:
            logger.error(f"BigQueryセマンティック検索中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            
            # VECTOR_SEARCH関数が使えない場合は、リアルタイムベクトル化にフォールバック
            logger.info("🔄 リアルタイムベクトル化検索にフォールバック")
            return await semantic_search_realtime_fallback(bq_client, query, query_embedding, max_results)
        
    except Exception as e:
        logger.error(f"❌ セマンティック検索エラー: {e}")
        # エラー時はキーワード検索にフォールバック
        logger.info("🔄 キーワード検索にフォールバック")
        return await keyword_search(bq_client, query, max_results)

async def semantic_search_realtime_fallback(bq_client: bigquery.Client, query: str, query_embedding: List[float], max_results: int) -> List[Dict]:
    """
    リアルタイムベクトル化によるセマンティック検索（フォールバック）
    """
    try:
        logger.info(f"🔍 リアルタイムベクトル化セマンティック検索実行")
        
        # データベースから研究者データを取得（テキスト形式）
        first_keyword = query.split()[0] if query.split() else query
        search_sql = f"""
        SELECT 
            name_ja,
            name_en,
            main_affiliation_name_ja,
            main_affiliation_name_en,
            research_keywords_ja,
            research_fields_ja,
            profile_ja,
            paper_title_ja_first,
            project_title_ja_first,
            researchmap_url
        FROM `apt-rope-217206.researcher_data.rd_250524`
        WHERE (
            research_keywords_ja IS NOT NULL OR
            research_fields_ja IS NOT NULL OR
            profile_ja IS NOT NULL
        )
        AND (
            LOWER(research_keywords_ja) LIKE LOWER('%{first_keyword}%') OR
            LOWER(research_fields_ja) LIKE LOWER('%{first_keyword}%') OR
            LOWER(profile_ja) LIKE LOWER('%{first_keyword}%')
        )
        LIMIT {max_results * 5}  -- より多くの候補を取得してから類似度計算
        """
        
        query_job = bq_client.query(search_sql)
        candidates = []
        
        for row in query_job:
            # 研究者のテキスト情報を結合
            researcher_text = ""
            if row.research_keywords_ja:
                researcher_text += row.research_keywords_ja + " "
            if row.research_fields_ja:
                researcher_text += row.research_fields_ja + " "
            if row.profile_ja:
                researcher_text += row.profile_ja[:200] + " "  # プロフィールは200文字まで
            
            candidates.append({
                "data": {
                    "name_ja": row.name_ja,
                    "name_en": row.name_en,
                    "main_affiliation_name_ja": row.main_affiliation_name_ja,
                    "main_affiliation_name_en": row.main_affiliation_name_en,
                    "research_keywords_ja": row.research_keywords_ja,
                    "research_fields_ja": row.research_fields_ja,
                    "profile_ja": row.profile_ja,
                    "paper_title_ja_first": row.paper_title_ja_first,
                    "project_title_ja_first": row.project_title_ja_first,
                    "researchmap_url": row.researchmap_url
                },
                "text": researcher_text.strip()
            })
        
        if not candidates:
            logger.info("📊 セマンティック検索の候補が見つかりませんでした")
            return []
        
        logger.info(f"📊 セマンティック検索候補: {len(candidates)}名")
        
        # 候補者のテキストをベクトル化（バッチ処理）
        embedding_model = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")
        candidate_texts = [candidate["text"] for candidate in candidates if candidate["text"]]
        
        if not candidate_texts:
            logger.info("📊 ベクトル化対象のテキストがありません")
            return []
        
        # バッチでベクトル化（効率化）
        batch_size = 5  # Vertex AIの制限に応じて調整
        candidate_embeddings = []
        
        for i in range(0, len(candidate_texts), batch_size):
            batch_texts = candidate_texts[i:i+batch_size]
            try:
                batch_embeddings = embedding_model.get_embeddings(batch_texts)
                candidate_embeddings.extend([emb.values for emb in batch_embeddings])
            except Exception as e:
                logger.warning(f"⚠️ バッチ{i//batch_size + 1}のベクトル化失敗: {e}")
                # エラー時は空のベクトルを追加
                candidate_embeddings.extend([[0.0] * len(query_embedding)] * len(batch_texts))
        
        # コサイン類似度を計算
        results_with_similarity = []
        
        for i, candidate in enumerate(candidates[:len(candidate_embeddings)]):
            if i >= len(candidate_embeddings):
                continue
                
            candidate_embedding = candidate_embeddings[i]
            
            # コサイン類似度計算
            similarity = calculate_cosine_similarity(query_embedding, candidate_embedding)
            
            result = candidate["data"].copy()
            result["distance"] = 1.0 - similarity  # 距離 = 1 - 類似度
            result["similarity"] = similarity
            
            results_with_similarity.append(result)
        
        # 類似度でソート（距離が小さい順 = 類似度が高い順）
        results_with_similarity.sort(key=lambda x: x["distance"])
        
        # 上位結果を返す
        final_results = results_with_similarity[:max_results]
        
        logger.info(f"✅ リアルタイムセマンティック検索完了: {len(final_results)}件")
        if final_results:
            logger.info(f"📊 最小距離: {final_results[0]['distance']:.4f}")
        
        return final_results
        
    except Exception as e:
        logger.error(f"❌ リアルタイムセマンティック検索エラー: {e}")
        raise

def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    コサイン類似度を計算
    """
    try:
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        # ゼロベクトルチェック
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = np.dot(vec1, vec2) / (norm1 * norm2)
        return float(similarity)
        
    except Exception as e:
        logger.warning(f"⚠️ コサイン類似度計算エラー: {e}")
        return 0.0

async def keyword_search(bq_client: bigquery.Client, query: str, max_results: int) -> List[Dict]:
    """
    キーワード検索（全文検索、拡張キーワード対応）
    """
    try:
        logger.info(f"🔍 キーワード検索実行: {query}")
        
        # キーワードを分割
        keywords = [kw.strip() for kw in query.split() if kw.strip()]
        logger.info(f"📝 検索キーワード: {keywords}")
        
        # LIKE条件を構築
        like_conditions = []
        for keyword in keywords:
            # SQLインジェクション対策
            safe_keyword = keyword.replace("'", "''")
            like_conditions.extend([
                f"LOWER(research_keywords_ja) LIKE LOWER('%{safe_keyword}%')",
                f"LOWER(research_fields_ja) LIKE LOWER('%{safe_keyword}%')",
                f"LOWER(profile_ja) LIKE LOWER('%{safe_keyword}%')",
                f"LOWER(name_ja) LIKE LOWER('%{safe_keyword}%')",
                f"LOWER(paper_title_ja_first) LIKE LOWER('%{safe_keyword}%')",
                f"LOWER(project_title_ja_first) LIKE LOWER('%{safe_keyword}%')"
            ])
        
        where_clause = " OR ".join(like_conditions)
        
        # 関連度スコアをキーワードごとに計算
        relevance_scores = []
        for keyword in keywords:
            safe_keyword = keyword.replace("'", "''")
            relevance_scores.append(f"""
                (
                    CASE WHEN LOWER(name_ja) LIKE LOWER('%{safe_keyword}%') THEN 10 ELSE 0 END +
                    CASE WHEN LOWER(research_keywords_ja) LIKE LOWER('%{safe_keyword}%') THEN 8 ELSE 0 END +
                    CASE WHEN LOWER(research_fields_ja) LIKE LOWER('%{safe_keyword}%') THEN 6 ELSE 0 END +
                    CASE WHEN LOWER(paper_title_ja_first) LIKE LOWER('%{safe_keyword}%') THEN 5 ELSE 0 END +
                    CASE WHEN LOWER(project_title_ja_first) LIKE LOWER('%{safe_keyword}%') THEN 5 ELSE 0 END +
                    CASE WHEN LOWER(profile_ja) LIKE LOWER('%{safe_keyword}%') THEN 4 ELSE 0 END
                )
            """)
        
        total_relevance_score = " + ".join(relevance_scores) if relevance_scores else "0"
        
        search_sql = f"""
        SELECT 
            name_ja,
            name_en,
            main_affiliation_name_ja,
            main_affiliation_name_en,
            research_keywords_ja,
            research_fields_ja,
            profile_ja,
            paper_title_ja_first,
            project_title_ja_first,
            researchmap_url,
            -- 関連度スコア（重み付けされたマッチの合計）
            ({total_relevance_score}) as relevance_score
        FROM `apt-rope-217206.researcher_data.rd_250524`
        WHERE {where_clause}
        ORDER BY relevance_score DESC, name_ja
        LIMIT {max_results}
        """
        
        query_job = bq_client.query(search_sql)
        results = []
        
        for row in query_job:
            result = {
                "name_ja": row.name_ja,
                "name_en": row.name_en,
                "main_affiliation_name_ja": row.main_affiliation_name_ja,
                "main_affiliation_name_en": row.main_affiliation_name_en,
                "research_keywords_ja": row.research_keywords_ja,
                "research_fields_ja": row.research_fields_ja,
                "profile_ja": row.profile_ja,
                "paper_title_ja_first": row.paper_title_ja_first,
                "project_title_ja_first": row.project_title_ja_first,
                "researchmap_url": row.researchmap_url,
                "relevance_score": float(row.relevance_score) if row.relevance_score else None
            }
            results.append(result)
        
        logger.info(f"✅ キーワード検索完了: {len(results)}件")
        return results
        
    except Exception as e:
        logger.error(f"❌ キーワード検索エラー: {e}")
        raise

async def expand_query_with_llm(query: str) -> Dict[str, Any]:
    """
    LLMを使用してクエリを拡張し、拡張されたキーワードのリストを返す
    """
    try:
        logger.info(f"🤖 LLMクエリ拡張開始: {query}")
        
        # Gemini 2.0 Flash使用
        try:
            model = GenerativeModel("gemini-2.0-flash-001")
            
            prompt = f"""あなたは学術研究データベースの検索アシスタントです。
ユーザーが入力した「元のキーワード」について、そのキーワードを含む研究情報をより効果的に見つけるために、
関連性の高い類義語、上位/下位概念語、英語の対応語（もしあれば）、具体的な技術名や物質名などを考慮し、
検索に有効そうなキーワードを最大10個提案してください。
提案は日本語の単語または短いフレーズで、カンマ区切りで出力してください。元のキーワード自体も提案に含めてください。

元のキーワード: 「{query}」

提案:"""
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 200,
                    "top_p": 0.8,
                    "top_k": 40
                }
            )
            
            expanded_text = response.text.strip()
            if expanded_text:
                # カンマ区切りでキーワードを分割
                expanded_keywords = [kw.strip() for kw in expanded_text.split(',') if kw.strip()]
                
                # 重複を削除しつつ順序を保持
                final_keywords = []
                if query not in expanded_keywords:
                    final_keywords.append(query)
                for kw in expanded_keywords:
                    if kw not in final_keywords:
                        final_keywords.append(kw)
                
                logger.info(f"✅ LLMクエリ拡張完了 (gemini-2.0-flash-001): {final_keywords}")
                return {
                    "original_query": query,
                    "expanded_keywords": final_keywords,
                    "expanded_query": ' '.join(final_keywords[:5])  # 検索用には最初の5個を使用
                }
            
        except Exception as e:
            logger.warning(f"⚠️ Gemini 2.0 Flash失敗: {e}")
            
            # フォールバックでtext-bisonを試行
            try:
                model = TextGenerationModel.from_pretrained("text-bison@002")
                
                prompt = f"""研究キーワード「{query}」に関連する学術用語を5-10個提案してください。カンマ区切りで出力してください。

元のキーワード: {query}

関連キーワード:"""
                
                response = model.predict(
                    prompt,
                    temperature=0.2,
                    max_output_tokens=200,
                    top_p=0.8,
                    top_k=40
                )
                
                expanded_text = response.text.strip()
                if expanded_text:
                    expanded_keywords = [kw.strip() for kw in expanded_text.split(',') if kw.strip()]
                    final_keywords = [query] if query not in expanded_keywords else []
                    final_keywords.extend([kw for kw in expanded_keywords if kw not in final_keywords])
                    
                    logger.info(f"✅ LLMクエリ拡張完了 (text-bison@002): {final_keywords}")
                    return {
                        "original_query": query,
                        "expanded_keywords": final_keywords,
                        "expanded_query": ' '.join(final_keywords[:5])
                    }
                    
            except Exception as e2:
                logger.warning(f"⚠️ Text-Bison フォールバック失敗: {e2}")
        
        # エラー時は元のクエリのみを返す
        logger.warning("⚠️ すべてのLLMモデルでクエリ拡張に失敗")
        return {
            "original_query": query,
            "expanded_keywords": [query],
            "expanded_query": query
        }
        
    except Exception as e:
        logger.error(f"❌ LLMクエリ拡張エラー: {e}")
        return {
            "original_query": query,
            "expanded_keywords": [query],
            "expanded_query": query
        }

async def add_llm_summaries(results: List[Dict], query: str) -> List[Dict]:
    """
    各研究者にLLM要約を追加（Gemini 2.0対応版、レート制限対策版）
    """
    try:
        logger.info(f"🤖 LLM要約生成開始: {len(results)}名の研究者")
        
        # Gemini 2.0 Flash Lite使用（軽量モデル）
        model = None
        model_name = ""
        
        try:
            model = GenerativeModel("gemini-2.0-flash-lite-001")
            model_name = "gemini-2.0-flash-lite-001"
            logger.info(f"✅ 軽量LLMモデル {model_name} を使用")
        except Exception as e:
            logger.warning(f"⚠️ Gemini 2.0 Flash Lite失敗: {e}")
            
            # フォールバックでtext-bisonを試行
            try:
                model = TextGenerationModel.from_pretrained("text-bison@002")
                model_name = "text-bison@002"
                logger.info(f"✅ LLMモデル {model_name} を使用")
            except Exception as e2:
                logger.error(f"❌ フォールバックモデル失敗: {e2}")
                return results
        
        if not model:
            logger.error("❌ 利用可能なLLMモデルがありません")
            return results
        
        for idx, result in enumerate(results):
            try:
                # レート制限対策: 少し待機
                if idx > 0:
                    time.sleep(0.5)
                
                # シンプルなプロンプトでトークン数を削減
                name = result.get('name_ja', '')
                affiliation = result.get('main_affiliation_name_ja', '')
                keywords = result.get('research_keywords_ja', '')
                profile = str(result.get('profile_ja', ''))[:200]  # 短縮
                
                prompt = f"""検索クエリ: 「{query}」
研究者: {name} ({affiliation})
研究キーワード: {keywords}
プロフィール概要: {profile}

この研究者と検索クエリとの関連性を200字以内で簡潔に説明してください:"""
                
                summary = ""
                
                if "gemini" in model_name:
                    # Geminiモデルの場合
                    response = model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": 0.1,
                            "max_output_tokens": 200,  # 短く制限
                            "top_p": 0.8
                        }
                    )
                    summary = response.text.strip()
                else:
                    # text-bisonモデルの場合
                    response = model.predict(
                        prompt,
                        temperature=0.1,
                        max_output_tokens=200,
                        top_p=0.8
                    )
                    summary = response.text.strip()
                
                if summary:
                    result["llm_summary"] = summary
                else:
                    result["llm_summary"] = f"「{query}」に関連する研究を行っています。"
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "Resource exhausted" in error_msg:
                    logger.warning(f"⚠️ API制限のため要約をスキップ ({result.get('name_ja', 'N/A')}): {e}")
                    result["llm_summary"] = "⚠️ API制限のため要約をスキップしました"
                else:
                    logger.warning(f"⚠️ 個別LLM要約エラー ({result.get('name_ja', 'N/A')}): {e}")
                    result["llm_summary"] = f"「{query}」に関連する研究を行っています。"
        
        logger.info("✅ LLM要約生成完了")
        return results
        
    except Exception as e:
        logger.error(f"❌ LLM要約生成エラー: {e}")
        # エラー時はそのまま返す
        return results
