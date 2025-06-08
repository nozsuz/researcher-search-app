"""
大学名正規化システム - 修正版（シンプル実装）
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
    
    # スペース正規化
    normalized = university_name.strip()
    normalized = re.sub(r'　+', '', normalized)  # 全角スペース除去
    normalized = re.sub(r'\s+', '', normalized)  # 半角スペース除去
    
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
    SQLでの大学正規化（シンプル版）
    """
    return f"""
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
                          WHEN {column_name} LIKE '%東京工業大学%' THEN '東京科学大学'
                          WHEN {column_name} LIKE '%東京医科歯科大学%' THEN '東京科学大学'
                          ELSE {column_name}
                        END,
                        r'　+', ''
                      ),
                      r'\\s+', ''
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
    """
