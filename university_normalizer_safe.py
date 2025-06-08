"""
大学正規化システム - 簡易修正版
複雑なルールでエラーが発生する場合の安全なフォールバック
"""

import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

def normalize_university_name_simple(university_name: str) -> str:
    """
    簡易版大学名正規化
    複雑なルールを避けて基本的な正規化のみ実行
    """
    if not university_name:
        return ""
    
    try:
        # 基本的な正規化ルール
        normalized = university_name.strip()
        
        # 明らかな附属機関の除去
        simple_patterns = [
            (r'附属病院$', ''),
            (r'附属学校$', ''),
            (r'史料編纂所$', ''),
            (r'総合研究博物館$', ''),
            (r'医学研究院$', ''),
            (r'医学医療系$', ''),
            (r'核物理研究センター$', ''),
            (r'金属材料研究所$', ''),
            (r'大学院$', ''),
            (r'病院$', ''),
        ]
        
        for pattern, replacement in simple_patterns:
            normalized = re.sub(pattern, replacement, normalized)
        
        # 重複する大学の統合
        university_mergers = {
            "東京工業大学": "東京科学大学",
            "東京医科歯科大学": "東京科学大学",
        }
        
        if normalized in university_mergers:
            normalized = university_mergers[normalized]
        
        return normalized.strip()
        
    except Exception as e:
        logger.warning(f"⚠️ 簡易正規化でエラー: {e}, 元の名前を返します: {university_name}")
        return university_name

def get_simple_university_stats_query(table_name: str) -> str:
    """
    簡易版大学統計クエリ
    複雑な正規化を避けた安全なバージョン
    """
    try:
        query = f"""
        WITH normalized_universities AS (
          SELECT 
            CASE 
              -- 基本的な正規化のみ
              WHEN main_affiliation_name_ja LIKE '%附属病院' THEN REGEXP_REPLACE(main_affiliation_name_ja, '附属病院$', '')
              WHEN main_affiliation_name_ja LIKE '%史料編纂所' THEN REGEXP_REPLACE(main_affiliation_name_ja, '史料編纂所$', '')
              WHEN main_affiliation_name_ja LIKE '%医学研究院' THEN REGEXP_REPLACE(main_affiliation_name_ja, '医学研究院$', '')
              WHEN main_affiliation_name_ja LIKE '%医学医療系' THEN REGEXP_REPLACE(main_affiliation_name_ja, '医学医療系$', '')
              WHEN main_affiliation_name_ja = '東京工業大学' THEN '東京科学大学'
              WHEN main_affiliation_name_ja = '東京医科歯科大学' THEN '東京科学大学'
              ELSE main_affiliation_name_ja
            END as university_name,
            name_ja,
            main_affiliation_name_ja as original_name
          FROM `{table_name}`
          WHERE main_affiliation_name_ja IS NOT NULL
            AND main_affiliation_name_ja LIKE '%大学%'
        ),
        
        university_stats AS (
          SELECT 
            university_name,
            COUNT(DISTINCT name_ja) as researcher_count,
            ARRAY_AGG(DISTINCT original_name) as original_names
          FROM normalized_universities
          GROUP BY university_name
          HAVING COUNT(DISTINCT name_ja) >= 5
        )
        
        SELECT 
          university_name,
          researcher_count,
          original_names
        FROM university_stats
        ORDER BY researcher_count DESC
        LIMIT 100
        """
        
        return query
        
    except Exception as e:
        logger.error(f"❌ 簡易クエリ生成エラー: {e}")
        # さらに簡単なフォールバック
        fallback_query = f"""
        SELECT 
          main_affiliation_name_ja as university_name,
          COUNT(DISTINCT name_ja) as researcher_count,
          [main_affiliation_name_ja] as original_names
        FROM `{table_name}`
        WHERE main_affiliation_name_ja IS NOT NULL
          AND main_affiliation_name_ja LIKE '%大学%'
        GROUP BY main_affiliation_name_ja
        HAVING COUNT(DISTINCT name_ja) >= 5
        ORDER BY researcher_count DESC
        LIMIT 50
        """
        return fallback_query

def get_normalized_university_stats_query_safe(table_name: str) -> str:
    """
    安全な大学統計クエリ生成
    エラーハンドリング付きで複数のレベルのフォールバックを提供
    """
    try:
        # まず元の複雑なクエリを試行
        from university_normalizer import get_normalized_university_stats_query
        return get_normalized_university_stats_query(table_name)
    except ImportError:
        logger.warning("⚠️ 元の正規化モジュールが見つかりません。簡易版を使用します。")
        return get_simple_university_stats_query(table_name)
    except Exception as e:
        logger.warning(f"⚠️ 元の正規化クエリでエラー: {e}。簡易版を使用します。")
        return get_simple_university_stats_query(table_name)

# 安全な正規化関数のエイリアス
def normalize_university_name_safe(university_name: str) -> str:
    """
    安全な大学名正規化
    元の関数が失敗した場合の簡易版フォールバック付き
    """
    try:
        # まず元の正規化を試行
        from university_normalizer import normalize_university_name
        return normalize_university_name(university_name)
    except ImportError:
        logger.warning("⚠️ 元の正規化モジュールが見つかりません。簡易版を使用します。")
        return normalize_university_name_simple(university_name)
    except Exception as e:
        logger.warning(f"⚠️ 元の正規化でエラー: {e}。簡易版を使用します。")
        return normalize_university_name_simple(university_name)
