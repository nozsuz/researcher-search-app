"""
東海国立大学機構の正規化テスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from university_normalizer_simple import normalize_university_name
from university_normalizer_fixed import normalize_university_name as normalize_fixed

def test_tokai_normalization():
    """
    東海国立大学機構の正規化テスト
    """
    test_cases = [
        # 問題となっていたケース
        "国立大学法人東海国立大学機構名古屋大学",
        "国立大学法人東海国立大学機構",
        "国立大学法人　東海国立大学機構　名古屋大学",
        "国立大学法人 東海国立大学機構 名古屋大学",
        "国立大学法人東海国立大学機構 名古屋大学",
        "名古屋大学",
        "国立大学法人東海国立大学機構名古屋大学大学院理学研究科",
        "国立大学法人東海国立機構 名古屋大学大学院",
        "東海国立大学機構名古屋大学",
        "東海国立大学機構　名古屋大学",
        "東海国立大学機構 名古屋大学",
        
        # 岐阜大学のケース
        "東海国立大学機構岐阜大学",
        "国立大学法人東海国立大学機構岐阜大学",
        
        # 機構名のみのケース
        "東海国立大学機構",
        "国立大学法人東海国立大学機構",
        
        # 通常の大学（比較用）
        "京都大学",
        "国立大学法人京都大学",
        "東京大学大学院医学系研究科",
    ]
    
    print("=" * 80)
    print("東海国立大学機構 正規化テスト")
    print("=" * 80)
    print(f"{'元の表記':<50} | {'シンプル版':<20} | {'詳細版':<20}")
    print("-" * 80)
    
    for case in test_cases:
        simple_result = normalize_university_name(case)
        fixed_result = normalize_fixed(case)
        
        # 結果の色分け（期待値との比較）
        expected = get_expected_result(case)
        simple_status = "✓" if simple_result == expected else "✗"
        fixed_status = "✓" if fixed_result == expected else "✗"
        
        print(f"{case:<50} | {simple_result:<20} | {fixed_result:<20}")
        if simple_result != expected or fixed_result != expected:
            print(f"{'期待値: ' + expected:<50} | {simple_status:<20} | {fixed_status:<20}")
            print("-" * 80)

def get_expected_result(input_name):
    """
    期待される正規化結果を返す
    """
    if "東海国立大学機構" in input_name:
        if "名古屋大学" in input_name:
            return "名古屋大学"
        elif "岐阜大学" in input_name:
            return "岐阜大学"
        else:
            return "東海国立大学機構"
    elif "京都大学" in input_name:
        return "京都大学"
    elif "東京大学" in input_name:
        return "東京大学"
    elif input_name == "名古屋大学":
        return "名古屋大学"
    else:
        # 基本的な正規化ルールに従う
        import re
        normalized = input_name
        normalized = re.sub(r'[\s　]+', '', normalized)
        normalized = re.sub(r'^国立大学法人', '', normalized)
        normalized = re.sub(r'^公立大学法人', '', normalized)
        normalized = re.sub(r'^学校法人', '', normalized)
        
        match = re.search(r'(.+?大学)', normalized)
        if match:
            return match.group(1)
        return normalized

if __name__ == "__main__":
    test_tokai_normalization()
