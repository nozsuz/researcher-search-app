"""
東海国立大学機構の正規化クイックテスト
"""

import re

def normalize_university_name_simple(university_name: str) -> str:
    """
    修正されたシンプル版正規化関数のテスト
    """
    if not university_name:
        return ""
    
    # 全角・半角スペース除去
    normalized = university_name.strip()
    normalized = re.sub(r'[\s　]+', '', normalized)
    
    # 特殊ケース：東海国立大学機構の処理（最優先）
    if '東海国立大学機構' in normalized:
        # 名古屋大学が含まれている場合
        if '名古屋大学' in normalized:
            return '名古屋大学'
        # 岐阜大学が含まれている場合
        elif '岐阜大学' in normalized:
            return '岐阜大学'
        else:
            # 機構名のみの場合は「東海国立大学機構」として扱う
            return '東海国立大学機構'
    
    # 法人格の除去
    normalized = re.sub(r'^国立大学法人', '', normalized)
    normalized = re.sub(r'^公立大学法人', '', normalized) 
    normalized = re.sub(r'^学校法人', '', normalized)
    normalized = re.sub(r'^独立行政法人', '', normalized)
    
    # 機構名の除去（東海国立大学機構以外）
    normalized = re.sub(r'機構', '', normalized)
    
    # 大学名の基本パターンを抽出
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
    
    return normalized

def test_cases():
    """
    テストケースの実行
    """
    cases = [
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
        "東海国立大学機構岐阜大学",
        "東海国立大学機構",
        "京都大学",
        "国立大学法人京都大学"
    ]
    
    print("東海国立大学機構 正規化テスト結果")
    print("=" * 60)
    print(f"{'入力':<40} | {'結果':<15}")
    print("-" * 60)
    
    for case in cases:
        result = normalize_university_name_simple(case)
        status = "✓" if is_expected_result(case, result) else "✗"
        print(f"{case:<40} | {result:<15} {status}")

def is_expected_result(input_name, result):
    """
    期待される結果かどうかを判定
    """
    if "東海国立大学機構" in input_name:
        if "名古屋大学" in input_name:
            return result == "名古屋大学"
        elif "岐阜大学" in input_name:
            return result == "岐阜大学"
        else:
            return result == "東海国立大学機構"
    elif "京都大学" in input_name:
        return result == "京都大学"
    elif input_name == "名古屋大学":
        return result == "名古屋大学"
    return True  # その他は正規化されていれば良い

if __name__ == "__main__":
    test_cases()
