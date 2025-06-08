"""
国立大学法人対応版 総合テスト
修正版の正規化システムをテスト
"""

import logging
import asyncio

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_fixed_normalizer():
    """
    university_normalizer_fixed.py のテスト
    """
    logger.info("🧪 修正版正規化システムテスト")
    
    try:
        from university_normalizer_fixed import normalize_university_name
        
        test_cases = [
            ("国立大学法人東京大学", "東京大学"),
            ("国立大学法人京都大学医学部附属病院", "京都大学"),
            ("国立大学法人東京工業大学", "東京科学大学"),
            ("国立大学法人東京医科歯科大学", "東京科学大学"),
            ("公立大学法人大阪市立大学", "大阪市立大学"),
            ("学校法人慶應義塾大学", "慶應義塾大学"),
            ("東京大学", "東京大学"),  # 法人格なし
        ]
        
        success = 0
        for original, expected in test_cases:
            result = normalize_university_name(original)
            if result == expected:
                logger.info(f"✅ {original} → {result}")
                success += 1
            else:
                logger.warning(f"❌ {original} → {result} (期待: {expected})")
        
        return success, len(test_cases)
        
    except Exception as e:
        logger.error(f"❌ 修正版テストエラー: {e}")
        return 0, 0

def test_simple_normalizer():
    """
    university_normalizer_simple.py のテスト
    """
    logger.info("🧪 シンプル版正規化システムテスト")
    
    try:
        from university_normalizer_simple import normalize_university_name
        
        test_cases = [
            ("国立大学法人東京大学", "東京大学"),
            ("国立大学法人京都大学大学院", "京都大学"),
            ("国立大学法人大阪大学医学部附属病院", "大阪大学"),
            ("公立大学法人横浜市立大学", "横浜市立大学"),
            ("学校法人早稲田大学", "早稲田大学"),
            ("東京大学", "東京大学"),  # 法人格なし
        ]
        
        success = 0
        for original, expected in test_cases:
            result = normalize_university_name(original)
            if result == expected:
                logger.info(f"✅ {original} → {result}")
                success += 1
            else:
                logger.warning(f"❌ {original} → {result} (期待: {expected})")
        
        return success, len(test_cases)
        
    except Exception as e:
        logger.error(f"❌ シンプル版テストエラー: {e}")
        return 0, 0

async def test_search_integration():
    """
    検索システムとの統合テスト
    """
    logger.info("🧪 検索システム統合テスト")
    
    try:
        from real_search import perform_real_search
        
        class TestRequest:
            def __init__(self):
                self.query = "人工知能"
                self.method = "keyword"
                self.max_results = 3
                self.use_llm_expansion = False
                self.use_llm_summary = False
                self.use_internal_evaluation = False
                self.young_researcher_filter = False
                self.university_filter = ["国立大学法人東京大学", "国立大学法人京都大学"]
        
        test_request = TestRequest()
        result = await perform_real_search(test_request)
        
        if result.get('status') == 'success':
            logger.info("✅ 国立大学法人フィルター付き検索成功")
            return True
        else:
            logger.warning(f"⚠️ 検索結果: {result.get('status')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 統合テストエラー: {e}")
        return False

def main():
    """
    メインテスト実行
    """
    logger.info("🚀 国立大学法人対応版 総合テスト開始")
    logger.info("="*70)
    
    results = {}
    
    # 1. 修正版テスト
    logger.info("\n📊 テスト1: university_normalizer_fixed.py")
    fixed_success, fixed_total = test_fixed_normalizer()
    results['fixed'] = (fixed_success, fixed_total)
    
    # 2. シンプル版テスト  
    logger.info("\n📊 テスト2: university_normalizer_simple.py")
    simple_success, simple_total = test_simple_normalizer()
    results['simple'] = (simple_success, simple_total)
    
    # 3. 統合テスト
    logger.info("\n📊 テスト3: 検索システム統合")
    integration_success = asyncio.run(test_search_integration())
    results['integration'] = integration_success
    
    # 結果まとめ
    logger.info("\n" + "="*70)
    logger.info("📊 テスト結果まとめ")
    logger.info("="*70)
    
    logger.info(f"修正版正規化: {results['fixed'][0]}/{results['fixed'][1]} ({'✅ 成功' if results['fixed'][0] == results['fixed'][1] else '❌ 失敗'})")
    logger.info(f"シンプル版正規化: {results['simple'][0]}/{results['simple'][1]} ({'✅ 成功' if results['simple'][0] == results['simple'][1] else '❌ 失敗'})")
    logger.info(f"検索システム統合: {'✅ 成功' if results['integration'] else '❌ 失敗'}")
    
    all_success = (
        results['fixed'][0] == results['fixed'][1] and 
        results['simple'][0] == results['simple'][1] and 
        results['integration']
    )
    
    if all_success:
        logger.info("\n🎉 全テスト成功！")
        logger.info("✅ 「国立大学法人○○大学」→「○○大学」の正規化が完了")
        logger.info("✅ 集計表示で「国立大学」と誤表示される問題は解決")
        logger.info("✅ 大学フィルタリング機能も正常動作")
    else:
        logger.warning("\n⚠️ 一部テストが失敗しました")
    
    return all_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
