"""
大学名正規化システム - 修正版（東海国立大学機構対応）
"""

import re
import logging

logger = logging.getLogger(__name__)

def normalize_university_name(university_name: str) -> str:
    """
    大学名を正規化する（東海国立大学機構対応版）
    """
    if not university_name:
        return ""
    
    # スペース正規化
    normalized = university_name.strip()
    normalized = re.sub(r'　+', '', normalized)  # 全角スペース除去
    normalized = re.sub(r'\s+', '', normalized)  # 半角スペース除去
    
    # 特殊ケース：東海国立大学機構の処理（最優先）
    if '東海国立大学機構' in normalized:
        # 名古屋大学が含まれている場合
        if '名古屋大学' in normalized:
            base_name = '名古屋大学'
        # 岐阜大学が含まれている場合
        elif '岐阜大学' in normalized:
            base_name = '岐阜大学'
        else:
            # 機構名のみの場合は「東海国立大学機構」として扱う
            base_name = '東海国立大学機構'
        
        # さらに後続の部分を除去
        normalized = base_name
    
    # 法人格の除去
    patterns_legal = [
        (r'^国立大学法人', ''),
        (r'^公立大学法人', ''),
        (r'^学校法人', ''),
        (r'^独立行政法人', ''),
    ]
    
    for pattern, replacement in patterns_legal:
        normalized = re.sub(pattern, replacement, normalized)
    
    # 機構名の除去（東海国立大学機構以外）
    normalized = re.sub(r'機構', '', normalized)
    
    # 基本的な正規化パターン
    patterns = [
        # 病院系
        (r'附属病院$', ''),
        (r'病院$', ''),
        (r'医学部附属病院$', ''),
        
        # 研究科・学部系
        (r'大学院医学研究科$', ''),
        (r'大学院工学研究科$', ''),
        (r'大学院.*研究科$', ''),
        (r'医学研究科$', ''),
        (r'工学研究科$', ''),
        (r'研究科$', ''),
        (r'学部$', ''),
        
        # 研究所・機関系
        (r'医科学研究所$', ''),
        (r'研究所$', ''),
        (r'研究院$', ''),
        (r'センター$', ''),
        
        # その他
        (r'大学院$', ''),
    ]
    
    # 東海国立大学機構処理後でない場合のみ通常の正規化を適用
    if '東海国立大学機構' not in university_name:
        for pattern, replacement in patterns:
            normalized = re.sub(pattern, replacement, normalized)
    
    # 大学統合
    if '東京工業大学' in normalized:
        normalized = '東京科学大学'
    elif '東京医科歯科大学' in normalized:
        normalized = '東京科学大学'
    
    return normalized.strip()

def get_university_normalization_sql(column_name: str) -> str:
    """
    SQLでの大学正規化（東海国立大学機構対応版）
    """
    return f"""
    CASE
      -- 東海国立大学機構の特殊処理
      WHEN {column_name} LIKE '%東海国立大学機構%' AND {column_name} LIKE '%名古屋大学%' THEN '名古屋大学'
      WHEN {column_name} LIKE '%東海国立大学機構%' AND {column_name} LIKE '%岐阜大学%' THEN '岐阜大学'
      WHEN {column_name} LIKE '%東海国立大学機構%' THEN '東海国立大学機構'
      
      -- 統合処理
      WHEN {column_name} LIKE '%東京工業大学%' THEN '東京科学大学'
      WHEN {column_name} LIKE '%東京医科歯科大学%' THEN '東京科学大学'
      
      -- 通常の正規化処理
      ELSE REGEXP_REPLACE(
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
                                    {column_name},
                                    r'　+', ''
                                  ),
                                  r'\\s+', ''
                                ),
                                r'^国立大学法人', ''
                              ),
                              r'^公立大学法人', ''
                            ),
                            r'^学校法人', ''
                          ),
                          r'^独立行政法人', ''
                        ),
                        r'機構', ''
                      ),
                      r'附属病院$', ''
                    ),
                    r'病院$', ''
                  ),
                  r'大学院.*研究科$', ''
                ),
                r'研究科$', ''
              ),
              r'学部$', ''
            ),
            r'研究所$', ''
          ),
          r'研究院$', ''
        ),
        r'大学院$', ''
      )
    END
    """
