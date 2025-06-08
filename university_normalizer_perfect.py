"""
大学名正規化システム - 完璧版（残り5%も完全統合）
"""

import re
import logging

logger = logging.getLogger(__name__)

def normalize_university_name(university_name: str) -> str:
    """
    大学名を正規化する（完璧版 - 残り5%も統合）
    """
    if not university_name:
        return ""
    
    # 全角スペース等の正規化
    normalized = university_name.strip()
    normalized = re.sub(r'　+', '', normalized)  # 全角スペース除去
    normalized = re.sub(r'\s+', '', normalized)  # 半角スペース除去
    
    # 完璧版の正規化パターン（残り5%対応）
    patterns = [
        # 最新の細かいパターン（現在のリストから）
        (r'大学院人間・環境学研究科$', ''),
        (r'大学院工学研究科$', ''),
        (r'大学院教育学研究科$', ''),
        (r'大学院理学系研究科$', ''),
        (r'遺伝子病制御研究所$', ''),
        (r'生体防御医学研究所$', ''),
        (r'地震研究所$', ''),
        (r'歯学部$', ''),
        (r'歯学研究科$', ''),
        (r'歯$', ''),  # 短縮形対応
        
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
        (r'大学院人間・環境学$', ''),  # 新追加
        (r'大学院教育学$', ''),      # 新追加
        (r'大学院理学系$', ''),      # 新追加
        
        # 病院系
        (r'附属病院$', ''),
        (r'病院$', ''),
        (r'医学部附属病院$', ''),
        
        # 東京大学の特殊機関
        (r'大気海洋研究所$', ''),
        (r'iPS細胞研究所$', ''),
        (r'物性研究所$', ''),
        (r'生産技術研究所$', ''),
        (r'史料編纂所$', ''),
        (r'定量生命科学研究所$', ''),
        (r'地震研究所$', ''),        # 新追加
        
        # 東北大学・北海道大学の特殊機関
        (r'加齢医学研究所$', ''),
        (r'遺伝子病制御研究所$', ''), # 新追加
        (r'生体防御医学研究所$', ''), # 新追加
        
        # 国立大学法人パターン（新追加）
        (r'^国立大学法人東海国立大学機構', ''),
        (r'^国立大学法人東京科学大学', '東京科学大学'),
        (r'^国立大学法人', ''),
        
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
    
    # 国立大学法人名古屋大学の特別処理
    if '国立大学法人東海国立大学機構名古屋大学' in university_name:
        return '名古屋大学'
    
    return normalized.strip()

def get_normalized_university_stats_query(table_name: str) -> str:
    """
    完璧版の大学統計クエリ（残り5%も完全統合）
    """
    return f"""
    WITH normalized_universities AS (
      SELECT 
        CASE
          -- 国立大学法人パターンの特別処理を最初に実行
          WHEN main_affiliation_name_ja LIKE '%国立大学法人東海国立大学機構名古屋大学%' THEN '名古屋大学'
          WHEN main_affiliation_name_ja LIKE '%国立大学法人東京科学大学%' THEN '東京科学大学'
          WHEN main_affiliation_name_ja LIKE '%東京工業大学%' THEN '東京科学大学'
          WHEN main_affiliation_name_ja LIKE '%東京医科歯科大学%' THEN '東京科学大学'
          ELSE
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
                                                                                                  REGEXP_REPLACE(
                                                                                                    -- スペース正規化
                                                                                                    REGEXP_REPLACE(
                                                                                                      REGEXP_REPLACE(
                                                                                                        main_affiliation_name_ja,
                                                                                                        r'　+', ''
                                                                                                      ),
                                                                                                      r'\\s+', ''
                                                                                                    ),
                                                                                                    r'^国立大学法人東海国立大学機構', ''
                                                                                                  ),
                                                                                                  r'^国立大学法人', ''
                                                                                                ),
                                                                                                r'大学院人間・環境学研究科$', ''
                                                                                              ),
                                                                                              r'大学院工学研究科$', ''
                                                                                            ),
                                                                                            r'大学院教育学研究科$', ''
                                                                                          ),
                                                                                          r'大学院理学系研究科$', ''
                                                                                        ),
                                                                                        r'遺伝子病制御研究所$', ''
                                                                                      ),
                                                                                      r'生体防御医学研究所$', ''
                                                                                    ),
                                                                                    r'地震研究所$', ''
                                                                                  ),
                                                                                  r'歯学部$', ''
                                                                                ),
                                                                                r'歯学研究科$', ''
                                                                              ),
                                                                              r'歯$', ''
                                                                            ),
                                                                            r'大学院人間・環境学$', ''
                                                                          ),
                                                                          r'大学院教育学$', ''
                                                                        ),
                                                                        r'大学院理学系$', ''
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
                                                    r'大学院工学系研究科$', ''
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
              r'研究科$', ''
            )
        END as university_name,
        name_ja,
        main_affiliation_name_ja as original_name
      FROM `{table_name}`
      WHERE main_affiliation_name_ja IS NOT NULL
        AND main_affiliation_name_ja LIKE '%大学%'
    ),
    
    final_normalized AS (
      SELECT 
        -- 最終段階の正規化
        REGEXP_REPLACE(
          REGEXP_REPLACE(
            REGEXP_REPLACE(
              REGEXP_REPLACE(
                REGEXP_REPLACE(
                  university_name,
                  r'学部$', ''
                ),
                r'研究所$', ''
              ),
              r'研究院$', ''
            ),
            r'センター$', ''
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
        ARRAY_AGG(DISTINCT original_name LIMIT 10) as original_names
      FROM final_normalized
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
