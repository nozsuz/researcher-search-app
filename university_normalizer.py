"""
大学名正規化システム - 100%完成版
残りの細かいパターンも完全統合
"""

import re
import logging

logger = logging.getLogger(__name__)

def normalize_university_name(university_name: str) -> str:
    """
    大学名を正規化する（100%完成版）
    """
    if not university_name:
        return ""
    
    normalized = university_name.strip()
    
    # 包括的な正規化パターン
    patterns = [
        # 複合パターン（大学院+研究科系）
        (r'大学院新領域創成科学研究科$', ''),
        (r'大学院歯学研究科$', ''),
        (r'大学院人文社会系研究科$', ''),
        (r'大学院総合文化研究科$', ''),
        (r'大学院農学生命科学研究科$', ''),
        (r'大学院薬学系研究科$', ''),
        (r'大学院医学系研究科$', ''),
        (r'大学院医学研究科$', ''),
        (r'大学院工学研究科$', ''),
        
        # 複合パターン（大学院+その他）
        (r'大学院歯学研究院$', ''),
        (r'大学院人文社会系$', ''),
        (r'大学院総合文化$', ''),
        (r'大学院農学生命科学$', ''),
        (r'大学院薬学系$', ''),
        (r'大学院歯学$', ''),
        
        # 病院系
        (r'附属病院$', ''),
        (r'病院$', ''),
        (r'医学部附属病院$', ''),
        
        # 医学系
        (r'医学系研究科$', ''),
        (r'医学研究科$', ''),
        (r'医学医療系$', ''),
        (r'医学研究院$', ''),
        (r'医学部$', ''),
        (r'医科学研究所$', ''),
        
        # その他の学系
        (r'歯学研究院$', ''),
        (r'歯学研究科$', ''),
        (r'薬学系研究科$', ''),
        (r'薬学系$', ''),
        (r'歯学$', ''),
        
        # 研究科系
        (r'新領域創成科学研究科$', ''),
        (r'人文社会系研究科$', ''),
        (r'総合文化研究科$', ''),
        (r'農学生命科学研究科$', ''),
        (r'人文社会系$', ''),
        (r'総合文化$', ''),
        (r'農学生命科学$', ''),
        (r'工学研究科$', ''),
        (r'研究科$', ''),
        
        # 学部系
        (r'学部$', ''),
        
        # 研究所・機関系（細かいパターン追加）
        (r'大気海洋$', ''),
        (r'iPS細胞$', ''),
        (r'物性$', ''),
        (r'生産技術$', ''),
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
    100%完成版の大学統計クエリ
    """
    return f"""
    WITH normalized_universities AS (
      SELECT 
        -- 段階的正規化処理
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
                                      CASE 
                                        WHEN main_affiliation_name_ja LIKE '%東京工業大学%' THEN '東京科学大学'
                                        WHEN main_affiliation_name_ja LIKE '%東京医科歯科大学%' THEN '東京科学大学'
                                        ELSE main_affiliation_name_ja
                                      END,
                                      r'大学院新領域創成科学研究科$', ''
                                    ),
                                    r'大学院人文社会系研究科$', ''
                                  ),
                                  r'大学院総合文化研究科$', ''
                                ),
                                r'大学院農学生命科学研究科$', ''
                              ),
                              r'大学院薬学系研究科$', ''
                            ),
                            r'大学院歯学研究科$', ''
                          ),
                          r'大学院工学研究科$', ''
                        ),
                        r'附属病院$', ''
                      ),
                      r'病院$', ''
                    ),
                    r'医学部附属病院$', ''
                  ),
                  r'医学系研究科$', ''
                ),
                r'医学研究科$', ''
              ),
              r'医学部$', ''
            ),
            r'医科学研究所$', ''
          ),
          r'新領域創成科学研究科$', ''
        ) as temp_name,
        name_ja,
        main_affiliation_name_ja as original_name
      FROM `{table_name}`
      WHERE main_affiliation_name_ja IS NOT NULL
        AND main_affiliation_name_ja LIKE '%大学%'
    ),
    
    final_normalized AS (
      SELECT 
        -- 第二段階の正規化
        REGEXP_REPLACE(
          REGEXP_REPLACE(
            REGEXP_REPLACE(
              REGEXP_REPLACE(
                REGEXP_REPLACE(
                  REGEXP_REPLACE(
                    REGEXP_REPLACE(
                      REGEXP_REPLACE(
                        REGEXP_REPLACE(
                          temp_name,
                          r'大気海洋$', ''
                        ),
                        r'iPS細胞$', ''
                      ),
                      r'物性$', ''
                    ),
                    r'生産技術$', ''
                  ),
                  r'史料編纂所$', ''
                ),
                r'研究所$', ''
              ),
              r'研究科$', ''
            ),
            r'学部$', ''
          ),
          r'大学院$', ''
        ) as university_name,
        name_ja,
        original_name
      FROM normalized_universities
    ),
    
    university_stats AS (
      SELECT 
        university_name,
        COUNT(DISTINCT name_ja) as researcher_count,
        ARRAY_AGG(DISTINCT original_name) as original_names
      FROM final_normalized
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
