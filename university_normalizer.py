"""
大学名正規化システム - シンプル版
BigQueryエラーを避けるための基本的な正規化のみ
"""

import re
import logging

logger = logging.getLogger(__name__)

def normalize_university_name(university_name: str) -> str:
    """
    大学名を正規化する（シンプル版）
    """
    if not university_name:
        return ""
    
    normalized = university_name.strip()
    
    # 基本的な附属機関の除去
    patterns = [
        (r'附属病院$', ''),
        (r'史料編纂所$', ''),
        (r'医学医療系$', ''),
        (r'医学研究院$', ''),
        (r'総合研究博物館$', ''),
        (r'病院$', ''),
        (r'大学院$', ''),
    ]
    
    for pattern, replacement in patterns:
        normalized = re.sub(pattern, replacement, normalized)
    
    # 大学統合
    if '東京工業大学' in normalized:
        normalized = '東京科学大学'
    elif '東京医科歯科大学' in normalized:
        normalized = '東京科学大学'
    
    return normalized.strip()

def get_normalized_university_stats_query(table_name: str) -> str:
    """
    シンプルな大学統計クエリ
    """
    return f"""
    WITH normalized_universities AS (
      SELECT 
        CASE 
          WHEN main_affiliation_name_ja LIKE '%東京工業大学%' THEN '東京科学大学'
          WHEN main_affiliation_name_ja LIKE '%東京医科歯科大学%' THEN '東京科学大学'
          WHEN main_affiliation_name_ja LIKE '%附属病院' THEN REGEXP_REPLACE(main_affiliation_name_ja, '附属病院$', '')
          WHEN main_affiliation_name_ja LIKE '%史料編纂所' THEN REGEXP_REPLACE(main_affiliation_name_ja, '史料編纂所$', '')
          WHEN main_affiliation_name_ja LIKE '%医学医療系' THEN REGEXP_REPLACE(main_affiliation_name_ja, '医学医療系$', '')
          WHEN main_affiliation_name_ja LIKE '%医学研究院' THEN REGEXP_REPLACE(main_affiliation_name_ja, '医学研究院$', '')
          WHEN main_affiliation_name_ja LIKE '%総合研究博物館' THEN REGEXP_REPLACE(main_affiliation_name_ja, '総合研究博物館$', '')
          WHEN main_affiliation_name_ja LIKE '%病院' THEN REGEXP_REPLACE(main_affiliation_name_ja, '病院$', '')
          WHEN main_affiliation_name_ja LIKE '%大学院' THEN REGEXP_REPLACE(main_affiliation_name_ja, '大学院$', '')
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
