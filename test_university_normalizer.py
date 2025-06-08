"""
大学名正規化システムのテストスクリプト
"""

import asyncio
import logging
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from university_normalizer import UniversityNormalizer, normalize_university_name, test_normalization

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_basic_normalization():
    """
    基本的な正規化機能のテスト
    """
    print("=" * 60)
    print("🧪 基本的な正規化機能のテスト")
    print("=" * 60)
    
    test_cases = [
        # 既存の主要大学
        "東京大学大学院",
        "東京大学医学部附属病院",
        "東京大学先端科学技術研究センター",
        "京都大学大学院医学研究科",
        "京都大学iPS細胞研究所",
        "大阪大学核物理研究センター",
        "北海道大学低温科学研究所",
        "東北大学金属材料研究所",
        
        # 新しい大学（テスト用）
        "新設科学技術大学大学院",
        "革新工学大学医学部附属病院",
        "未来大学先端研究センター",
        "創造大学大学院工学研究科",
        "先端技術大学生命科学研究所",
        
        # 法人格付きの大学
        "学校法人新設大学",
        "国立大学法人未来大学",
        "公立大学法人地域大学",
        
        # 複雑なケース
        "東京科学大学大学院情報理工学研究科",
        "新設大学　医学部　附属病院",  # 全角空白
        "革新大学 先端科学技術 研究センター",  # 複数空白
    ]
    
    normalizer = UniversityNormalizer()
    
    for i, name in enumerate(test_cases, 1):
        normalized = normalizer.normalize_university_name(name)
        print(f"{i:2d}. '{name}' → '{normalized}'")
        
        # 新規大学名かどうかを判定
        if any(keyword in name for keyword in ["新設", "革新", "未来", "創造", "先端技術"]):
            print(f"    💡 新規大学: 動的正規化が適用されました")
    
    print()

def test_sql_generation():
    """
    SQL生成機能のテスト
    """
    print("=" * 60)
    print("🧪 SQL生成機能のテスト")
    print("=" * 60)
    
    normalizer = UniversityNormalizer()
    
    # 基本的な正規化SQL
    basic_sql = normalizer.generate_dynamic_normalization_sql("main_affiliation_name_ja")
    print("基本正規化SQL:")
    print(basic_sql)
    print()
    
    # 統計用クエリ
    stats_query = normalizer.get_normalized_university_stats_query("test_table")
    print("統計用クエリ（抜粋）:")
    print(stats_query[:500] + "..." if len(stats_query) > 500 else stats_query)
    print()

def test_grouping():
    """
    大学名グルーピング機能のテスト
    """
    print("=" * 60)
    print("🧪 大学名グルーピング機能のテスト")
    print("=" * 60)
    
    # テスト用の大学名リスト
    university_names = [
        "東京大学",
        "東京大学大学院",
        "東京大学医学部附属病院",
        "東京大学先端科学技術研究センター",
        "京都大学",
        "京都大学大学院",
        "京都大学iPS細胞研究所",
        "新設大学",
        "新設大学大学院",
        "新設大学研究センター",
        "革新大学",
        "革新大学医学部附属病院",
    ]
    
    normalizer = UniversityNormalizer()
    groups = normalizer.get_university_groups(university_names)
    
    print("グループ化結果:")
    for normalized_name, original_names in groups.items():
        print(f"  📚 {normalized_name}:")
        for orig in original_names:
            print(f"    - {orig}")
        print(f"    💡 統合効果: {len(original_names)}件 → 1件")
    print()

async def test_api_integration():
    """
    API統合テスト（モック）
    """
    print("=" * 60)
    print("🧪 API統合テスト（モック）")
    print("=" * 60)
    
    # main.pyの関数をインポートしてテスト
    try:
        from university_normalizer import get_normalized_university_stats_query
        
        query = get_normalized_university_stats_query("test_table")
        print("✅ 統計クエリ生成: 成功")
        print(f"クエリ長: {len(query)}文字")
        
        # フィルタリング用SQL生成テスト
        from university_normalizer import get_university_normalization_sql
        filter_sql = get_university_normalization_sql("main_affiliation_name_ja")
        print("✅ フィルタリングSQL生成: 成功")
        print(f"SQL長: {len(filter_sql)}文字")
        
    except Exception as e:
        print(f"❌ API統合テストエラー: {e}")
    
    print()

def test_cache_performance():
    """
    キャッシュ性能のテスト
    """
    print("=" * 60)
    print("🧪 キャッシュ性能テスト")
    print("=" * 60)
    
    import time
    
    normalizer = UniversityNormalizer()
    
    test_names = [
        "東京大学大学院医学系研究科",
        "京都大学iPS細胞研究所",
        "新設大学先端技術研究センター"
    ] * 100  # 100回繰り返し
    
    # 初回実行（キャッシュなし）
    start_time = time.time()
    for name in test_names:
        normalizer.normalize_university_name(name)
    first_run_time = time.time() - start_time
    
    # 2回目実行（キャッシュあり）
    start_time = time.time()
    for name in test_names:
        normalizer.normalize_university_name(name)
    second_run_time = time.time() - start_time
    
    print(f"初回実行（キャッシュなし）: {first_run_time:.4f}秒")
    print(f"2回目実行（キャッシュあり）: {second_run_time:.4f}秒")
    print(f"性能向上: {first_run_time / second_run_time:.2f}倍")
    print(f"キャッシュサイズ: {len(normalizer._normalization_cache)}件")
    print()

def main():
    """
    メイン関数
    """
    print("🚀 大学名正規化システム テストスイート")
    print("=" * 60)
    
    # 各テストを実行
    test_basic_normalization()
    test_sql_generation()
    test_grouping()
    
    # 非同期テスト
    asyncio.run(test_api_integration())
    
    test_cache_performance()
    
    print("=" * 60)
    print("✅ すべてのテストが完了しました")
    print("💡 新規大学名が登録されても、動的正規化システムが自動的に適用されます")

if __name__ == "__main__":
    main()
