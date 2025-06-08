#!/usr/bin/env python3
"""
大学API動作テストスクリプト
現在の大学リストの状況を確認
"""

import requests
import json

def test_university_api():
    """大学APIの動作テスト"""
    
    print("🔍 大学API動作テスト開始")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    try:
        # 1. サーバーのヘルスチェック
        print("1. サーバーヘルスチェック...")
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ サーバー稼働中")
        else:
            print(f"❌ サーバーエラー: {response.status_code}")
            return
        
        # 2. 大学APIのテスト
        print("\n2. 大学API動作確認...")
        response = requests.get(f"{base_url}/api/universities", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 大学API成功: ステータス = {data.get('status')}")
            
            universities = data.get('universities', [])
            print(f"📊 取得大学数: {len(universities)}校")
            
            if universities:
                print("\n🏫 大学リスト（上位10校）:")
                for i, uni in enumerate(universities[:10], 1):
                    name = uni.get('name', '不明')
                    count = uni.get('count', 0)
                    original_names = uni.get('original_names', [])
                    
                    # 統合状況の確認
                    if original_names and len(original_names) > 1:
                        consolidated = f" (統合: {len(original_names)}校)"
                        print(f"  {i:2d}. {name}: {count:,}名{consolidated}")
                        
                        # 統合された大学名を表示（最初の3つ）
                        for j, orig in enumerate(original_names[:3]):
                            print(f"      └─ {orig}")
                        if len(original_names) > 3:
                            print(f"      └─ ...他{len(original_names)-3}校")
                    else:
                        print(f"  {i:2d}. {name}: {count:,}名")
                
                # 医学系の統合状況をチェック
                print("\n🔬 医学系統合状況チェック:")
                medical_patterns = ['医学部', '医学研究科', '医学系研究科', '医学医療系', '医学研究院']
                
                found_medical = False
                for uni in universities:
                    original_names = uni.get('original_names', [])
                    for orig in original_names:
                        for pattern in medical_patterns:
                            if pattern in orig:
                                print(f"  • {orig} → {uni.get('name')}")
                                found_medical = True
                
                if not found_medical:
                    print("  ⚠️ 医学系の統合が見つかりませんでした")
                
                # 学部系の統合状況をチェック
                print("\n🎓 学部系統合状況チェック:")
                faculty_patterns = ['工学部', '理学部', '文学部', '法学部', '経済学部']
                
                found_faculty = False
                for uni in universities:
                    original_names = uni.get('original_names', [])
                    for orig in original_names:
                        for pattern in faculty_patterns:
                            if pattern in orig:
                                print(f"  • {orig} → {uni.get('name')}")
                                found_faculty = True
                
                if not found_faculty:
                    print("  ⚠️ 学部系の統合が見つかりませんでした")
            
        else:
            print(f"❌ 大学API失敗: {response.status_code}")
            try:
                error_data = response.json()
                print(f"エラー詳細: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"エラー内容: {response.text}")
    
    except requests.RequestException as e:
        print(f"❌ 接続エラー: {e}")
        print("💡 サーバーが起動していることを確認してください")
    
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")

if __name__ == "__main__":
    test_university_api()
