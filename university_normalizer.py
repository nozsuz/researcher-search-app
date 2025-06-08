"""
大学名正規化システム - 修正版
「大学大学」重複問題を解決
"""

import re
import logging

logger = logging.getLogger(__name__)

def normalize_university_name(university_name: str) -> str:
    """
    大学名を正規化する（重複除去版）
    """
    if not university_name:
        return ""
    
    # 全角スペース等の正規化
    normalized = university_name.strip()
    normalized = re.sub(r'　+', '', normalized)  # 全角スペース除去
    normalized = re.sub(r'\s+', '', normalized)  # 半角スペース除去
    
    # 基本的な正規化パターン
    patterns = [
        # 複合パターン（大学院+学科/研究院）
        (r'大学院医学研究院$', ''),
        (r'大学院歯学研究院$', ''),
        (r'大学院新領域創成科学研究科$', ''),
        (r'大学院人文社会系研究科$', ''),
        (r'大学院総合文化研究科$', ''),
        (r'大学院農学生命科学研究科$', ''),
        (r'大学院薬学系研究科$', ''),
        (r'大学院医学系研究科$', ''),
        (r'大学院医学研究科$', ''),
        (r'大学院工学研究科$', ''),
        
        # 病院系
        (r'附属病院$', ''),
        (r'病院$', ''),
        (r'医学部附属病院$', ''),
        
        # 医学系
        (r'医学研究院$', ''),
        (r'歯学研究院$', ''),
        (r'医学系研究科$', ''),
        (r'医学研究科$', ''),
        (r'医学医療系$', ''),
        (r'医学部$', ''),
        (r'医科学研究所$', ''),
        
        # 研究科系
        (r'新領域創成科学研究科$', ''),
        (r'人文社会系研究科$', ''),
        (r'総合文化研究科$', ''),
        (r'農学生命科学研究科$', ''),
        (r'薬学系研究科$', ''),
        (r'歯学研究科$', ''),
        (r'工学研究科$', ''),
        (r'研究科$', ''),
        
        # 学部系
        (r'学部$', ''),
        
        # 研究所・機関系
        (r'史料編纂所$', ''),
        (r'研究所$', ''),
        (r'センター$', ''),
        (r'研究院$', ''),
        
        # その他
        (r'短期大学部$', ''),
        (r'短期大$', ''),
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
    改良版の大学統計クエリ（重複除去対応）
    """
    return f"""
    WITH step1_normalize AS (
      SELECT 
        -- 基本的な正規化（スペース除去、特別な統合）
        CASE
          -- 東京科学大学統合
          WHEN main_affiliation_name_ja LIKE '%東京工業大学%' THEN '東京科学大学'
          WHEN main_affiliation_name_ja LIKE '%東京医科歯科大学%' THEN '東京科学大学'
          ELSE main_affiliation_name_ja
        END as normalized_name,
        name_ja,
        main_affiliation_name_ja as original_name
      FROM `{table_name}`
      WHERE main_affiliation_name_ja IS NOT NULL
        AND main_affiliation_name_ja LIKE '%大学%'
    ),
    
    step2_extract AS (
      SELECT 
        -- 国立大学法人を除去して大学名を抽出
        CASE
          WHEN normalized_name LIKE '国立大学法人%' THEN
            REGEXP_REPLACE(normalized_name, r'^国立大学法人\\s*', '')
          ELSE normalized_name
        END as temp_name,
        name_ja,
        original_name
      FROM step1_normalize
    ),
    
    step3_clean AS (
      SELECT 
        -- 研究科、学部、研究所等の除去
        REGEXP_REPLACE(
          REGEXP_REPLACE(
            REGEXP_REPLACE(
              REGEXP_REPLACE(
                REGEXP_REPLACE(
                  REGEXP_REPLACE(
                    REGEXP_REPLACE(
                      REGEXP_REPLACE(
                        REGEXP_REPLACE(
                          REGEXP_REPLACE(
                            REGEXP_REPLACE(
                              REGEXP_REPLACE(
                                REGEXP_REPLACE(
                                  REGEXP_REPLACE(
                                    REGEXP_REPLACE(
                                      REGEXP_REPLACE(
                                        REGEXP_REPLACE(
                                          REGEXP_REPLACE(
                                            REGEXP_REPLACE(
                                              REGEXP_REPLACE(temp_name, r'大学院.*$', ''),
                                              r'研究科.*$', ''
                                            ),
                                            r'学部.*$', ''
                                          ),
                                          r'研究所.*$', ''
                                        ),
                                        r'研究院.*$', ''
                                      ),
                                      r'医学部.*$', ''
                                    ),
                                    r'附属.*$', ''
                                  ),
                                  r'病院.*$', ''
                                ),
                                r'センター.*$', ''
                              ),
                              r'短期大学部$', ''
                            ),
                            r'短期大$', ''
                          ),
                          r'　+', ''
                        ),
                        r'\\s+', ''
                      ),
                      r'大学院$', ''
                    ),
                    r'研究科$', ''
                  ),
                  r'学部$', ''
                ),
                r'研究所$', ''
              ),
              r'研究院$', ''
            ),
            r'センター$', ''
          ),
          r'病院$', ''
        ) as university_name,
        name_ja,
        original_name
      FROM step2_extract
    ),
    
    university_stats AS (
      SELECT 
        university_name,
        COUNT(DISTINCT name_ja) as researcher_count,
        ARRAY_AGG(DISTINCT original_name) as original_names
      FROM step3_clean
      WHERE university_name != ''
        AND university_name IS NOT NULL
        AND LENGTH(university_name) > 0
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
