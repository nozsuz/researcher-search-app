"""
安全な大学名正規化クエリ生成器
段階的にテスト可能な正規化システム
"""

def generate_safe_normalization_query(table_name: str, test_mode: bool = False) -> str:
    """
    安全な正規化クエリを生成
    
    Args:
        table_name: テーブル名
        test_mode: テストモード（trueの場合、LIMIT追加）
        
    Returns:
        安全な正規化クエリ
    """
    
    limit_clause = "LIMIT 100" if test_mode else ""
    
    return f"""
    WITH step1_special_mapping AS (
        SELECT 
            name_ja,
            main_affiliation_name_ja as original_university,
            CASE 
                WHEN main_affiliation_name_ja LIKE '%東京医科歯科大学%' THEN '東京科学大学'
                WHEN main_affiliation_name_ja LIKE '%東京工業大学%' THEN '東京科学大学'
                ELSE main_affiliation_name_ja
            END as after_special_mapping
        FROM `{table_name}`
        WHERE main_affiliation_name_ja IS NOT NULL
          AND main_affiliation_name_ja != ''
          AND main_affiliation_name_ja LIKE '%大学%'
        {limit_clause}
    ),
    step2_remove_corporation AS (
        SELECT 
            name_ja,
            original_university,
            after_special_mapping,
            REGEXP_REPLACE(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        after_special_mapping,
                        r'^学校法人(.+大学).*$', r'\\\\1'
                    ),
                    r'^国立大学法人(.+大学).*$', r'\\\\1'
                ),
                r'^公立大学法人(.+大学).*$', r'\\\\1'
            ) as after_corporation_removal
        FROM step1_special_mapping
    ),
    step3_remove_graduate_school AS (
        SELECT 
            name_ja,
            original_university,
            after_special_mapping,
            after_corporation_removal,
            REGEXP_REPLACE(
                after_corporation_removal,
                r'^(.+大学)大学院.*$', r'\\\\1'
            ) as after_graduate_school_removal
        FROM step2_remove_corporation
    ),
    step4_remove_affiliated_organizations AS (
        SELECT 
            name_ja,
            original_university,
            after_special_mapping,
            after_corporation_removal,
            after_graduate_school_removal,
            TRIM(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(
                            REGEXP_REPLACE(
                                REGEXP_REPLACE(
                                    REGEXP_REPLACE(
                                        REGEXP_REPLACE(
                                            REGEXP_REPLACE(
                                                after_graduate_school_removal,
                                                r'^(.+大学).+附属病院.*$', r'\\\\1'
                                            ),
                                            r'^(.+大学).+病院.*$', r'\\\\1'
                                        ),
                                        r'^(.+大学).+研究所.*$', r'\\\\1'
                                    ),
                                    r'^(.+大学).+センター.*$', r'\\\\1'
                                ),
                                r'^(.+大学).+機構.*$', r'\\\\1'
                            ),
                            r'^(.+大学).+学部.*$', r'\\\\1'
                        ),
                        r'^(.+大学).+研究科.*$', r'\\\\1'
                    ),
                    r'^(.+大学).+研究院.*$', r'\\\\1'
                )
            ) as normalized_university
        FROM step3_remove_graduate_school
    )
    SELECT 
        normalized_university as university_name,
        COUNT(DISTINCT name_ja) as researcher_count,
        ARRAY_AGG(DISTINCT original_university ORDER BY original_university LIMIT 10) as original_names,
        -- デバッグ情報（テストモード時のみ）
        {'''
        ARRAY_AGG(DISTINCT after_special_mapping ORDER BY after_special_mapping LIMIT 3) as step1_examples,
        ARRAY_AGG(DISTINCT after_corporation_removal ORDER BY after_corporation_removal LIMIT 3) as step2_examples,
        ARRAY_AGG(DISTINCT after_graduate_school_removal ORDER BY after_graduate_school_removal LIMIT 3) as step3_examples
        ''' if test_mode else ''}
    FROM step4_remove_affiliated_organizations
    WHERE normalized_university IS NOT NULL 
      AND normalized_university != ''
      AND normalized_university LIKE '%大学%'
      AND LENGTH(normalized_university) >= 3
      AND LENGTH(normalized_university) <= 50  -- 異常に長い名前を除外
    GROUP BY normalized_university
    HAVING COUNT(DISTINCT name_ja) >= 5  -- 5名以上の研究者がいる大学のみ
    ORDER BY researcher_count DESC
    """

def generate_investigation_query(table_name: str) -> str:
    """
    調査用クエリを生成（問題のあるデータを特定）
    
    Args:
        table_name: テーブル名
        
    Returns:
        調査用クエリ
    """
    
    return f"""
    WITH suspicious_patterns AS (
        SELECT 
            main_affiliation_name_ja,
            COUNT(DISTINCT name_ja) as researcher_count,
            CASE 
                WHEN main_affiliation_name_ja LIKE '%学学%' THEN '重複文字パターン'
                WHEN main_affiliation_name_ja LIKE '%大大%' THEN '重複文字パターン'
                WHEN LENGTH(main_affiliation_name_ja) > 50 THEN '異常に長い名前'
                WHEN main_affiliation_name_ja NOT LIKE '%大学%' THEN '大学以外の機関'
                WHEN main_affiliation_name_ja LIKE '%　%' THEN '全角空白含む'
                WHEN REGEXP_CONTAINS(main_affiliation_name_ja, r'[0-9]+') THEN '数字含む'
                ELSE 'その他'
            END as pattern_type
        FROM `{table_name}`
        WHERE main_affiliation_name_ja IS NOT NULL
          AND main_affiliation_name_ja != ''
        GROUP BY main_affiliation_name_ja
        HAVING researcher_count >= 1
    )
    SELECT 
        pattern_type,
        COUNT(*) as pattern_count,
        SUM(researcher_count) as total_researchers,
        ARRAY_AGG(main_affiliation_name_ja ORDER BY researcher_count DESC LIMIT 5) as examples
    FROM suspicious_patterns
    WHERE pattern_type != 'その他'
    GROUP BY pattern_type
    ORDER BY total_researchers DESC
    """

# テスト用関数
def create_test_queries():
    """
    テスト用クエリを生成して表示
    """
    table_name = "apt-rope-217206.researcher_data.rd_250524"
    
    print("🧪 安全な正規化テストクエリ:")
    print("=" * 60)
    test_query = generate_safe_normalization_query(table_name, test_mode=True)
    print(test_query)
    
    print("\n🔍 データ調査クエリ:")
    print("=" * 60)
    investigation_query = generate_investigation_query(table_name)
    print(investigation_query)

if __name__ == "__main__":
    create_test_queries()
