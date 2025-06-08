"""
東海国立大学機構対応のSQLクエリ生成テスト
"""

def get_tokai_aware_normalization_query(table_name: str) -> str:
    """
    東海国立大学機構に対応したSQL正規化クエリ
    """
    return f"""
    WITH normalized_universities AS (
      SELECT 
        -- 大学名の基本部分を抽出（○○大学の部分のみ）
        CASE 
          -- 東海国立大学機構の特殊処理
          WHEN main_affiliation_name_ja LIKE '%東海国立大学機構%' AND main_affiliation_name_ja LIKE '%名古屋大学%' THEN '名古屋大学'
          WHEN main_affiliation_name_ja LIKE '%東海国立大学機構%' AND main_affiliation_name_ja LIKE '%岐阜大学%' THEN '岐阜大学'
          WHEN main_affiliation_name_ja LIKE '%東海国立大学機構%' THEN '東海国立大学機構'
          
          -- 統合処理
          WHEN REGEXP_CONTAINS(main_affiliation_name_ja, r'東京工業大学') THEN '東京科学大学'
          WHEN REGEXP_CONTAINS(main_affiliation_name_ja, r'東京医科歯科大学') THEN '東京科学大学'
          
          -- 通常の正規化処理
          ELSE REGEXP_EXTRACT(
            REGEXP_REPLACE(
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
              r'機構', ''
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

def test_sql_generation():
    """
    SQLクエリ生成のテスト
    """
    table_name = "your_project.your_dataset.researchers"
    query = get_tokai_aware_normalization_query(table_name)
    
    print("東海国立大学機構対応SQL正規化クエリ")
    print("=" * 60)
    print(query)
    
    # 重要な部分をハイライト
    print("\n" + "=" * 60)
    print("重要なポイント:")
    print("1. 東海国立大学機構の特殊処理が最優先で実行される")
    print("2. 名古屋大学/岐阜大学が含まれていれば適切に抽出")
    print("3. 機構名のみの場合は「東海国立大学機構」として保持")
    print("4. 他の正規化ルールはその後に適用")

if __name__ == "__main__":
    test_sql_generation()
