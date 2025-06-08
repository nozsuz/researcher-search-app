"""
大学名データの調査スクリプト
実際のデータベースにある大学名を分析して正規化の効果を確認
"""

import asyncio
import logging
from typing import Dict, List, Tuple
from collections import Counter

logger = logging.getLogger(__name__)

async def investigate_university_data():
    """
    実際の大学名データを調査
    """
    try:
        from gcp_auth import get_bigquery_client
        
        bq_client = get_bigquery_client()
        if not bq_client:
            print("❌ BigQueryクライアントが利用できません")
            return
        
        print("🔍 大学名データの調査を開始...")
        
        # 生の大学名データを取得
        raw_query = """
        SELECT 
            main_affiliation_name_ja,
            COUNT(DISTINCT name_ja) as researcher_count
        FROM `apt-rope-217206.researcher_data.rd_250524`
        WHERE main_affiliation_name_ja IS NOT NULL
          AND main_affiliation_name_ja != ''
        GROUP BY main_affiliation_name_ja
        ORDER BY researcher_count DESC
        LIMIT 50
        """
        
        print("📊 生の大学名データ（上位50件）:")
        print("=" * 60)
        
        query_job = bq_client.query(raw_query)
        raw_data = []
        
        for i, row in enumerate(query_job, 1):
            university_name = row.main_affiliation_name_ja
            count = row.researcher_count
            raw_data.append((university_name, count))
            print(f"{i:2d}. {university_name} ({count:,}名)")
        
        # 奇妙な大学名パターンを調査
        print("\n🔍 奇妙なパターンの調査:")
        print("=" * 60)
        
        suspicious_patterns = []
        for name, count in raw_data:
            # 奇妙なパターンを検出
            if any(pattern in name for pattern in ['学学', '大大', '都大学学']):
                suspicious_patterns.append((name, count))
                print(f"❗ {name} ({count}名) - 疑わしいパターン")
        
        if not suspicious_patterns:
            print("✅ 奇妙なパターンは検出されませんでした")
        
        # 正規化テスト
        print("\n🧪 正規化効果のテスト:")
        print("=" * 60)
        
        from university_normalizer import normalize_university_name
        
        normalization_effects = []
        for name, count in raw_data[:20]:  # 上位20件で正規化をテスト
            normalized = normalize_university_name(name)
            if name != normalized:
                normalization_effects.append((name, normalized, count))
                reduction = len(name) - len(normalized)
                print(f"'{name}' → '{normalized}' ({reduction}文字短縮, {count}名)")
        
        if not normalization_effects:
            print("📝 上位20件では正規化が適用される大学はありませんでした")
        
        # 特定の大学のバリエーションを調査
        print("\n🏫 主要大学のバリエーション調査:")
        print("=" * 60)
        
        major_universities = ['東京大学', '京都大学', '大阪大学', '東北大学', '北海道大学']
        
        for base_name in major_universities:
            variations_query = f"""
            SELECT 
                main_affiliation_name_ja,
                COUNT(DISTINCT name_ja) as researcher_count
            FROM `apt-rope-217206.researcher_data.rd_250524`
            WHERE main_affiliation_name_ja LIKE '%{base_name}%'
              AND main_affiliation_name_ja IS NOT NULL
            GROUP BY main_affiliation_name_ja
            ORDER BY researcher_count DESC
            """
            
            query_job = bq_client.query(variations_query)
            variations = list(query_job)
            
            if len(variations) > 1:
                print(f"\n📋 {base_name}関連の表記バリエーション:")
                total_researchers = 0
                for var in variations:
                    print(f"  - {var.main_affiliation_name_ja} ({var.researcher_count}名)")
                    total_researchers += var.researcher_count
                print(f"  💡 統合効果: {len(variations)}種類 → 1種類 (計{total_researchers}名)")
        
        print("\n✅ 大学名データ調査完了")
        
    except Exception as e:
        print(f"❌ 調査エラー: {e}")

async def test_normalization_with_real_data():
    """
    実際のデータで正規化をテスト
    """
    try:
        from gcp_auth import get_bigquery_client
        from university_normalizer import get_normalized_university_stats_query
        
        bq_client = get_bigquery_client()
        if not bq_client:
            print("❌ BigQueryクライアントが利用できません")
            return
        
        print("🧪 実際のデータで正規化テストを実行...")
        
        # 正規化済みクエリを実行
        query = get_normalized_university_stats_query("apt-rope-217206.researcher_data.rd_250524")
        
        print("📊 正規化後の結果（上位20件）:")
        print("=" * 60)
        
        query_job = bq_client.query(query)
        
        for i, row in enumerate(query_job, 1):
            if i > 20:  # 上位20件のみ
                break
            
            university_name = row.university_name
            count = row.researcher_count
            original_names = row.original_names if hasattr(row, 'original_names') else []
            
            print(f"{i:2d}. {university_name} ({count:,}名)")
            
            # 正規化効果を表示
            if len(original_names) > 1:
                print(f"    💡 統合効果: {len(original_names)}種類の表記を統合")
                # 主要な元表記を表示
                for orig in original_names[:3]:  # 最初の3つのみ
                    print(f"      - {orig}")
                if len(original_names) > 3:
                    print(f"      - ...など{len(original_names)}種類")
        
        print("\n✅ 正規化テスト完了")
        
    except Exception as e:
        print(f"❌ 正規化テストエラー: {e}")

async def main():
    """
    メイン関数
    """
    print("🚀 大学名データ調査＆正規化テスト")
    print("=" * 60)
    
    # 生データの調査
    await investigate_university_data()
    
    print("\n" + "=" * 60)
    
    # 正規化テスト
    await test_normalization_with_real_data()

if __name__ == "__main__":
    asyncio.run(main())
