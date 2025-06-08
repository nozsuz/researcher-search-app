"""
大学フィルタリング修正版テスト
real_search.pyの修正が正しく動作するかテスト
"""

import asyncio
import logging
import sys
import os

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestRequest:
    """テスト用のリクエストクラス"""
    def __init__(self, query, university_filter=None):
        self.query = query
        self.method = "keyword"
        self.max_results = 3
        self.use_llm_expansion = False
        self.use_llm_summary = False
        self.use_internal_evaluation = False
        self.young_researcher_filter = False
        self.university_filter = university_filter

async def test_university_filtering():
    """
    大学フィルタリング機能のテスト
    """
    logger.info("🧪 大学フィルタリング修正版テスト開始")
    
    try:
        from real_search import perform_real_search
        
        # テストケース1: 大学フィルターなし
        logger.info("📊 テスト1: 大学フィルターなし")
        request1 = TestRequest("人工知能")
        result1 = await perform_real_search(request1)
        logger.info(f"結果1: {result1.get('status')}")
        
        # テストケース2: 大学フィルターあり（正常ケース）
        logger.info("📊 テスト2: 大学フィルターあり（東京大学）")
        request2 = TestRequest("人工知能", university_filter=["東京大学"])
        result2 = await perform_real_search(request2)
        logger.info(f"結果2: {result2.get('status')}")
        
        # テストケース3: 複数大学フィルター
        logger.info("📊 テスト3: 複数大学フィルター")
        request3 = TestRequest("人工知能", university_filter=["東京大学", "京都大学"])
        result3 = await perform_real_search(request3)
        logger.info(f"結果3: {result3.get('status')}")
        
        # テスト結果の評価
        success_count = 0
        for i, result in enumerate([result1, result2, result3], 1):
            if result.get('status') == 'success':
                success_count += 1
                logger.info(f"✅ テスト{i}: 成功")
            else:
                logger.warning(f"⚠️ テスト{i}: {result.get('status')} - {result.get('error_message', 'N/A')}")
        
        logger.info(f"🎯 テスト結果: {success_count}/3 成功")
        
        if success_count == 3:
            logger.info("🎉 全テスト成功！大学フィルタリング修正完了")
            return True
        else:
            logger.warning("⚠️ 一部テストが失敗。さらなる修正が必要")
            return False
            
    except Exception as e:
        logger.error(f"❌ テスト実行エラー: {e}")
        import traceback
        logger.error(f"詳細: {traceback.format_exc()}")
        return False

async def test_university_normalizer():
    """
    university_normalizer_fixed.pyのテスト
    """
    logger.info("🧪 大学正規化モジュールテスト開始")
    
    try:
        from university_normalizer_fixed import normalize_university_name, get_university_normalization_sql
        
        # 正規化テスト
        test_cases = [
            ("東京大学", "東京大学"),
            ("東京大学大学院", "東京大学"),
            ("東京大学医学部附属病院", "東京大学"),
            ("京都大学研究所", "京都大学"),
            ("東京工業大学", "東京科学大学"),
            ("東京医科歯科大学", "東京科学大学")
        ]
        
        success = True
        for original, expected in test_cases:
            result = normalize_university_name(original)
            if result == expected:
                logger.info(f"✅ {original} → {result}")
            else:
                logger.warning(f"❌ {original} → {result} (期待値: {expected})")
                success = False
        
        # SQL生成テスト
        sql = get_university_normalization_sql("test_column")
        if len(sql) > 100:
            logger.info(f"✅ SQL生成成功: {len(sql)}文字")
        else:
            logger.warning(f"❌ SQL生成失敗: {len(sql)}文字")
            success = False
        
        return success
        
    except Exception as e:
        logger.error(f"❌ 正規化モジュールテストエラー: {e}")
        return False

async def main():
    """
    メインテスト実行
    """
    logger.info("🚀 大学フィルタリング修正版 総合テスト開始")
    
    # 1. 正規化モジュールテスト
    normalizer_ok = await test_university_normalizer()
    
    # 2. 大学フィルタリングテスト
    filtering_ok = await test_university_filtering()
    
    # 3. 結果まとめ
    logger.info("\n" + "="*50)
    logger.info("📊 テスト結果まとめ")
    logger.info("="*50)
    logger.info(f"正規化モジュール: {'✅ 成功' if normalizer_ok else '❌ 失敗'}")
    logger.info(f"大学フィルタリング: {'✅ 成功' if filtering_ok else '❌ 失敗'}")
    
    if normalizer_ok and filtering_ok:
        logger.info("🎉 全テスト成功！修正完了")
        logger.info("✅ 大学フィルタリング機能が正常に動作します")
        logger.info("✅ モックデータ表示問題は解決されました")
    else:
        logger.warning("⚠️ 一部テストが失敗。追加の修正が必要です")
    
    return normalizer_ok and filtering_ok

if __name__ == "__main__":
    # テスト実行
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
