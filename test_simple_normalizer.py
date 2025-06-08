"""
シンプル版大学名正規化システムのテスト
"""

from university_normalizer_simple import normalize_university_name, get_normalized_university_stats_query

def test_simple_normalization():
    """
    シンプル版正規化のテスト
    """
    print("シンプル版大学名正規化テスト")
    print("=" * 60)
    print("ルール: ○○大学+{任意の文字} → ○○大学")
    print("-" * 60)
    
    test_cases = [
        # 基本パターン
        "京都大学",
        "京都大学大学院", 
        "京都大学医学部附属病院",
        "京都大学iPS細胞研究所",
        
        # 東京大学系
        "東京大学",
        "東京大学大学院医学系研究科",
        "東京大学医学部附属病院",
        "東京大学史料編纂所",
        "東京大学物性研究所",
        
        # 特殊統合（東京科学大学）
        "東京工業大学",
        "東京医科歯科大学",
        "東京工業大学大学院",
        "東京医科歯科大学病院",
        
        # その他の大学
        "大阪大学",
        "大阪大学大学院医学系研究科",
        "北海道大学病院",
        "九州大学農学研究院",
        "筑波大学附属病院",
        "名古屋大学工学研究科",
        
        # 複雑なケース
        "慶應義塾大学",
        "東京理科大学",
        "東大阪大学",
        "東大阪大学短期大学部"
    ]
    
    for i, name in enumerate(test_cases, 1):
        normalized = normalize_university_name(name)
        status = "統合" if name != normalized else "変更なし"
        print(f"{i:2d}. {name:<45} → {normalized:<20} ({status})")
    
    print("\n" + "=" * 60)
    print("SQLクエリテスト")
    print("-" * 60)
    
    # SQLクエリ生成テスト
    table_name = "sample_table"
    query = get_normalized_university_stats_query(table_name)
    
    print(f"クエリ長: {len(query)}文字")
    print(f"行数: {query.count(chr(10)) + 1}")
    print("\nクエリ概要:")
    lines = query.split('\n')
    for i, line in enumerate(lines[:10], 1):
        print(f"{i:2d}: {line.strip()}")
    if len(lines) > 10:
        print(f"... (残り{len(lines) - 10}行)")
    
    print("\n" + "=" * 60)
    print("特徴:")
    print("- シンプルなREGEXP_EXTRACTによる○○大学抽出")
    print("- 複雑な多重REGEXP_REPLACEなし")
    print("- 東京工業大学 + 東京医科歯科大学 → 東京科学大学の統合")
    print("- 保守しやすいクリーンなコード")

if __name__ == "__main__":
    test_simple_normalization()
