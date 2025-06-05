"""
実際の研究者検索機能（評価システム統合版）
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
    若手研究者かどうかを判定（第三段階まで実装）
    
    Returns:
        Tuple[bool, List[str]]: (若手研究者フラグ, 判定理由のリスト)
    """
    reasons = []
    
    # デバッグ用ログ
    name = researcher_data.get('name_ja', 'Unknown')
    logger.debug(f"🔍 若手研究者判定開始: {name}")
    
    # 第2段階を先に実施：プロフィールキーワードによる判定
    profile_ja = (researcher_data.get('profile_ja', '') or '').lower()
    
    # プロフィール内の職位情報を優先的にチェック
    profile_positions = [
        '特任研究員', '特任講師', '特任助教', '助教', '准教授', 
        '博士研究員', 'ポスドク', '研究員', '助手', '講師',
        '博士後期課程', '博士課程', 'ポストドクトラル',
        '日本学術振興会特別研究員', 'jsps特別研究員', '特別研究員',
        '博士学生', '大学院生', '医員'
    ]
    
    # 現在の職位を確認するためのより幅広いパターン
    current_position_patterns = [
        r'\d{4}年\s*-\s*(.+)',  # "2023年- 特任助教"
        r'\d{4}年\s*～\s*(.+)',  # "2023年～ 特任助教"
        r'\d{4}年\s*から\s*(.+)',  # "2023年から 特任助教"
        r'現在\s*[：:]?\s*(.+)',  # "現在：特任助教"
    ]
    
    for pattern in current_position_patterns:
        match = re.search(pattern, profile_ja)
        if match:
            position_text = match.group(1).lower()
            for pos in profile_positions:
                if pos in position_text:
                    reasons.append(f"現職(プロフィール): {pos}")
                    break
            if reasons:
                break
    
    # 第1段階：職位カラムによる判定（データがある場合のみ）
    job_ja = (researcher_data.get('main_affiliation_job_ja', '') or '').lower()
    job_title_ja = (researcher_data.get('main_affiliation_job_title_ja', '') or '').lower()
    job_en = (researcher_data.get('main_affiliation_job_en', '') or '').lower()
    job_title_en = (researcher_data.get('main_affiliation_job_title_en', '') or '').lower()
    
    # 若手研究者の職位（日本語）
    young_positions_ja = [
        '助教', '准教授', '博士研究員', 'ポスドク', '研究員', 
        '特任助教', '特任准教授', '助手', '講師', '特任研究員',
        '博士後期課程', '博士課程', 'ポストドクトラル', '日本学術振興会特別研究員',
        'jsps特別研究員', '特別研究員', '博士学生', '大学院生'
    ]
    
    # 若手研究者の職位（英語）
    young_positions_en = [
        'assistant', 'associate professor', 'postdoc', 'researcher', 
        'fellow', 'doctoral', 'phd student', 'graduate student',
        'research associate', 'post-doctoral', 'jsps fellow'
    ]
    
    # シニア研究者の職位（除外条件）
    senior_positions_ja = ['教授', '名誉教授', '客員教授', '特任教授', '主席研究員', '統括']
    senior_positions_en = ['professor', 'emeritus', 'director', 'principal', 'chief']
    
    # 職位チェック
    for pos in young_positions_ja:
        if pos in job_ja or pos in job_title_ja:
            # シニアポジションでないことを確認
            is_senior = any(sp in job_ja or sp in job_title_ja for sp in senior_positions_ja)
            if not is_senior:
                reasons.append(f"職位: {pos}")
                break
    
    for pos in young_positions_en:
        if pos in job_en or pos in job_title_en:
            # シニアポジションでないことを確認
            is_senior = any(sp in job_en or sp in job_title_en for sp in senior_positions_en)
            if not is_senior and 'full professor' not in job_en.lower():
                reasons.append(f"職位(英): {pos}")
                break
    
    # 第2段階：プロフィールキーワードによる追加判定
    
    # 若手研究者を示すキーワード
    young_keywords = [
        '若手', '新進気鋭', 'early career', '博士課程', '博士取得',
        '学位取得', 'キャリア初期', '研究員として', '採用され',
        '着任', '博士号取得', 'ph.d.取得', '学振', 'jsps',
        '育志賞', '若手研究者賞', '奨励賞'
    ]
    
    # 平成生まれのパターン（若手指標）
    heisei_pattern = r'平成元年生まれ|平成\d+年生まれ'
    if re.search(heisei_pattern, profile_ja):
        match = re.search(heisei_pattern, profile_ja)
        birth_text = match.group(0)
        # 平成元年 = 1989年
        if '平成元年' in birth_text:
            birth_year = 1989
        else:
            heisei_year = int(re.search(r'\d+', birth_text).group(0))
            birth_year = 1988 + heisei_year
        
        current_year = datetime.now().year
        age = current_year - birth_year
        if age <= 45:  # 45歳以下
            reasons.append(f"生年: {birth_text}（{age}歳）")
    
    for keyword in young_keywords:
        if keyword in profile_ja:
            reasons.append(f"キーワード: {keyword}")
            break
    
    # 第3段階：年次情報からの推定
    current_year = datetime.now().year
    
    # 博士号取得年の抽出
    phd_patterns = [
        r'(\d{4})年.*?博士.*?取得',
        r'(\d{4})年.*?ph\.?d\.?',
        r'博士.*?(\d{4})年',
        r'ph\.?d\.?.*?(\d{4})',
        r'(\d{4})年.*?学位',
        r'(\d{4})年.*?博士課程.*?修了'
    ]
    
    for pattern in phd_patterns:
        match = re.search(pattern, profile_ja)
        if match:
            year = int(match.group(1))
            years_since = current_year - year
            if 0 <= years_since <= 15:  # 博士取得後15年以内
                reasons.append(f"博士取得: {year}年（{years_since}年前）")
                break
    
    # 最初の論文発表年からの推定
    paper_title = researcher_data.get('paper_title_ja_first', '')
    paper_year_match = re.search(r'\[(\d{4})\]', paper_title) or re.search(r'(\d{4})年', paper_title)
    if paper_year_match:
        first_paper_year = int(paper_year_match.group(1))
        years_active = current_year - first_paper_year
        if 0 <= years_active <= 10:  # 研究活動開始から10年以内
            reasons.append(f"研究開始: {first_paper_year}年（{years_active}年前）")
    
    # 年齢に関する直接的な記述
    age_patterns = [
        r'(\d{2})歳',
        r'(\d{4})年生まれ',
        r'(\d{4})年.*?誕生'
    ]
    
    for pattern in age_patterns:
        match = re.search(pattern, profile_ja)
        if match:
            if '歳' in pattern:
                age = int(match.group(1))
                if 25 <= age <= 45:  # 若手研究者の年齢範囲
                    reasons.append(f"年齢: {age}歳")
            else:
                birth_year = int(match.group(1))
                age = current_year - birth_year
                if 25 <= age <= 45:
                    reasons.append(f"生年: {birth_year}年（{age}歳）")
            break
    
    # プロフィール内の年次パターンを使った現職判定
    current_year = datetime.now().year
    for i in range(current_year - 5, current_year + 1):  # 過去5年から現在まで
        year_pattern = f"{i}年-|〜{i}年|{i}年～"
        if re.search(year_pattern, profile_ja):
            # その年以降の職位を確認
            for pos in profile_positions:
                if pos in profile_ja:
                    reasons.append(f"現職(プロフィール): {pos} ({i}年～)")
                    break
            break
    
    # 総合判定
    is_young = len(reasons) > 0
    
    # 特別な除外条件の確認
    exclusion_keywords = ['退職', '名誉', '元教授', '元所長', '顧問', '理事長', '学長', '総長']
    for keyword in exclusion_keywords:
        if keyword in profile_ja or keyword in job_ja or keyword in job_title_ja:
            is_young = False
            reasons = [f"除外条件: {keyword}"]
            break
    
    # デバッグ用ログ
    logger.debug(f"🎯 若手判定結果: {name} - {is_young} - {reasons}")
    
    return is_young, reasons

async def perform_real_search(request) -> Dict[str, Any]:
    """
    実際の研究者検索を実行（評価システム統合版）
    """
    start_time = time.time()
    
    try:
        logger.info(f"🔍 実際の検索開始: {request.query}, method: {request.method}")
        logger.info(f"📊 全パラメータ: query={request.query}, method={request.method}, max_results={request.max_results}, use_llm_expansion={request.use_llm_expansion}, use_llm_summary={request.use_llm_summary}, use_internal_evaluation={getattr(request, 'use_internal_evaluation', 'NONE')}")
        
        # 内部評価モードは無効化（常にFalse）
        use_internal_evaluation = False
        # AI要約モードの判定
        use_ai_summary = request.use_llm_summary
        # 若手研究者フィルタリング
        young_researcher_filter = getattr(request, 'young_researcher_filter', False)
        logger.info(f"📊 評価モード: 標準検索")
        logger.info(f"📊 AI要約: {'ON' if use_ai_summary else 'OFF'}")
        
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
        
        # 若手研究者フィルタリング
        if young_researcher_filter and results:
            logger.info(f"🌟 若手研究者フィルタリングを実行")
            filtered_results = []
            for result in results:
                if result.get('is_young_researcher', False):
                    filtered_results.append(result)
                    logger.info(f"  ✅ {result.get('name_ja', 'Unknown')}: {result.get('young_researcher_reasons', [])}")
                else:
                    logger.debug(f"  ❌ {result.get('name_ja', 'Unknown')}: 若手研究者ではない")
            
            logger.info(f"🌟 フィルタリング結果: {len(results)}件 → {len(filtered_results)}件")
            results = filtered_results
        
        # 評価システムによる処理（AI関連性分析を統合）
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
                    "executed_query_info": f"AI関連性分析実行 (方法: {request.method}, 実行時間: {execution_time:.2f}秒)",
                    "expanded_info": expanded_info
                }
                
            except Exception as e:
                logger.error(f"❌ AI関連性分析でエラー: {e}")
                import traceback
                logger.error(f"スタックトレース: {traceback.format_exc()}")
                # エラー時は従来方式にフォールバック
                use_internal_evaluation = False
        
        # 従来方式の処理（内部評価がOFFの場合）
        if not use_internal_evaluation:
            # AI要約が要求されている場合
            if use_ai_summary and results and vertex_ai_available:
                try:
                    results = await add_llm_summaries(results, request.query)
                    logger.info("🤖 AI要約を追加完了")
                except Exception as e:
                    logger.warning(f"⚠️ AI要約生成失敗: {e}")
        
        execution_time = time.time() - start_time
        
        # 実行情報を生成
        executed_query_info = f"実際のGCP検索実行 (方法: {request.method}"
        if use_internal_evaluation:
            executed_query_info += ", 評価モード: 内部評価"
        if request.use_llm_expansion and vertex_ai_available and request.method != "semantic":
            executed_query_info += ", キーワード拡張: ON"
        if use_ai_summary and vertex_ai_available:
            executed_query_info += ", AI要約: ON"
        executed_query_info += f", 実行時間: {execution_time:.2f}秒)"
        
        # 拡張情報のデバッグ出力
        if expanded_info:
            logger.info(f"🏷️ レスポンスに拡張情報を含めます: {expanded_info}")
        else:
            logger.info("🏷️ 拡張情報なし")
        
        # 結果返却前の最終確認
        if results and len(results) > 0:
            logger.info(f"🔍 最終結果返却前のデータ確認:")
            first_result = results[0]
            logger.info(f"  - 最初の結果のname: {first_result.get('name_ja', 'N/A')}")
            logger.info(f"  - is_young_researcher: {first_result.get('is_young_researcher', 'MISSING')}")
            logger.info(f"  - young_researcher_reasons: {first_result.get('young_researcher_reasons', 'MISSING')}")
            logger.info(f"  - 結果のキー: {list(first_result.keys())}")
        
        response_data = {
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
        
        logger.info(f"📦 APIレスポンスデータのキー: {list(response_data.keys())}")
        
        return response_data
        
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
                
                # DataFrameのカラム名を確認
                logger.info(f"📊 DataFrame columns: {list(df.columns)}")
                
                for idx, row in df.iterrows():
                    result = {}
                    
                    # 各カラムをチェックしてデータを取得
                    for col in df.columns:
                        value = row[col]
                        
                        # distanceカラムはそのままコピー
                        if col == 'distance':
                            result['distance'] = value
                        
                        # baseカラムが存在する場合
                        elif col == 'base' and isinstance(value, dict):
                            # base内のすべてのキーをトップレベルにコピー
                            for key, val in value.items():
                                result[key] = val
                        
                        # ネストされたカラム名の場合（例： base.name_ja）
                        elif '.' in col:
                            # ドットの後の部分をキー名として使用
                            key_name = col.split('.')[-1]
                            result[key_name] = value
                        
                        # 通常のカラム
                        else:
                            result[col] = value
                    
                    # デバッグログ：最初の結果のみ
                    if idx == 0:
                        logger.info(f"🔍 セマンティック検索結果の確認:")
                        logger.info(f"  - result keys: {list(result.keys())}")
                        logger.info(f"  - name_ja: {result.get('name_ja', 'NOT FOUND')}")
                    
                    # 若手研究者判定
                    is_young, young_reasons = is_young_researcher(result)
                    result["is_young_researcher"] = is_young
                    result["young_researcher_reasons"] = young_reasons
                    
                    # デバッグ：若手研究者フィールドが追加されたか確認
                    if idx == 0:
                        logger.info(f"  - is_young_researcher: {result.get('is_young_researcher', 'NOT FOUND')}")
                        logger.info(f"  - young_researcher_reasons: {result.get('young_researcher_reasons', 'NOT FOUND')}")
                    
                    # 特定の研究者のデバッグ情報
                    if '後藤' in result.get('name_ja', '') or '小松' in result.get('name_ja', ''):
                        logger.info(f"🔍 セマンティック検索 - {result.get('name_ja')}氏のデータ: ")
                        logger.info(f"  - main_affiliation_job_ja: {result.get('main_affiliation_job_ja', 'NULL/MISSING')}")
                        logger.info(f"  - main_affiliation_job_title_ja: {result.get('main_affiliation_job_title_ja', 'NULL/MISSING')}")
                        logger.info(f"  - is_young_researcher: {is_young}")
                        logger.info(f"  - young_researcher_reasons: {young_reasons}")
                        logger.info(f"  - profile_ja[:300]: {str(result.get('profile_ja', ''))[:300]}")
                    
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
            main_affiliation_job_ja,
            main_affiliation_job_title_ja,
            main_affiliation_job_en,
            main_affiliation_job_title_en,
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
                    "main_affiliation_job_ja": row.main_affiliation_job_ja,
                    "main_affiliation_job_title_ja": row.main_affiliation_job_title_ja,
                    "main_affiliation_job_en": row.main_affiliation_job_en,
                    "main_affiliation_job_title_en": row.main_affiliation_job_title_en,
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
            
            # 若手研究者判定
            is_young, young_reasons = is_young_researcher(result)
            result["is_young_researcher"] = is_young
            result["young_researcher_reasons"] = young_reasons
            
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
            main_affiliation_job_ja,
            main_affiliation_job_title_ja,
            main_affiliation_job_en,
            main_affiliation_job_title_en,
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
            # 基本データを収集
            researcher_data = {
                "name_ja": row.name_ja,
                "name_en": row.name_en,
                "main_affiliation_name_ja": row.main_affiliation_name_ja,
                "main_affiliation_name_en": row.main_affiliation_name_en,
                "main_affiliation_job_ja": row.main_affiliation_job_ja,
                "main_affiliation_job_title_ja": row.main_affiliation_job_title_ja,
                "main_affiliation_job_en": row.main_affiliation_job_en,
                "main_affiliation_job_title_en": row.main_affiliation_job_title_en,
                "research_keywords_ja": row.research_keywords_ja,
                "research_fields_ja": row.research_fields_ja,
                "profile_ja": row.profile_ja,
                "paper_title_ja_first": row.paper_title_ja_first,
                "project_title_ja_first": row.project_title_ja_first,
                "researchmap_url": row.researchmap_url,
                "relevance_score": float(row.relevance_score) if row.relevance_score else None
            }
            
            # 若手研究者判定
            is_young, young_reasons = is_young_researcher(researcher_data)
            researcher_data["is_young_researcher"] = is_young
            researcher_data["young_researcher_reasons"] = young_reasons
            
            # 特定の研究者のデバッグ情報
            if '後藤' in researcher_data.get('name_ja', '') or '小松' in researcher_data.get('name_ja', ''):
                logger.info(f"🔍 検索 - {researcher_data.get('name_ja')}氏のデータ: ")
                logger.info(f"  - main_affiliation_job_ja: {researcher_data.get('main_affiliation_job_ja', 'NULL/MISSING')}")
                logger.info(f"  - main_affiliation_job_title_ja: {researcher_data.get('main_affiliation_job_title_ja', 'NULL/MISSING')}")
                logger.info(f"  - is_young_researcher: {is_young}")
                logger.info(f"  - young_researcher_reasons: {young_reasons}")
                logger.info(f"  - profile_ja[:300]: {str(researcher_data.get('profile_ja', ''))[:300]}")
                logger.info(f"  - 全フィールド: {list(researcher_data.keys())}")
                # 職位カラムの存在を確認
                if 'main_affiliation_job_ja' not in researcher_data:
                    logger.warning(f"  ⚠️ main_affiliation_job_ja カラムが存在しません！")
            
            results.append(researcher_data)
        
        logger.info(f"✅ キーワード検索完了: {len(results)}件")
        
        # デバッグ：最初の結果の若手研究者フィールドを確認
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
                
                # 研究者情報を収集（セマンティック/キーワード検索共通）
                name = result.get('name_ja', '')
                affiliation = result.get('main_affiliation_name_ja', '')
                keywords = result.get('research_keywords_ja', '')
                fields = result.get('research_fields_ja', '')
                profile = str(result.get('profile_ja', ''))[:300]  # 300文字まで
                paper = result.get('paper_title_ja_first', '')
                project = result.get('project_title_ja_first', '')
                
                # 統一されたプロンプト（全情報を含む）
                prompt = f"""研究者情報:
名前: {name} ({affiliation})
研究キーワード: {keywords}
研究分野: {fields}
プロフィール: {profile}
主要論文: {paper}
主要プロジェクト: {project}

検索クエリ: 「{query}」

上記の研究キーワード、プロフィール、主要論文、主要プロジェクトを踏まえて、
この研究者と検索クエリとの関連性を200字程度で分析してください。"""
                
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
