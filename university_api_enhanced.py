"""
大学API強化版モジュール
エラーハンドリングとフォールバック機能付き
"""

import time
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

async def get_universities_enhanced(PROJECT_ID: str, BIGQUERY_TABLE: str) -> Dict[str, Any]:
    """
    強化された大学リスト取得機能
    詳細なエラーハンドリングとフォールバック機能付き
    """
    start_time = time.time()
    
    try:
        logger.info("🏫 大学リスト取得開始")
        
        # Step 1: モジュールのインポートテスト
        try:
            from gcp_auth import get_bigquery_client, get_gcp_status
            from university_normalizer import get_normalized_university_stats_query
            logger.info("✅ 必要モジュールのインポート成功")
        except ImportError as e:
            logger.error(f"❌ モジュールインポートエラー: {e}")
            return await get_universities_fallback("module_import_error", str(e))
        
        # Step 2: GCP状況確認
        gcp_status = get_gcp_status()
        logger.info(f"📊 GCP状況: {gcp_status}")
        
        bq_client = get_bigquery_client()
        
        if not bq_client:
            logger.warning("⚠️ BigQueryクライアントが利用できません - フォールバックモード")
            return await get_universities_fallback("bigquery_unavailable", "BigQueryクライアントが初期化されていません")
        
        # Step 3: 正規化クエリの生成と検証
        try:
            query = get_normalized_university_stats_query(BIGQUERY_TABLE)
            logger.info(f"✅ 正規化クエリ生成成功: {len(query)}文字")
            
            # クエリの最初の部分をログ出力（デバッグ用）
            logger.debug(f"📄 クエリ先頭: {query[:200]}...")
            
        except Exception as e:
            logger.error(f"❌ 正規化クエリ生成エラー: {e}")
            return await get_universities_fallback("query_generation_error", str(e))
        
        # Step 4: BigQueryクエリ実行
        try:
            logger.info("🔍 BigQueryクエリ実行開始")
            query_job = bq_client.query(query)
            
            universities = []
            normalization_details = []
            row_count = 0
            
            logger.info("⏳ クエリ結果の処理中...")
            
            for row in query_job:
                row_count += 1
                
                # 基本的な大学情報
                university_data = {
                    "name": row.university_name,
                    "count": row.researcher_count
                }
                
                # 正規化の詳細情報を含める
                if hasattr(row, 'original_names') and row.original_names:
                    university_data["original_names"] = row.original_names
                    if len(row.original_names) > 1:
                        normalization_details.append({
                            "normalized_name": row.university_name,
                            "original_names": row.original_names,
                            "consolidated_count": row.researcher_count
                        })
                
                universities.append(university_data)
                
                # 最初の10件をログ出力
                if row_count <= 10:
                    original_info = ""
                    if hasattr(row, 'original_names') and row.original_names and len(row.original_names) > 1:
                        original_info = f" (統合: {len(row.original_names)}校)"
                    logger.info(f"  {row_count}. {row.university_name}: {row.researcher_count}名{original_info}")
            
            execution_time = time.time() - start_time
            
            response = {
                "status": "success",
                "total_universities": len(universities),
                "universities": universities,
                "normalization_info": {
                    "method": "dynamic_rule_based",
                    "consolidated_universities": len(normalization_details),
                    "details": normalization_details[:10]  # 上位10件の詳細のみ
                },
                "execution_time": execution_time,
                "query_stats": {
                    "rows_processed": row_count,
                    "query_length": len(query)
                }
            }
            
            logger.info(f"✅ 大学リスト取得完了: {len(universities)}校 (正規化統合: {len(normalization_details)}校) {execution_time:.2f}秒")
            return response
            
        except Exception as e:
            logger.error(f"❌ BigQueryクエリ実行エラー: {e}")
            import traceback
            logger.error(f"📋 エラーの詳細: {traceback.format_exc()}")
            return await get_universities_fallback("bigquery_execution_error", str(e))
            
    except Exception as e:
        logger.error(f"❌ 大学リスト取得で予期しないエラー: {e}")
        import traceback
        logger.error(f"📋 エラーの詳細: {traceback.format_exc()}")
        return await get_universities_fallback("unexpected_error", str(e))

async def get_universities_fallback(error_type: str, error_message: str) -> Dict[str, Any]:
    """
    大学リスト取得のフォールバック機能
    実際のデータが取得できない場合のモックデータ
    """
    logger.warning(f"🔄 フォールバックモード実行: {error_type}")
    
    # 問題解決された後に期待される結果を模擬
    mock_universities = [
        {"name": "東京大学", "count": 2150, "note": "統合後"},
        {"name": "京都大学", "count": 1890, "note": "統合後"},
        {"name": "大阪大学", "count": 1654, "note": "統合後"},
        {"name": "東北大学", "count": 1543, "note": "統合後"},
        {"name": "筑波大学", "count": 1432, "note": "統合後（附属病院・医学医療系含む）"},
        {"name": "九州大学", "count": 1321, "note": "統合後（病院・博物館含む）"},
        {"name": "北海道大学", "count": 1298, "note": "統合後（医学研究院含む）"},
        {"name": "名古屋大学", "count": 1245, "note": "統合後"},
        {"name": "東京科学大学", "count": 1187, "note": "統合後（東工大・東京医科歯科大）"},
        {"name": "慶應義塾大学", "count": 1098, "note": "統合後"}
    ]
    
    return {
        "status": "fallback",
        "total_universities": len(mock_universities),
        "universities": mock_universities,
        "fallback_info": {
            "reason": error_type,
            "error_message": error_message,
            "note": "これはモックデータです。実際の正規化システムの修復後、正確なデータが表示されます。"
        },
        "normalization_info": {
            "method": "mock_data",
            "consolidated_universities": 5,
            "note": "実際のシステムでは動的正規化が適用されます"
        }
    }

async def get_universities_simple(PROJECT_ID: str, BIGQUERY_TABLE: str) -> Dict[str, Any]:
    """
    簡略化された大学リスト取得（問題解決用）
    複雑な正規化を行わない基本版
    """
    try:
        from gcp_auth import get_bigquery_client
        
        bq_client = get_bigquery_client()
        
        if bq_client:
            # シンプルなクエリ（正規化なし）
            simple_query = f"""
            SELECT 
                main_affiliation_name_ja as university_name,
                COUNT(DISTINCT name_ja) as researcher_count
            FROM `{BIGQUERY_TABLE}`
            WHERE main_affiliation_name_ja IS NOT NULL
              AND main_affiliation_name_ja LIKE '%大学%'
            GROUP BY main_affiliation_name_ja
            HAVING COUNT(DISTINCT name_ja) >= 5
            ORDER BY researcher_count DESC
            LIMIT 50
            """
            
            logger.info("🔍 シンプル大学クエリ実行")
            query_job = bq_client.query(simple_query)
            
            universities = []
            for row in query_job:
                universities.append({
                    "name": row.university_name,
                    "count": row.researcher_count
                })
            
            return {
                "status": "success",
                "mode": "simple",
                "total_universities": len(universities),
                "universities": universities,
                "note": "正規化なしの基本データです"
            }
        else:
            return await get_universities_fallback("bigquery_unavailable", "BigQueryクライアントが利用できません")
            
    except Exception as e:
        logger.error(f"❌ シンプル大学リスト取得エラー: {e}")
        return await get_universities_fallback("simple_query_error", str(e))

def test_university_api_components() -> Dict[str, Any]:
    """
    大学API機能の詳細なテスト
    """
    test_results = {
        "timestamp": time.time(),
        "tests": {}
    }
    
    # 1. モジュールインポートテスト
    try:
        from gcp_auth import get_bigquery_client, get_gcp_status
        from university_normalizer import get_normalized_university_stats_query, normalize_university_name
        test_results["tests"]["module_import"] = {
            "status": "✅ 成功",
            "message": "必要なモジュールがすべてインポートできました"
        }
    except Exception as e:
        test_results["tests"]["module_import"] = {
            "status": "❌ 失敗",
            "error": str(e)
        }
        return test_results
    
    # 2. 正規化機能テスト
    try:
        test_cases = [
            "筑波大学附属病院",
            "東京大学史料編纂所", 
            "九州大学総合研究博物館"
        ]
        
        normalization_results = []
        for case in test_cases:
            normalized = normalize_university_name(case)
            normalization_results.append({
                "original": case,
                "normalized": normalized,
                "changed": case != normalized
            })
        
        test_results["tests"]["normalization"] = {
            "status": "✅ 成功",
            "results": normalization_results
        }
    except Exception as e:
        test_results["tests"]["normalization"] = {
            "status": "❌ 失敗",
            "error": str(e)
        }
    
    return test_results
