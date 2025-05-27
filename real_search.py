"""
実際の研究者検索機能（LLM修正版）
BigQuery + Vertex AI を使用した本格的な検索システム
LLM機能の安定性を向上
"""

import logging
import time
from typing import Dict, List, Optional, Any
from google.cloud import bigquery
from vertexai.language_models import TextGenerationModel, TextEmbeddingModel
from vertexai.generative_models import GenerativeModel
import numpy as np

logger = logging.getLogger(__name__)

async def perform_real_search(request) -> Dict[str, Any]:
    """
    実際の研究者検索を実行
    """
    start_time = time.time()
    
    try:
        logger.info(f"🔍 実際の検索開始: {request.query}, method: {request.method}")
        
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
                expanded_query = await expand_query_with_llm(search_query)
                if expanded_query and expanded_query != search_query:
                    expanded_info = {
                        "original_query": search_query,
                        "expanded_query": expanded_query
                    }
                    search_query = expanded_query
                    logger.info(f"🔄 LLMクエリ拡張結果: {search_query}")
                    logger.info(f"🧠 拡張情報保存: {expanded_info}")
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
        
        # LLM要約の生成
        if request.use_llm_summary and results and vertex_ai_available:
            try:
                results = await add_llm_summaries(results, request.query)  # 元のクエリを使用
                logger.info("🤖 LLM要約を追加完了")
            except Exception as e:
                logger.warning(f"⚠️ LLM要約生成失敗: {e}")
        
        execution_time = time.time() - start_time
        
        # 実行情報を生成
        executed_query_info = f"実際のGCP検索実行 (方法: {request.method}"
        if request.use_llm_expansion and vertex_ai_available and request.method != "semantic":
            executed_query_info += ", キーワード拡張: ON"
        if request.use_llm_summary and vertex_ai_available:
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

async def semantic_search_with_embedding(bq_client: bigquery.Client, query: str, max_results: int) -> List[Dict]:
    """
    実際のセマンティック検索（ベクトル埋め込みベース）
    """
    try:
        logger.info(f"🔍 セマンティック検索（埋め込みベース）実行: {query}")
        
        # 1. クエリのベクトル化
        embedding_model = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")
        query_embeddings = embedding_model.get_embeddings([query])
        query_embedding = query_embeddings[0].values
        
        logger.info(f"📊 クエリベクトル次元: {len(query_embedding)}")
        
        # 2. データベースから研究者データを取得（テキスト形式）
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
        
        # 3. 候補者のテキストをベクトル化（バッチ処理）
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
        
        # 4. コサイン類似度を計算
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
        
        # 5. 類似度でソート（類似度が高い順）
        results_with_similarity.sort(key=lambda x: x["similarity"], reverse=True)
        
        # 上位結果を返す
        final_results = results_with_similarity[:max_results]
        
        logger.info(f"✅ セマンティック検索完了: {len(final_results)}件")
        if final_results:
            logger.info(f"📊 最高類似度: {final_results[0]['similarity']:.4f}")
        
        return final_results
        
    except Exception as e:
        logger.error(f"❌ セマンティック検索エラー: {e}")
        # エラー時はキーワード検索にフォールバック
        logger.info("🔄 キーワード検索にフォールバック")
        return await keyword_search(bq_client, query, max_results)

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
    キーワード検索（従来の全文検索）
    """
    try:
        logger.info(f"🔍 キーワード検索実行: {query}")
        
        # キーワードを分割
        keywords = [kw.strip() for kw in query.split() if kw.strip()]
        
        # LIKE条件を構築
        like_conditions = []
        for keyword in keywords:
            like_conditions.extend([
                f"LOWER(research_keywords_ja) LIKE LOWER('%{keyword}%')",
                f"LOWER(research_fields_ja) LIKE LOWER('%{keyword}%')",
                f"LOWER(profile_ja) LIKE LOWER('%{keyword}%')",
                f"LOWER(name_ja) LIKE LOWER('%{keyword}%')"
            ])
        
        where_clause = " OR ".join(like_conditions)
        
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
            -- 関連度スコア（マッチした条件の数）
            (
                {' + '.join([f"CASE WHEN {condition} THEN 1 ELSE 0 END" for condition in like_conditions])}
            ) as relevance_score
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

async def expand_query_with_llm(query: str) -> str:
    """
    LLMを使用してクエリを拡張（Gemini 2.0対応版）
    """
    try:
        logger.info(f"🤖 LLMクエリ拡張開始: {query}")
        
        # Gemini 2.0 Flash使用
        try:
            model = GenerativeModel("gemini-2.0-flash-001")
            
            prompt = f"""研究キーワード「{query}」に関連する学術用語を3-5個追加して、より効果的な検索クエリを作成してください。

元のキーワード: {query}

拡張されたクエリ (元のキーワード + 関連用語):"""
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 100,
                    "top_p": 0.8,
                    "top_k": 40
                }
            )
            
            expanded_query = response.text.strip()
            if expanded_query and len(expanded_query) > len(query):
                logger.info(f"✅ LLMクエリ拡張完了 (gemini-2.0-flash-001): {expanded_query}")
                return expanded_query
            
        except Exception as e:
            logger.warning(f"⚠️ Gemini 2.0 Flash失敗: {e}")
            
            # フォールバックでtext-bisonを試行
            try:
                model = TextGenerationModel.from_pretrained("text-bison@002")
                
                prompt = f"""研究キーワード「{query}」に関連する学術用語を3-5個追加して、より効果的な検索クエリを作成してください。

元のキーワード: {query}

拡張されたクエリ (元のキーワード + 関連用語):"""
                
                response = model.predict(
                    prompt,
                    temperature=0.2,
                    max_output_tokens=100,
                    top_p=0.8,
                    top_k=40
                )
                
                expanded_query = response.text.strip()
                if expanded_query and len(expanded_query) > len(query):
                    logger.info(f"✅ LLMクエリ拡張完了 (text-bison@002): {expanded_query}")
                    return expanded_query
                    
            except Exception as e2:
                logger.warning(f"⚠️ Text-Bison フォールバック失敗: {e2}")
        
        # エラー時は元のクエリを返す
        logger.warning("⚠️ すべてのLLMモデルでクエリ拡張に失敗")
        return query
        
    except Exception as e:
        logger.error(f"❌ LLMクエリ拡張エラー: {e}")
        return query

async def add_llm_summaries(results: List[Dict], query: str) -> List[Dict]:
    """
    各研究者にLLM要約を追加（Gemini 2.0対応版）
    """
    try:
        logger.info(f"🤖 LLM要約生成開始: {len(results)}名の研究者")
        
        # Gemini 2.0 Flash Lite使用
        model = None
        model_name = ""
        
        try:
            model = GenerativeModel("gemini-2.0-flash-lite-001")
            model_name = "gemini-2.0-flash-lite-001"
            logger.info(f"✅ LLMモデル {model_name} を使用")
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
        
        for result in results:
            try:
                # プロフィール情報を整理
                name = result.get('name_ja', 'N/A')
                affiliation = result.get('main_affiliation_name_ja', 'N/A')
                keywords = result.get('research_keywords_ja', 'N/A')
                fields = result.get('research_fields_ja', 'N/A')
                
                profile_text = f"""研究者: {name}
所属: {affiliation}
キーワード: {keywords}
分野: {fields}"""
                
                prompt = f"""以下の研究者が「{query}」とどのように関連しているか、簡潔に説明してください（50文字以内）。

{profile_text}

関連性の説明:"""
                
                summary = ""
                
                if "gemini" in model_name:
                    # Geminiモデルの場合
                    response = model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": 0.2,
                            "max_output_tokens": 80,
                            "top_p": 0.8
                        }
                    )
                    summary = response.text.strip()
                else:
                    # text-bisonモデルの場合
                    response = model.predict(
                        prompt,
                        temperature=0.2,
                        max_output_tokens=80,
                        top_p=0.8
                    )
                    summary = response.text.strip()
                
                if summary:
                    result["llm_summary"] = summary
                else:
                    result["llm_summary"] = f"「{query}」に関連する研究を行っています。"
                
            except Exception as e:
                logger.warning(f"⚠️ 個別LLM要約エラー ({result.get('name_ja', 'N/A')}): {e}")
                result["llm_summary"] = f"「{query}」に関連する研究を行っています。"
        
        logger.info("✅ LLM要約生成完了")
        return results
        
    except Exception as e:
        logger.error(f"❌ LLM要約生成エラー: {e}")
        # エラー時はそのまま返す
        return results
