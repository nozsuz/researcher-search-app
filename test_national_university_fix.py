"""
国立大学法人対応版正規化テスト
「国立大学法人○○大学」→「○○大学」の正規化をテスト
"""

import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_national_university_normalization():
    """
    国立大学法人の正規化テスト
    """
    logger.info("🧪 国立大学法人対応版正規化テスト開始")
    
    try:
        from university_normalizer_fixed import normalize_university_name, get_university_normalization_sql
        
        # テストケース
        test_cases = [
            # 問題となっているケース
            ("国立大学法人東京大学", "東京大学"),
            ("国立大学法人京都大学", "京都大学"),
            ("国立大学法人大阪大学", "大阪大学"),
            ("国立大学法人筑波大学", "筑波大学"),
            
            # 複合ケース
            ("国立大学法人東京大学大学院", "東京大学"),
            ("国立大学法人京都大学医学部附属病院", "京都大学"),
            ("国立大学法人東北大学医学研究科", "東北大学"),
            
            # 統合ケース
            ("国立大学法人東京工業大学", "東京科学大学"),
            ("国立大学法人東京医科歯科大学", "東京科学大学"),
            
            # その他の法人格
            ("公立大学法人大阪市立大学", "大阪市立大学"),
            ("学校法人慶應義塾大学", "慶應義塾大学"),
            ("独立行政法人国立高等専門学校機構", "国立高等専門学校機構"),
            
            # 法人格なしのケース（従来通り）
            ("東京大学", "東京大学"),
            ("東京大学大学院", "東京大学"),
            ("京都大学医学部附属病院", "京都大学"),
        ]
        
        logger.info("📊 正規化テスト実行:")
        success_count = 0
        total_count = len(test_cases)
        
        for original, expected in test_cases:
            result = normalize_university_name(original)
            if result == expected:
                logger.info(f"✅ {original} → {result}")
                success_count += 1
            else:
                logger.warning(f"❌ {original} → {result} (期待値: {expected})")
        
        # SQLクエリ生成テスト
        logger.info("\n📄 SQLクエリ生成テスト:")
        sql = get_university_normalization_sql("main_affiliation_name_ja")
        
        if "^国立大学法人" in sql:
            logger.info("✅ 国立大学法人の除去パターンが含まれています")
            sql_ok = True
        else:
            logger.warning("❌ 国立大学法人の除去パターンが見つかりません")
            sql_ok = False
        
        logger.info(f"📊 SQLクエリ長: {len(sql)}文字")
        logger.info(f"📊 REGEXP_REPLACE数: {sql.count('REGEXP_REPLACE')}")
        
        # 結果まとめ
        logger.info(f"\n📈 テスト結果:")
        logger.info(f"正規化テスト: {success_count}/{total_count} 成功")
        logger.info(f"SQLテスト: {'✅ 成功' if sql_ok else '❌ 失敗'}")
        
        overall_success = (success_count == total_count) and sql_ok
        
        if overall_success:
            logger.info("🎉 全テスト成功！国立大学法人対応完了")
        else:
            logger.warning("⚠️ 一部テストが失敗しました")
        
        return overall_success, success_count, total_count
        
    except Exception as e:
        logger.error(f"❌ テスト実行エラー: {e}")
        return False, 0, 0

def test_sql_patterns():
    """
    SQLパターンの詳細テスト
    """
    logger.info("🔍 SQLパターン詳細テスト")
    
    try:
        from university_normalizer_fixed import get_university_normalization_sql
        
        sql = get_university_normalization_sql("test_column")
        
        # 確認すべきパターン
        required_patterns = [
            "^国立大学法人",
            "^公立大学法人", 
            "^学校法人",
            "^独立行政法人",
            "附属病院$",
            "研究科$",
            "学部$",
            "研究所$"
        ]
        
        logger.info("📋 必要パターンの確認:")
        all_patterns_found = True
        
        for pattern in required_patterns:
            if pattern in sql:
                logger.info(f"✅ {pattern}")
            else:
                logger.warning(f"❌ {pattern}")
                all_patterns_found = False
        
        return all_patterns_found
        
    except Exception as e:
        logger.error(f"❌ SQLパターンテストエラー: {e}")
        return False

def main():
    """
    メインテスト実行
    """
    logger.info("🚀 国立大学法人対応版 総合テスト開始")
    logger.info("="*60)
    
    # 1. 正規化テスト
    norm_success, success_count, total_count = test_national_university_normalization()
    
    logger.info("\n" + "-"*40)
    
    # 2. SQLパターンテスト
    sql_success = test_sql_patterns()
    
    # 3. 結果まとめ
    logger.info("\n" + "="*60)
    logger.info("📊 最終テスト結果")
    logger.info("="*60)
    logger.info(f"正規化機能: {success_count}/{total_count} ({'✅ 成功' if norm_success else '❌ 失敗'})")
    logger.info(f"SQLパターン: {'✅ 成功' if sql_success else '❌ 失敗'}")
    
    overall_success = norm_success and sql_success
    
    if overall_success:
        logger.info("🎉 全テスト成功！")
        logger.info("✅ 「国立大学法人○○大学」→「○○大学」の正規化が正常に動作します")
        logger.info("✅ 集計表示で「国立大学」と誤表示される問題は解決されます")
    else:
        logger.warning("⚠️ 一部テストが失敗。追加の修正が必要です")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
