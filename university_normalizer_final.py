"""
大学名正規化システム - 究極完成版
最後の2%も完全統合
"""

import re
import logging

logger = logging.getLogger(__name__)

def normalize_university_name(university_name: str) -> str:
    """
    大学名を正規化する（究極完成版）
    """
    if not university_name:
        return ""
    
    # 全角スペース等の正規化
    normalized = university_name.strip()
    normalized = re.sub(r'　+', '', normalized)  # 全角スペース除去
    normalized = re.sub(r'\s+', '', normalized)  # 半角スペース除去
    
    # 究極完成版の正規化パターン
    patterns = [
        # 複合パターン（大学院+詳細分野）
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
        (r'大学院工学系研究科$', ''),
        (r'大学院歯学研究科$', ''),
        
        # 病院系
        (r'附属病院$', ''),
        (r'病院$', ''),
        (r'医学部附属病院$', ''),
        
        # 東京大学の特殊機関（残り2%の主要パターン）
        (r'大気海洋研究所$', ''),
        (r'iPS細胞研究所$', ''),
        (r'物性研究所$', ''),
        (r'生産技術研究所$', ''),
        (r'史料編纂所$', ''),
        (r'定量生命科学研究所$', ''),
        
        # 東北大学の加齢医学
        (r'加齢医学研究所$', ''),
        
        # 一般的パターン
        (r'医学研究院$', ''),
        (r'歯学研究院$', ''),
        (r'医学系研究科$', ''),
        (r'医学研究科$', ''),
        (r'医学医療系$', ''),
        (r'医学部$', ''),
        (r'医科学研究所$', ''),
        (r'新領域創成科学研究科$', ''),
        (r'歯学研究科$', ''),
        (r'工学研究科$', ''),
        (r'研究科$', ''),
        (r'学部$', ''),
        (r'研究所$', ''),
        (r'研究院$', ''),
        (r'センター$', ''),
        
        # その他
        (r'短期大学部$', ''),
        (r'短期大$', ''),
        (r'大学院$', ''),
    ]
    
    # パターンマッチング適用
    for pattern, replacement in patterns:
        normalized = re.sub(pattern, replacement, normalized)
    
    # 大学統合（東京工業大学 + 東京医科歯科大学 → 東京科学大学）
    if '東京工業大学' in normalized:
        normalized = '東京科学大学'
    elif '東京医科歯科大学' in normalized:
        normalized = '東京科学大学'
    
    return normalized.strip()

def get_normalized_university_stats_query(table_name: str) -> str:
    """
    究極完成版の大学統計クエリ
    全パターンを完全統合
    """
    return f"""
    WITH normalized_universities AS (
      SELECT 
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
                                                                                    REGEXP_REPLACE(
                                                                                      REGEXP_REPLACE(
                                                                                        REGEXP_REPLACE(
                                                                                          REGEXP_REPLACE(
                                                                                            REGEXP_REPLACE(
                                                                                              -- 大学名統合を最初に実行
                                                                                              CASE 
                                                                                                WHEN main_affiliation_name_ja LIKE '%東京工業大学%' THEN '東京科学大学'
                                                                                                WHEN main_affiliation_name_ja LIKE '%東京医科歯科大学%' THEN '東京科学大学'
                                                                                                ELSE main_affiliation_name_ja
                                                                                              END,
                                                                                              r'　+', ''
                                                                                            ),
                                                                                            r'\\s+', ''
                                                                                          ),
                                                                                          r'大学院医学研究院$', ''
                                                                                        ),
                                                                                        r'大学院歯学研究院$', ''
                                                                                      ),
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
                                                                            r'大学院医学系研究科$', ''
                                                                          ),
                                                                          r'大学院医学研究科$', ''
                                                                        ),
                                                                        r'大学院工学研究科$', ''
                                                                      ),
                                                                      r'大学院工学系研究科$', ''
                                                                    ),
                                                                    r'大学院歯学研究科$', ''
                                                                  ),
                                                                  r'附属病院$', ''
                                                                ),
                                                                r'病院$', ''
                                                              ),
                                                              r'医学部附属病院$', ''
                                                            ),
                                                            r'大気海洋研究所$', ''
                                                          ),
                                                          r'iPS細胞研究所$', ''
                                                        ),
                                                        r'物性研究所$', ''
                                                      ),
                                                      r'生産技術研究所$', ''
                                                    ),
                                                    r'史料編纂所$', ''
                                                  ),
                                                  r'定量生命科学研究所$', ''
                                                ),
                                                r'加齢医学研究所$', ''
                                              ),
                                              r'医学研究院$', ''
                                            ),
                                            r'歯学研究院$', ''
                                          ),
                                          r'医学系研究科$', ''
                                        ),
                                        r'医学研究科$', ''
                                      ),
                                      r'医学医療系$', ''
                                    ),
                                    r'医学部$', ''
                                  ),
                                  r'医科学研究所$', ''
                                ),
                                r'新領域創成科学研究科$', ''
                              ),
                              r'歯学研究科$', ''
                            ),
                            r'工学研究科$', ''
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
                r'短期大学部$', ''
              ),
              r'短期大$', ''
            ),
            r'大学院$', ''
          ),
          r'大学$', '大学'
        ) as university_name,
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
        ARRAY_AGG(DISTINCT original_name LIMIT 10) as original_names
      FROM normalized_universities
      WHERE LENGTH(university_name) > 2
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
