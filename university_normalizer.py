"""
大学名正規化システム - 包括的パターン対応版
すべての複合パターンに対応
"""

import re
import logging

logger = logging.getLogger(__name__)

def normalize_university_name(university_name: str) -> str:
    """
    大学名を正規化する（包括的パターン対応版）
    """
    if not university_name:
        return ""
    
    normalized = university_name.strip()
    
    # 包括的な正規化パターン（長いパターンから先に処理）
    patterns = [
        # 複合パターン（大学院+学部/研究科系）
        (r'大学院歯学研究院$', ''),
        (r'大学院人文社会系$', ''),
        (r'大学院総合文化$', ''),
        (r'大学院農学生命科学$', ''),
        (r'大学院薬学系$', ''),
        (r'大学院歯学$', ''),
        (r'大学院医学系研究科$', ''),
        (r'大学院医学研究科$', ''),
        (r'大学院工学研究科$', ''),
        (r'大学院理学研究科$', ''),
        (r'大学院文学研究科$', ''),
        (r'大学院法学研究科$', ''),
        (r'大学院経済学研究科$', ''),
        
        # 医学系（複合）
        (r'医学部附属病院$', ''),
        (r'医学系研究科$', ''),
        (r'医学研究科$', ''),
        (r'医学医療系$', ''),
        (r'医学研究院$', ''),
        (r'医学部$', ''),
        (r'医科学研究所$', ''),
        
        # その他の学系
        (r'歯学研究院$', ''),
        (r'薬学系$', ''),
        (r'歯学$', ''),
        
        # 研究科系
        (r'人文社会系$', ''),
        (r'総合文化$', ''),
        (r'農学生命科学$', ''),
        (r'工学研究科$', ''),
        (r'理学研究科$', ''),
        (r'文学研究科$', ''),
        (r'法学研究科$', ''),
        (r'経済学研究科$', ''),
        (r'研究科$', ''),
        
        # 学部系
        (r'工学部$', ''),
        (r'理学部$', ''),
        (r'文学部$', ''),
        (r'法学部$', ''),
        (r'経済学部$', ''),
        (r'学部$', ''),
        
        # 研究所・機関系
        (r'生産技術$', ''),
        (r'史料編纂所$', ''),
        (r'総合研究博物館$', ''),
        (r'核物理研究センター$', ''),
        (r'金属材料研究所$', ''),
        (r'研究所$', ''),
        (r'センター$', ''),
        (r'研究院$', ''),
        
        # 病院系
        (r'附属病院$', ''),
        (r'病院$', ''),
        
        # その他（最後に処理）
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
    包括的パターン対応の大学統計クエリ
    """
    return f"""
    WITH normalized_universities AS (
      SELECT 
        CASE 
          -- 大学統合
          WHEN main_affiliation_name_ja LIKE '%東京工業大学%' THEN '東京科学大学'
          WHEN main_affiliation_name_ja LIKE '%東京医科歯科大学%' THEN '東京科学大学'
          
          -- 複合パターン（大学院+学部/研究科系）
          WHEN main_affiliation_name_ja LIKE '%大学院歯学研究院' THEN REGEXP_REPLACE(main_affiliation_name_ja, '大学院歯学研究院$', '')
          WHEN main_affiliation_name_ja LIKE '%大学院人文社会系' THEN REGEXP_REPLACE(main_affiliation_name_ja, '大学院人文社会系$', '')
          WHEN main_affiliation_name_ja LIKE '%大学院総合文化' THEN REGEXP_REPLACE(main_affiliation_name_ja, '大学院総合文化$', '')
          WHEN main_affiliation_name_ja LIKE '%大学院農学生命科学' THEN REGEXP_REPLACE(main_affiliation_name_ja, '大学院農学生命科学$', '')
          WHEN main_affiliation_name_ja LIKE '%大学院薬学系' THEN REGEXP_REPLACE(main_affiliation_name_ja, '大学院薬学系$', '')
          WHEN main_affiliation_name_ja LIKE '%大学院歯学' THEN REGEXP_REPLACE(main_affiliation_name_ja, '大学院歯学$', '')
          WHEN main_affiliation_name_ja LIKE '%大学院医学系研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '大学院医学系研究科$', '')
          WHEN main_affiliation_name_ja LIKE '%大学院医学研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '大学院医学研究科$', '')
          WHEN main_affiliation_name_ja LIKE '%大学院工学研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '大学院工学研究科$', '')
          WHEN main_affiliation_name_ja LIKE '%大学院理学研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '大学院理学研究科$', '')
          WHEN main_affiliation_name_ja LIKE '%大学院文学研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '大学院文学研究科$', '')
          WHEN main_affiliation_name_ja LIKE '%大学院法学研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '大学院法学研究科$', '')
          WHEN main_affiliation_name_ja LIKE '%大学院経済学研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '大学院経済学研究科$', '')
          
          -- 医学系（複合）
          WHEN main_affiliation_name_ja LIKE '%医学部附属病院' THEN REGEXP_REPLACE(main_affiliation_name_ja, '医学部附属病院$', '')
          WHEN main_affiliation_name_ja LIKE '%医学系研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '医学系研究科$', '')
          WHEN main_affiliation_name_ja LIKE '%医学研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '医学研究科$', '')
          WHEN main_affiliation_name_ja LIKE '%医学医療系' THEN REGEXP_REPLACE(main_affiliation_name_ja, '医学医療系$', '')
          WHEN main_affiliation_name_ja LIKE '%医学研究院' THEN REGEXP_REPLACE(main_affiliation_name_ja, '医学研究院$', '')
          WHEN main_affiliation_name_ja LIKE '%医学部' THEN REGEXP_REPLACE(main_affiliation_name_ja, '医学部$', '')
          WHEN main_affiliation_name_ja LIKE '%医科学研究所' THEN REGEXP_REPLACE(main_affiliation_name_ja, '医科学研究所$', '')
          
          -- その他の学系
          WHEN main_affiliation_name_ja LIKE '%歯学研究院' THEN REGEXP_REPLACE(main_affiliation_name_ja, '歯学研究院$', '')
          WHEN main_affiliation_name_ja LIKE '%薬学系' THEN REGEXP_REPLACE(main_affiliation_name_ja, '薬学系$', '')
          WHEN main_affiliation_name_ja LIKE '%歯学' THEN REGEXP_REPLACE(main_affiliation_name_ja, '歯学$', '')
          
          -- 研究科系
          WHEN main_affiliation_name_ja LIKE '%人文社会系' THEN REGEXP_REPLACE(main_affiliation_name_ja, '人文社会系$', '')
          WHEN main_affiliation_name_ja LIKE '%総合文化' THEN REGEXP_REPLACE(main_affiliation_name_ja, '総合文化$', '')
          WHEN main_affiliation_name_ja LIKE '%農学生命科学' THEN REGEXP_REPLACE(main_affiliation_name_ja, '農学生命科学$', '')
          WHEN main_affiliation_name_ja LIKE '%工学研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '工学研究科$', '')
          WHEN main_affiliation_name_ja LIKE '%理学研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '理学研究科$', '')
          WHEN main_affiliation_name_ja LIKE '%文学研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '文学研究科$', '')
          WHEN main_affiliation_name_ja LIKE '%法学研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '法学研究科$', '')
          WHEN main_affiliation_name_ja LIKE '%経済学研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '経済学研究科$', '')
          WHEN main_affiliation_name_ja LIKE '%研究科' THEN REGEXP_REPLACE(main_affiliation_name_ja, '研究科$', '')
          
          -- 学部系
          WHEN main_affiliation_name_ja LIKE '%工学部' THEN REGEXP_REPLACE(main_affiliation_name_ja, '工学部$', '')
          WHEN main_affiliation_name_ja LIKE '%理学部' THEN REGEXP_REPLACE(main_affiliation_name_ja, '理学部$', '')
          WHEN main_affiliation_name_ja LIKE '%文学部' THEN REGEXP_REPLACE(main_affiliation_name_ja, '文学部$', '')
          WHEN main_affiliation_name_ja LIKE '%法学部' THEN REGEXP_REPLACE(main_affiliation_name_ja, '法学部$', '')
          WHEN main_affiliation_name_ja LIKE '%経済学部' THEN REGEXP_REPLACE(main_affiliation_name_ja, '経済学部$', '')
          WHEN main_affiliation_name_ja LIKE '%学部' THEN REGEXP_REPLACE(main_affiliation_name_ja, '学部$', '')
          
          -- 研究所・機関系
          WHEN main_affiliation_name_ja LIKE '%生産技術' THEN REGEXP_REPLACE(main_affiliation_name_ja, '生産技術$', '')
          WHEN main_affiliation_name_ja LIKE '%史料編纂所' THEN REGEXP_REPLACE(main_affiliation_name_ja, '史料編纂所$', '')
          WHEN main_affiliation_name_ja LIKE '%総合研究博物館' THEN REGEXP_REPLACE(main_affiliation_name_ja, '総合研究博物館$', '')
          WHEN main_affiliation_name_ja LIKE '%核物理研究センター' THEN REGEXP_REPLACE(main_affiliation_name_ja, '核物理研究センター$', '')
          WHEN main_affiliation_name_ja LIKE '%金属材料研究所' THEN REGEXP_REPLACE(main_affiliation_name_ja, '金属材料研究所$', '')
          WHEN main_affiliation_name_ja LIKE '%研究所' THEN REGEXP_REPLACE(main_affiliation_name_ja, '研究所$', '')
          WHEN main_affiliation_name_ja LIKE '%センター' THEN REGEXP_REPLACE(main_affiliation_name_ja, 'センター$', '')
          WHEN main_affiliation_name_ja LIKE '%研究院' THEN REGEXP_REPLACE(main_affiliation_name_ja, '研究院$', '')
          
          -- 病院系
          WHEN main_affiliation_name_ja LIKE '%附属病院' THEN REGEXP_REPLACE(main_affiliation_name_ja, '附属病院$', '')
          WHEN main_affiliation_name_ja LIKE '%病院' THEN REGEXP_REPLACE(main_affiliation_name_ja, '病院$', '')
          
          -- その他（最後に処理）
          WHEN main_affiliation_name_ja LIKE '%短期大' THEN REGEXP_REPLACE(main_affiliation_name_ja, '短期大$', '')
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
