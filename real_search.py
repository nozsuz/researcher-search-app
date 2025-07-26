"""
実際の研究者検索機能（評価システム・除外キーワード機能統合版）
BigQuery + Vertex AI + 評価システムを使用した本格的な検索システム
"""

import logging
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from google.cloud import bigquery
from vertexai.language_models import TextGenerationModel, TextEmbeddingModel
from vertexai.generative_models import GenerativeModel
import numpy as np
from evaluation_system import UniversalResearchEvaluator

logger = logging.getLogger(__name__)

# 評価システムのインスタンスをグローバルに保持
evaluator = UniversalResearchEvaluator()

def is_young_researcher(researcher_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    若手研究者かどうかを判定するロジック（インデント修正・文字化け対策版）
    """
    reasons = []
    name = researcher_data.get('name_ja', 'Unknown')
    logger.debug(f"🔍 若手研究者判定開始: {name}")

    # --- データ準備 ---
    profile_ja = (researcher_data.get('profile_ja', '') or '').lower()
    job_ja = (researcher_data.get('main_affiliation_job_ja', '') or '').lower()
    job_title_ja = (researcher_data.get('main_affiliation_job_title_ja', '') or '').lower()
    job_en = (researcher_data.get('main_affiliation_job_en', '') or '').lower()
    job_title_en = (researcher_data.get('main_affiliation_job_title_en', '') or '').lower()
    
    combined_job_info = f"{job_ja} {job_title_ja} {job_en} {job_title_en}"
    
    # --- 判定キーワード定義 ---
    young_positions_ja = ['助教', '准教授', '博士研究員', 'ポスドク', '研究員', '特任助教', '特任准教授', '助手', '講師', '特任研究員', '博士後期課程', '博士課程', 'ポストドクトラル', '日本学術振興会特別研究員', 'jsps特別研究員', '特別研究員', '博士学生', '大学院生', '医員']
    young_positions_en = ['assistant', 'associate professor', 'postdoc', 'researcher', 'fellow', 'doctoral', 'phd student', 'graduate student', 'research associate', 'post-doctoral', 'jsps fellow']
    senior_positions_ja = ['教授', '名誉教授', '客員教授', '特任教授', '主席研究員', '統括', '代表取締役', '社長', '所長', 'センター長']
    senior_positions_en = ['professor', 'emeritus', 'director', 'principal', 'chief', 'ceo', 'president']
    
    # --- 1. 除外条件のチェック (最優先) ---
    for pos in senior_positions_ja:
        if pos in combined_job_info:
            reasons = [f"除外条件(\u8077\u4f4d): {pos}"]
            logger.debug(f"🎯 若手判定結果: {name} - False - {reasons}")
            return False, reasons
            
    for pos in senior_positions_en:
        if pos in combined_job_info and 'associate professor' not in combined_job_info:
            reasons = [f"除外条件(\u8077\u4f4d,英): {pos}"]
            logger.debug(f"🎯 若手判定結果: {name} - False - {reasons}")
            return False, reasons

    exclusion_keywords_profile = ['退職', '元教授', '元所長', '顧問', '理事長', '学長', '総長']
    for keyword in exclusion_keywords_profile:
        if keyword in profile_ja:
            reasons = [f"除外条件(経歴): {keyword}"]
            logger.debug(f"🎯 若手判定結果: {name} - False - {reasons}")
            return False, reasons

    # --- 2. 若手判定 (職位を優先) ---
    for pos in young_positions_ja:
        if pos in combined_job_info:
            reasons.append(f"\u8077\u4f4d: {pos}")
            break
    if not reasons:
        for pos in young_positions_en:
            if pos in combined_job_info:
                reasons.append(f"\u8077\u4f4d(英): {pos}")
                break

    # --- 3. プロフィールからの推測 (職位で判定できなかった場合) ---
    if not reasons:
        current_position_patterns = [r'\d{4}年\s*-\s*(.+)', r'\d{4}年\s*～\s*(.+)', r'\d{4}年\s*から\s*(.+)', r'現在\s*[：:]?\s*(.+)']
        for pattern in current_position_patterns:
            match = re.search(pattern, profile_ja)
            if match:
                position_text = match.group(1).lower()
                if not any(sp in position_text for sp in senior_positions_ja):
                    for pos in young_positions_ja:
                        if pos in position_text:
                            reasons.append(f"現職(プロフィール): {pos}")
                            break
                if reasons: break
        
        if not reasons:
            current_year = datetime.now().year
            phd_patterns = [r'(\d{4})年.*?博士.*?取得', r'(\d{4})年.*?ph\\.?d\\.?', r'博士.*?(\d{4})年', r'ph\\.?d\\.?.*?(\d{4})', r'(\d{4})年.*?学位', r'(\d{4})年.*?博士課程.*?修了']
            for pattern in phd_patterns:
                match = re.search(pattern, profile_ja)
                if match:
                    year_str = match.group(1)
                    if year_str and year_str.isdigit():
                        year = int(year_str)
                        years_since = current_year - year
                        if 0 <= years_since <= 15:
                            reasons.append(f"博士取得: {year}年（{years_since}年前）")
                            break
            
            if not reasons:
                age_patterns = [r'(\d{2})歳', r'(\d{4})年生まれ', r'(\d{4})年.*?誕生']
                for pattern in age_patterns:
                    match = re.search(pattern, profile_ja)
                    if match:
                        age_text = match.group(1)
                        if age_text and age_text.isdigit():
                            if '歳' in pattern:
                                age = int(age_text)
                                if 25 <= age <= 45: reasons.append(f"年齢: {age}歳")
                            else:
                                birth_year = int(age_text)
                                age = current_year - birth_year
                                if 25 <= age <= 45: reasons.append(f"生年: {birth_year}年（{age}歳）")
                        if reasons: break
            
            if not reasons:
                young_keywords = ['若手', '新進気鋭', 'early career', '博士課程', '博士取得', 'キャリア初期', '研究員として', '採用され', '着任', '博士号取得', 'ph.d.取得', '学振', 'jsps', '育志賞', '若手研究者賞', '奨励賞']
                for keyword in young_keywords:
                    if keyword in profile_ja:
                        reasons.append(f"キーワード: {keyword}")
                        break

    is_young = len(reasons) > 0
    logger.debug(f"🎯 若手判定結果: {name} - {is_young} - {reasons}")
    return is_young, list(set(reasons))


async def perform_real_search(request) -> Dict[str, Any]:
    """
    研究者検索のメイン関数（フィルタリングロジック修正版）
    """
    start_time = time.time()
    try:
        logger.info(f"🔍 実際の検索開始: {request.query}, method: {request.method}")
        
        # --- パラメータ準備 ---
        young_researcher_filter = getattr(request, 'young_researcher_filter', False)
        university_filter = getattr(request, 'university_filter', None)
        exclude_keywords = getattr(request, 'exclude_keywords', None)
        
        logger.info(f"📊 若手フィルター: {'ON' if young_researcher_filter else 'OFF'}")
        if university_filter: logger.info(f"🏫 大学フィルター: {university_filter}")
        if exclude_keywords: logger.info(f"🚫 除外キーワード: {exclude_keywords}")

        # --- GCPクライアント準備 ---
        from gcp_auth import get_bigquery_client, is_vertex_ai_ready
        bq_client = get_bigquery_client()
        if not bq_client:
            raise Exception("BigQueryクライアントが利用できません")
        
        vertex_ai_available = is_vertex_ai_ready()
        if (request.method == "semantic" or request.use_llm_expansion) and not vertex_ai_available:
            logger.warning("⚠️ Vertex AIが利用できないため、キーワード検索にフォールバックします。")
            request.method = "keyword"
            request.use_llm_expansion = False

        # --- クエリ拡張 (必要な場合) ---
        search_query = request.query.strip()
        expanded_info = None
        if request.use_llm_expansion and request.method == "keyword":
            try:
                expansion_result = await expand_query_with_llm(search_query)
                if expansion_result and expansion_result["expanded_keywords"] != [search_query]:
                    expanded_info = expansion_result
                    search_query = expansion_result["expanded_query"]
                    logger.info(f"🧠 クエリ拡張実行: {search_query}")
            except Exception as e:
                logger.warning(f"⚠️ LLMクエリ拡張失敗: {e}")

        # --- 検索実行 ---
        # 各検索関数内で is_young_researcher の判定が行われる
        if request.method == "semantic":
            results = await semantic_search_with_embedding(bq_client, search_query, request.max_results, university_filter, exclude_keywords)
        else:
            results = await keyword_search(bq_client, search_query, request.max_results, university_filter, exclude_keywords)
        
        logger.info(f"📊 初期検索結果: {len(results)}件")

        # --- 若手研究者フィルタリング (ここが重要) ---
        # 検索結果に対して、リクエストに応じてフィルタリングを適用する
        if young_researcher_filter:
            logger.info(f"🌟 若手研究者フィルタリングを実行")
            
            # is_young_researcherがTrueのレコードのみを抽出
            filtered_results = [r for r in results if r.get('is_young_researcher', False)]
            
            logger.info(f"🌟 フィルタリング結果: {len(results)}件 → {len(filtered_results)}件")
            results = filtered_results

        # --- AI要約 (フィルタリング後の結果に対して実行) ---
        if request.use_llm_summary and results and vertex_ai_available:
            try:
                results = await add_llm_summaries(results, request.query)
                logger.info("🤖 AI要約を追加完了")
            except Exception as e:
                logger.warning(f"⚠️ AI要約生成失敗: {e}")

        # --- レスポンス生成 ---
        execution_time = time.time() - start_time
        executed_query_info = f"実際のGCP検索実行 (方法: {request.method}, 実行時間: {execution_time:.2f}秒)"
        
        return {
            "status": "success",
            "query": request.query,
            "method": request.method,
            "results": results,
            "total": len(results),
            "execution_time": execution_time,
            "executed_query_info": executed_query_info,
            "expanded_info": expanded_info
        }

    except Exception as e:
        logger.error(f"❌ 実際の検索でエラー: {e}")
        import traceback
        logger.error(f"スタックトレース: {traceback.format_exc()}")
        return {
            "status": "error",
            "error_message": str(e),
            "execution_time": time.time() - start_time
        }

# ▼▼▼ この関数をまるごと置き換えてください ▼▼▼
async def semantic_search_with_embedding(bq_client: bigquery.Client, query: str, max_results: int, university_filter: Optional[List[str]] = None, exclude_keywords: Optional[List[str]] = None) -> List[Dict]:
    """
    実際のセマンティック検索（事後フィルタリング方式の【完全修正版】）
    """
    query_embedding = None
    try:
        logger.info(f"🔍 セマンティック検索（事後フィルタリング【修正版】）実行: {query}")
        
        # 1. クエリのベクトル化
        embedding_model = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")
        query_embeddings = embedding_model.get_embeddings([query])
        query_embedding = query_embeddings[0].values
        
        expected_dimensions = 768
        if len(query_embedding) != expected_dimensions:
            if len(query_embedding) > expected_dimensions:
                query_embedding = query_embedding[:expected_dimensions]
            else:
                query_embedding = query_embedding + [0.0] * (expected_dimensions - len(query_embedding))
        
        query_embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        # 2. 大学フィルター条件（事前フィルタリング用）
        university_condition = ""
        if university_filter and len(university_filter) > 0:
            try:
                from university_normalizer_fixed import get_university_normalization_sql
                safe_universities = [univ.replace("'", "''") for univ in university_filter]
                university_list = ",".join([f"'{univ}'" for univ in safe_universities])
                normalization_sql = get_university_normalization_sql("main_affiliation_name_ja")
                university_condition = f" AND ({normalization_sql}) IN ({university_list})"
            except Exception as e:
                logger.warning(f"⚠️ 大学正規化システムエラー、シンプルフィルターを使用: {e}")
                safe_universities = [univ.replace("'", "''") for univ in university_filter]
                like_conditions = [f"main_affiliation_name_ja LIKE '%{univ}%'" for univ in safe_universities]
                university_condition = f" AND ({' OR '.join(like_conditions)})"

        # 3. 除外キーワード条件（事後フィルタリング用）
        exclude_where_clause = ""
        if exclude_keywords:
            conditions = []
            for keyword in exclude_keywords:
                safe_keyword = keyword.replace("'", "''")
                # `base`プレフィックスを削除
                conditions.append(f"""
                    NOT (
                        LOWER(research_keywords_ja) LIKE LOWER('%{safe_keyword}%') OR
                        LOWER(research_fields_ja) LIKE LOWER('%{safe_keyword}%') OR
                        LOWER(profile_ja) LIKE LOWER('%{safe_keyword}%')
                    )
                """)
            if conditions:
                exclude_where_clause = f"WHERE {' AND '.join(conditions)}"

        # 4. 事後フィルタリングを行うSQLクエリを構築
        top_k_for_search = max(50, max_results * 5)

        sql_query_semantic = f"""
        WITH vector_results AS (
            SELECT
                base.*,  -- ここでbase構造を展開する
                distance
            FROM
                VECTOR_SEARCH(
                    (SELECT * FROM `apt-rope-217206.researcher_data.rd_250524`
                     WHERE ARRAY_LENGTH(embedding) > 0{university_condition}),
                    'embedding',
                    (SELECT {query_embedding_str} AS query_vector),
                    top_k => @top_k_for_search,
                    distance_type => 'COSINE'
                )
        )
        SELECT *
        FROM vector_results
        {exclude_where_clause}
        ORDER BY distance ASC
        LIMIT @max_results
        """
        
        logger.info(f"Generated SQL for Semantic Search:\n{sql_query_semantic}")
        
        try:
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("top_k_for_search", "INT64", top_k_for_search),
                    bigquery.ScalarQueryParameter("max_results", "INT64", max_results),
                ]
            )
            df = bq_client.query(sql_query_semantic, job_config=job_config).to_dataframe()
            
            if len(df) > 0:
                results = []
                # この修正により、dfには既に展開されたカラムが含まれるため、整形ロジックを簡略化
                for idx, row in df.iterrows():
                    result = row.to_dict()
                    result["distance"] = row["distance"] # ← この行を追加
                    is_young, young_reasons = is_young_researcher(result)
                    result["is_young_researcher"] = is_young
                    result["young_researcher_reasons"] = young_reasons
                    results.append(result)
                
                logger.info(f"✅ セマンティック検索完了: {len(results)}件")
                return results
            else:
                logger.info("検索結果が空です。")
                return []
                
        except Exception as e:
            logger.error(f"BigQueryセマンティック検索中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            logger.info("🔄 リアルタイムベクトル化検索にフォールバック")
            return await semantic_search_realtime_fallback(bq_client, query, query_embedding, max_results, university_filter, exclude_keywords)
        
    except Exception as e:
        logger.error(f"❌ セマンティック検索エラー: {e}")
        logger.info("🔄 キーワード検索にフォールバック")
        return await keyword_search(bq_client, query, max_results, university_filter, exclude_keywords)

async def semantic_search_realtime_fallback(bq_client: bigquery.Client, query: str, query_embedding: List[float], max_results: int, university_filter: Optional[List[str]] = None, exclude_keywords: Optional[List[str]] = None) -> List[Dict]:
    # (この関数は変更ありません)
    try:
        logger.info(f"🔍 リアルタイムベクトル化セマンティック検索実行")
        first_keyword = query.split()[0] if query.split() else query
        university_condition = ""
        if university_filter and len(university_filter) > 0:
            try:
                from university_normalizer_fixed import get_university_normalization_sql
                safe_universities = [univ.replace("'", "''") for univ in university_filter]
                university_list = ",".join([f"'{univ}'" for univ in safe_universities])
                normalization_sql = get_university_normalization_sql("main_affiliation_name_ja")
                university_condition = f" AND ({normalization_sql}) IN ({university_list})"
            except Exception as e:
                logger.warning(f"⚠️ 大学正規化システムエラー、シンプルフィルターを使用: {e}")
                safe_universities = [univ.replace("'", "''") for univ in university_filter]
                like_conditions = [f"main_affiliation_name_ja LIKE '%{univ}%'" for univ in safe_universities]
                university_condition = f" AND ({' OR '.join(like_conditions)})"
        exclude_condition = ""
        if exclude_keywords:
            conditions = []
            for keyword in exclude_keywords:
                safe_keyword = keyword.replace("'", "''")
                conditions.append(f""" NOT ( LOWER(research_keywords_ja) LIKE LOWER('%{safe_keyword}%') OR LOWER(research_fields_ja) LIKE LOWER('%{safe_keyword}%') OR LOWER(profile_ja) LIKE LOWER('%{safe_keyword}%') ) """)
            if conditions: exclude_condition = f" AND {' AND '.join(conditions)}"
        search_sql = f""" SELECT name_ja, name_en, main_affiliation_name_ja, main_affiliation_name_en, main_affiliation_job_ja, main_affiliation_job_title_ja, main_affiliation_job_en, main_affiliation_job_title_en, research_keywords_ja, research_fields_ja, profile_ja, paper_title_ja_first, project_title_ja_first, researchmap_url FROM `apt-rope-217206.researcher_data.rd_250524` WHERE ( research_keywords_ja IS NOT NULL OR research_fields_ja IS NOT NULL OR profile_ja IS NOT NULL ) AND ( LOWER(research_keywords_ja) LIKE LOWER('%{first_keyword}%') OR LOWER(research_fields_ja) LIKE LOWER('%{first_keyword}%') OR LOWER(profile_ja) LIKE LOWER('%{first_keyword}%') ){university_condition}{exclude_condition} LIMIT {max_results * 5} """
        query_job = bq_client.query(search_sql)
        candidates = []
        for row in query_job:
            researcher_text = ""
            if row.research_keywords_ja: researcher_text += row.research_keywords_ja + " "
            if row.research_fields_ja: researcher_text += row.research_fields_ja + " "
            if row.profile_ja: researcher_text += row.profile_ja[:200] + " "
            candidates.append({ "data": { "name_ja": row.name_ja, "name_en": row.name_en, "main_affiliation_name_ja": row.main_affiliation_name_ja, "main_affiliation_name_en": row.main_affiliation_name_en, "main_affiliation_job_ja": row.main_affiliation_job_ja, "main_affiliation_job_title_ja": row.main_affiliation_job_title_ja, "main_affiliation_job_en": row.main_affiliation_job_en, "main_affiliation_job_title_en": row.main_affiliation_job_title_en, "research_keywords_ja": row.research_keywords_ja, "research_fields_ja": row.research_fields_ja, "profile_ja": row.profile_ja, "paper_title_ja_first": row.paper_title_ja_first, "project_title_ja_first": row.project_title_ja_first, "researchmap_url": row.researchmap_url }, "text": researcher_text.strip() })
        if not candidates:
            logger.info("📊 セマンティック検索の候補が見つかりませんでした")
            return []
        logger.info(f"📊 セマンティック検索候補: {len(candidates)}名")
        embedding_model = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")
        candidate_texts = [candidate["text"] for candidate in candidates if candidate["text"]]
        if not candidate_texts:
            logger.info("📊 ベクトル化対象のテキストがありません")
            return []
        batch_size = 5
        candidate_embeddings = []
        for i in range(0, len(candidate_texts), batch_size):
            batch_texts = candidate_texts[i:i+batch_size]
            try:
                batch_embeddings = embedding_model.get_embeddings(batch_texts)
                candidate_embeddings.extend([emb.values for emb in batch_embeddings])
            except Exception as e:
                logger.warning(f"⚠️ バッチ{i//batch_size + 1}のベクトル化失敗: {e}")
                candidate_embeddings.extend([[0.0] * len(query_embedding)] * len(batch_texts))
        results_with_similarity = []
        for i, candidate in enumerate(candidates[:len(candidate_embeddings)]):
            if i >= len(candidate_embeddings): continue
            candidate_embedding = candidate_embeddings[i]
            similarity = calculate_cosine_similarity(query_embedding, candidate_embedding)
            result = candidate["data"].copy()
            result["distance"] = 1.0 - similarity
            result["similarity"] = similarity
            is_young, young_reasons = is_young_researcher(result)
            result["is_young_researcher"] = is_young
            result["young_researcher_reasons"] = young_reasons
            results_with_similarity.append(result)
        results_with_similarity.sort(key=lambda x: x["distance"])
        final_results = results_with_similarity[:max_results]
        logger.info(f"✅ リアルタイムセマンティック検索完了: {len(final_results)}件")
        if final_results: logger.info(f"📊 最小距離: {final_results[0]['distance']:.4f}")
        return final_results
    except Exception as e:
        logger.error(f"❌ リアルタイムセマンティック検索エラー: {e}")
        raise

def calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    # (この関数は変更ありません)
    try:
        vec1, vec2 = np.array(vec1), np.array(vec2)
        norm1, norm2 = np.linalg.norm(vec1), np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0: return 0.0
        similarity = np.dot(vec1, vec2) / (norm1 * norm2)
        return float(similarity)
    except Exception as e:
        logger.warning(f"⚠️ コサイン類似度計算エラー: {e}")
        return 0.0

async def keyword_search(bq_client: bigquery.Client, query: str, max_results: int, university_filter: Optional[List[str]] = None, exclude_keywords: Optional[List[str]] = None) -> List[Dict]:
    # (この関数は変更ありません)
    try:
        logger.info(f"🔍 キーワード検索実行: {query}")
        keywords = [kw.strip() for kw in query.split() if kw.strip()]
        logger.info(f"📝 検索キーワード: {keywords}")
        like_conditions = []
        for keyword in keywords:
            safe_keyword = keyword.replace("'", "''")
            like_conditions.extend([ f"LOWER(research_keywords_ja) LIKE LOWER('%{safe_keyword}%')", f"LOWER(research_fields_ja) LIKE LOWER('%{safe_keyword}%')", f"LOWER(profile_ja) LIKE LOWER('%{safe_keyword}%')", f"LOWER(name_ja) LIKE LOWER('%{safe_keyword}%')", f"LOWER(paper_title_ja_first) LIKE LOWER('%{safe_keyword}%')", f"LOWER(project_title_ja_first) LIKE LOWER('%{safe_keyword}%')" ])
        where_clause = " OR ".join(like_conditions)
        relevance_scores = []
        for keyword in keywords:
            safe_keyword = keyword.replace("'", "''")
            relevance_scores.append(f""" ( CASE WHEN LOWER(name_ja) LIKE LOWER('%{safe_keyword}%') THEN 10 ELSE 0 END + CASE WHEN LOWER(research_keywords_ja) LIKE LOWER('%{safe_keyword}%') THEN 8 ELSE 0 END + CASE WHEN LOWER(research_fields_ja) LIKE LOWER('%{safe_keyword}%') THEN 6 ELSE 0 END + CASE WHEN LOWER(paper_title_ja_first) LIKE LOWER('%{safe_keyword}%') THEN 5 ELSE 0 END + CASE WHEN LOWER(project_title_ja_first) LIKE LOWER('%{safe_keyword}%') THEN 5 ELSE 0 END + CASE WHEN LOWER(profile_ja) LIKE LOWER('%{safe_keyword}%') THEN 4 ELSE 0 END ) """)
        total_relevance_score = " + ".join(relevance_scores) if relevance_scores else "0"
        university_condition = ""
        if university_filter and len(university_filter) > 0:
            try:
                from university_normalizer_fixed import get_university_normalization_sql
                safe_universities = [univ.replace("'", "''") for univ in university_filter]
                university_list = ",".join([f"'{univ}'" for univ in safe_universities])
                normalization_sql = get_university_normalization_sql("main_affiliation_name_ja")
                university_condition = f" AND ({normalization_sql}) IN ({university_list})"
            except Exception as e:
                logger.warning(f"⚠️ 大学正規化システムエラー、シンプルフィルターを使用: {e}")
                safe_universities = [univ.replace("'", "''") for univ in university_filter]
                like_conditions = [f"main_affiliation_name_ja LIKE '%{univ}%'" for univ in safe_universities]
                university_condition = f" AND ({' OR '.join(like_conditions)})"
        exclude_condition = ""
        if exclude_keywords:
            conditions = []
            for keyword in exclude_keywords:
                safe_keyword = keyword.replace("'", "''")
                conditions.append(f""" NOT ( LOWER(research_keywords_ja) LIKE LOWER('%{safe_keyword}%') OR LOWER(research_fields_ja) LIKE LOWER('%{safe_keyword}%') OR LOWER(profile_ja) LIKE LOWER('%{safe_keyword}%') ) """)
            if conditions: exclude_condition = f" AND {' AND '.join(conditions)}"
        search_sql = f""" SELECT name_ja, name_en, main_affiliation_name_ja, main_affiliation_name_en, main_affiliation_job_ja, main_affiliation_job_title_ja, main_affiliation_job_en, main_affiliation_job_title_en, research_keywords_ja, research_fields_ja, profile_ja, paper_title_ja_first, project_title_ja_first, researchmap_url, ({total_relevance_score}) as relevance_score FROM `apt-rope-217206.researcher_data.rd_250524` WHERE ({where_clause}){university_condition}{exclude_condition} ORDER BY relevance_score DESC, name_ja LIMIT {max_results} """
        query_job = bq_client.query(search_sql)
        results = []
        for row in query_job:
            researcher_data = { "name_ja": row.name_ja, "name_en": row.name_en, "main_affiliation_name_ja": row.main_affiliation_name_ja, "main_affiliation_name_en": row.main_affiliation_name_en, "main_affiliation_job_ja": row.main_affiliation_job_ja, "main_affiliation_job_title_ja": row.main_affiliation_job_title_ja, "main_affiliation_job_en": row.main_affiliation_job_en, "main_affiliation_job_title_en": row.main_affiliation_job_title_en, "research_keywords_ja": row.research_keywords_ja, "research_fields_ja": row.research_fields_ja, "profile_ja": row.profile_ja, "paper_title_ja_first": row.paper_title_ja_first, "project_title_ja_first": row.project_title_ja_first, "researchmap_url": row.researchmap_url, "relevance_score": float(row.relevance_score) if row.relevance_score else None }
            is_young, young_reasons = is_young_researcher(researcher_data)
            researcher_data["is_young_researcher"] = is_young
            researcher_data["young_researcher_reasons"] = young_reasons
            if '後藤' in researcher_data.get('name_ja', '') or '小松' in researcher_data.get('name_ja', ''):
                logger.info(f"🔍 検索 - {researcher_data.get('name_ja')}氏のデータ: ")
                logger.info(f"  - main_affiliation_job_ja: {researcher_data.get('main_affiliation_job_ja', 'NULL/MISSING')}")
                logger.info(f"  - main_affiliation_job_title_ja: {researcher_data.get('main_affiliation_job_title_ja', 'NULL/MISSING')}")
                logger.info(f"  - is_young_researcher: {is_young}")
                logger.info(f"  - young_researcher_reasons: {young_reasons}")
                logger.info(f"  - profile_ja[:300]: {str(researcher_data.get('profile_ja', ''))[:300]}")
                logger.info(f"  - 全フィールド: {list(researcher_data.keys())}")
                if 'main_affiliation_job_ja' not in researcher_data: logger.warning(f"  ⚠️ main_affiliation_job_ja カラムが存在しません！")
            results.append(researcher_data)
        logger.info(f"✅ キーワード検索完了: {len(results)}件")
        if results and len(results) > 0:
            first_result = results[0]
            logger.info(f"🔍 キーワード検索結果の最初のデータ:")
            logger.info(f"  - name_ja: {first_result.get('name_ja', 'N/A')}")
            logger.info(f"  - is_young_researcher: {first_result.get('is_young_researcher', 'MISSING')}")
            logger.info(f"  - young_researcher_reasons: {first_result.get('young_researcher_reasons', 'MISSING')}")
            logger.info(f"  - キーリスト: {list(first_result.keys())}")
        return results
    except Exception as e:
        logger.error(f"❌ キーワード検索エラー: {e}")
        raise

async def expand_query_with_llm(query: str) -> Dict[str, Any]:
    # (この関数は変更ありません)
    try:
        logger.info(f"🤖 LLMクエリ拡張開始: {query}")
        try:
            model = GenerativeModel("gemini-2.0-flash-001")
            prompt = f"""あなたは学術研究データベースの検索アシスタントです。 ユーザーが入力した「元のキーワード」について、そのキーワードを含む研究情報をより効果的に見つけるために、 関連性の高い類義語、上位/下位概念語、英語の対応語（もしあれば）、具体的な技術名や物質名などを考慮し、 検索に有効そうなキーワードを最大10個提案してください。 提案は日本語の単語または短いフレーズで、カンマ区切りで出力してください。元のキーワード自体も提案に含めてください。 元のキーワード: 「{query}」 提案:"""
            response = model.generate_content(prompt, generation_config={ "temperature": 0.2, "max_output_tokens": 200, "top_p": 0.8, "top_k": 40 })
            expanded_text = response.text.strip()
            if expanded_text:
                expanded_keywords = [kw.strip() for kw in expanded_text.split(',') if kw.strip()]
                final_keywords = []
                if query not in expanded_keywords: final_keywords.append(query)
                for kw in expanded_keywords:
                    if kw not in final_keywords: final_keywords.append(kw)
                logger.info(f"✅ LLMクエリ拡張完了 (gemini-2.0-flash-001): {final_keywords}")
                return { "original_query": query, "expanded_keywords": final_keywords, "expanded_query": ' '.join(final_keywords[:5]) }
        except Exception as e:
            logger.warning(f"⚠️ Gemini 2.0 Flash失敗: {e}")
            try:
                model = TextGenerationModel.from_pretrained("text-bison@002")
                prompt = f"""研究キーワード「{query}」に関連する学術用語を5-10個提案してください。カンマ区切りで出力してください。 元のキーワード: {query} 関連キーワード:"""
                response = model.predict(prompt, temperature=0.2, max_output_tokens=200, top_p=0.8, top_k=40)
                expanded_text = response.text.strip()
                if expanded_text:
                    expanded_keywords = [kw.strip() for kw in expanded_text.split(',') if kw.strip()]
                    final_keywords = [query] if query not in expanded_keywords else []
                    final_keywords.extend([kw for kw in expanded_keywords if kw not in final_keywords])
                    logger.info(f"✅ LLMクエリ拡張完了 (text-bison@002): {final_keywords}")
                    return { "original_query": query, "expanded_keywords": final_keywords, "expanded_query": ' '.join(final_keywords[:5]) }
            except Exception as e2: logger.warning(f"⚠️ Text-Bison フォールバック失敗: {e2}")
        logger.warning("⚠️ すべてのLLMモデルでクエリ拡張に失敗")
        return { "original_query": query, "expanded_keywords": [query], "expanded_query": query }
    except Exception as e:
        logger.error(f"❌ LLMクエリ拡張エラー: {e}")
        return { "original_query": query, "expanded_keywords": [query], "expanded_query": query }

async def add_llm_summaries(results: List[Dict], query: str) -> List[Dict]:
    # (この関数は変更ありません)
    try:
        logger.info(f"🤖 LLM要約生成開始: {len(results)}名の研究者")
        model, model_name = None, ""
        try:
            model = GenerativeModel("gemini-2.0-flash-lite-001")
            model_name = "gemini-2.0-flash-lite-001"
            logger.info(f"✅ 軽量LLMモデル {model_name} を使用")
        except Exception as e:
            logger.warning(f"⚠️ Gemini 2.0 Flash Lite失敗: {e}")
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
                if idx > 0: time.sleep(0.5)
                name, affiliation, keywords, fields, profile, paper, project = result.get('name_ja', ''), result.get('main_affiliation_name_ja', ''), result.get('research_keywords_ja', ''), result.get('research_fields_ja', ''), str(result.get('profile_ja', ''))[:300], result.get('paper_title_ja_first', ''), result.get('project_title_ja_first', '')
                prompt = f"""研究者情報:\n名前: {name} ({affiliation})\n研究キーワード: {keywords}\n研究分野: {fields}\nプロフィール: {profile}\n主要論文: {paper}\n主要プロジェクト: {project}\n\n検索クエリ: 「{query}」\n\n上記の研究キーワード、プロフィール、主要論文、主要プロジェクトを踏まえて、 この研究者と検索クエリとの関連性を200字程度で分析してください。"""
                summary = ""
                if "gemini" in model_name:
                    response = model.generate_content(prompt, generation_config={ "temperature": 0.1, "max_output_tokens": 200, "top_p": 0.8 })
                    summary = response.text.strip()
                else:
                    response = model.predict(prompt, temperature=0.1, max_output_tokens=200, top_p=0.8)
                    summary = response.text.strip()
                if summary: result["llm_summary"] = summary
                else: result["llm_summary"] = f"「{query}」に関連する研究を行っています。"
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
        return results