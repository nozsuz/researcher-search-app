"""
大学名正規化システム - シンプル版（修正版）
○○大学+{任意の文字} → ○○大学 に統合
"""

import re
import logging

logger = logging.getLogger(__name__)

def normalize_university_name(university_name: str) -> str:
    """
    大学名を正規化する（シンプル版・修正版）
    ○○大学+{任意の文字} → ○○大学 に統合
    「国立大学法人」等の法人格を除去
    """
    if not university_name:
        return ""
    
    # 全角・半角スペース除去
    normalized = university_name.strip()
    normalized = re.sub(r'[\s　]+', '', normalized)
    
    # 法人格の除去
    normalized = re.sub(r'^国立大学法人', '', normalized)
    normalized = re.sub(r'^公立大学法人', '', normalized) 
    normalized = re.sub(r'^学校法人', '', normalized)
    normalized = re.sub(r'^独立行政法人', '', normalized)
    
    # 大学名の基本パターンを抽出
    # "○○大学" の部分を正しく抽出する
    match = re.search(r'(.+?大学)', normalized)
    if match:
        base_university = match.group(1)
        
        # 特殊な統合処理
        if '東京工業大学' in base_university:
            return '東京科学大学'
        elif '東京医科歯科大学' in base_university:
            return '東京科学大学'
        else:
            return base_university
    
    # "大学"が含まれていない場合はそのまま返す
    return normalized

def get_normalized_university_stats_query(table_name: str) -> str:
    """
    シンプル版の大学統計クエリ（修正版）
    REGEXP_EXTRACTを使用して○○大学の部分のみを正しく抽出
    「国立大学法人」等の法人格を除去
    """
    return f"""
    WITH normalized_universities AS (
      SELECT 
        -- 大学名の基本部分を抽出（○○大学の部分のみ）
        CASE 
          WHEN REGEXP_CONTAINS(main_affiliation_name_ja, r'東京工業大学') THEN '東京科学大学'
          WHEN REGEXP_CONTAINS(main_affiliation_name_ja, r'東京医科歯科大学') THEN '東京科学大学'
          ELSE REGEXP_EXTRACT(
            REGEXP_REPLACE(
              REGEXP_REPLACE(
                REGEXP_REPLACE(
                  REGEXP_REPLACE(
                    REGEXP_REPLACE(main_affiliation_name_ja, r'[\\s　]+', ''),
                    r'^国立大学法人', ''
                  ),
                  r'^公立大学法人', ''
                ),
                r'^学校法人', ''
              ),
              r'^独立行政法人', ''
            ),
            r'(.+?大学)'
          )
        END as university_name,
        name_ja,
        main_affiliation_name_ja as original_name
      FROM `{table_name}`
      WHERE main_affiliation_name_ja IS NOT NULL
        AND main_affiliation_name_ja LIKE '%大学%'
        AND REGEXP_CONTAINS(main_affiliation_name_ja, r'.+大学')
    ),
    
    university_stats AS (
      SELECT 
        university_name,
        COUNT(DISTINCT name_ja) as researcher_count,
        ARRAY_AGG(DISTINCT original_name LIMIT 10) as sample_original_names
      FROM normalized_universities
      WHERE university_name IS NOT NULL
        AND university_name != ''
        AND university_name != '大学'  -- "大学"のみを除外
      GROUP BY university_name
      HAVING COUNT(DISTINCT name_ja) >= 5
    )
    
    SELECT 
      university_name,
      researcher_count,
      sample_original_names
    FROM university_stats
    ORDER BY researcher_count DESC
    LIMIT 100
    """

# 古い複雑な関数名との互換性のため
get_normalized_university_stats_query_safe = get_normalized_university_stats_query
normalize_university_name_safe = normalize_university_name

# テスト関数
def test_normalization():
    """
    正規化のテスト
    """
    test_cases = [
        "京都大学",
        "京都大学大学院",
        "京都大学医学部附属病院",
        "京都大学iPS細胞研究所",
        "東京大学",
        "東京大学大学院医学系研究科",
        "東京大学医学部附属病院",
        "東京工業大学",
        "東京医科歯科大学",
        "大阪大学",
        "大阪大学大学院医学系研究科",
        "北海道大学病院",
        "九州大学農学研究院",
        "慶應義塾大学",
        "東京理科大学",
        "国立大学法人東京大学",
        "国立大学法人京都大学",
        "国立大学法人大阪大学大学院",
        "公立大学法人大阪市立大学",
        "学校法人慶應義塾大学",
        "東海国立大学機構名古屋大学"
    ]
    
    print("大学名正規化テスト（シンプル版・修正版）:")
    print("-" * 60)
    for name in test_cases:
        normalized = normalize_university_name(name)
        print(f"{name:<40} → {normalized}")
    
    print("\n" + "=" * 60)
    print("正規化ルール:")
    print("1. 法人格除去: 国立大学法人○○大学 → ○○大学")
    print("2. 基本抽出: ○○大学+{任意文字} → ○○大学")
    print("3. 統合処理: 東京工業大学・東京医科歯科大学 → 東京科学大学")

if __name__ == "__main__":
    test_normalization()
