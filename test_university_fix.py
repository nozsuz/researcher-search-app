#!/usr/bin/env python3
"""
大学API修正テストスクリプト
強化されたエラーハンドリングとフォールバック機能のテスト
"""

import requests
import json
import time

def test_university_api_endpoints():
    """
    大学API関連エンドポイントのテスト
    """
    base_url = "http://localhost:8000"
    
    print("🚀 大学API修正テスト開始")
    print("=" * 60)
    
    # テストするエンドポイント
    endpoints = [
        "/test/university-api",           # 詳細テスト
        "/debug/university-normalization", # デバッグ情報
        "/api/universities/simple",       # シンプル版
        "/api/universities/emergency",     # 緊急時用
        "/api/universities"               # メイン
    ]
    
    results = {}
    
    for endpoint in endpoints:
        print(f"\n📍 テスト中: {endpoint}")
        print("-" * 40)
        
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}{endpoint}", timeout=30)
            response_time = time.time() - start_time
            
            print(f"ステータスコード: {response.status_code}")
            print(f"レスポンス時間: {response_time:.2f}秒")
            
            if response.status_code == 200:
                data = response.json()
                
                # レスポンス内容の分析
                if endpoint == "/test/university-api":
                    print("🧪 詳細テスト結果:")
                    tests = data.get("tests", {})
                    for test_name, test_result in tests.items():
                        status = test_result.get("status", "不明")
                        print(f"  - {test_name}: {status}")
                        if "error" in test_result:
                            print(f"    エラー: {test_result['error']}")
                
                elif endpoint == "/debug/university-normalization":
                    print("🔍 デバッグ情報:")
                    if "normalization_tests" in data:
                        changed_count = sum(1 for t in data["normalization_tests"] if t.get("changed"))
                        print(f"  - 正規化テスト: {len(data['normalization_tests'])}件中{changed_count}件が変更")
                    if "sql_analysis" in data:
                        sql_info = data["sql_analysis"]
                        print(f"  - SQLクエリ: {sql_info.get('total_length')}文字, {sql_info.get('line_count')}行")
                
                elif endpoint.startswith("/api/universities"):
                    print("🏫 大学データ:")
                    status = data.get("status", "不明")
                    total = data.get("total_universities", 0)
                    mode = data.get("mode", data.get("status", ""))
                    print(f"  - ステータス: {status}")
                    print(f"  - モード: {mode}")
                    print(f"  - 大学数: {total}")
                    
                    # 上位5校を表示
                    universities = data.get("universities", [])
                    if universities:
                        print("  - 上位5校:")
                        for i, uni in enumerate(universities[:5], 1):
                            name = uni.get("name", "不明")
                            count = uni.get("count", 0)
                            print(f"    {i}. {name}: {count}名")
                
                results[endpoint] = {
                    "status": "成功",
                    "response_time": response_time,
                    "data_summary": {
                        "status": data.get("status"),
                        "total_items": len(data.get("universities", data.get("tests", [])))
                    }
                }
                
            else:
                print(f"❌ エラーレスポンス: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"エラー内容: {error_data}")
                except:
                    print(f"エラー内容: {response.text}")
                
                results[endpoint] = {
                    "status": "失敗",
                    "error_code": response.status_code,
                    "response_time": response_time
                }
                
        except requests.RequestException as e:
            print(f"❌ リクエストエラー: {e}")
            results[endpoint] = {
                "status": "接続エラー",
                "error": str(e)
            }
        except Exception as e:
            print(f"❌ 予期しないエラー: {e}")
            results[endpoint] = {
                "status": "予期しないエラー",
                "error": str(e)
            }
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)
    
    success_count = 0
    for endpoint, result in results.items():
        status = result.get("status")
        response_time = result.get("response_time", 0)
        
        if status == "成功":
            success_count += 1
            emoji = "✅"
        else:
            emoji = "❌"
        
        print(f"{emoji} {endpoint}: {status} ({response_time:.2f}s)")
    
    print(f"\n📈 成功率: {success_count}/{len(endpoints)} ({success_count/len(endpoints)*100:.1f}%)")
    
    # 推奨事項
    print("\n💡 推奨事項:")
    if success_count == len(endpoints):
        print("✅ すべてのエンドポイントが正常に動作しています！")
    else:
        print("⚠️ 一部のエンドポイントで問題が発生しています。")
        print("  1. サーバーが起動していることを確認してください")
        print("  2. GCP認証情報が正しく設定されているか確認してください")
        print("  3. 正規化モジュールが正しく配置されているか確認してください")
    
    return results

def test_university_data_quality():
    """
    大学データの品質テスト
    """
    print("\n🔬 大学データ品質テスト")
    print("-" * 40)
    
    try:
        # メインエンドポイントをテスト
        response = requests.get("http://localhost:8000/api/universities", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            universities = data.get("universities", [])
            
            if universities:
                # データ品質チェック
                print(f"📊 データ品質分析 ({len(universities)}校)")
                
                # 名前の長さ分析
                name_lengths = [len(uni.get("name", "")) for uni in universities]
                avg_name_length = sum(name_lengths) / len(name_lengths)
                print(f"  - 平均大学名長: {avg_name_length:.1f}文字")
                
                # 研究者数分析
                counts = [uni.get("count", 0) for uni in universities]
                total_researchers = sum(counts)
                avg_count = total_researchers / len(counts)
                print(f"  - 総研究者数: {total_researchers:,}名")
                print(f"  - 平均研究者数: {avg_count:.1f}名/校")
                
                # 上位・下位校
                if len(universities) >= 5:
                    print("  - 上位3校:")
                    for i, uni in enumerate(universities[:3], 1):
                        print(f"    {i}. {uni.get('name')}: {uni.get('count'):,}名")
                    
                    print("  - 下位3校:")
                    for i, uni in enumerate(universities[-3:], len(universities)-2):
                        print(f"    {i}. {uni.get('name')}: {uni.get('count'):,}名")
                
            else:
                print("❌ 大学データが取得できませんでした")
        else:
            print(f"❌ API呼び出し失敗: {response.status_code}")
            
    except Exception as e:
        print(f"❌ データ品質テストエラー: {e}")

if __name__ == "__main__":
    print("🔧 大学API修正検証ツール")
    print("=" * 60)
    
    # エンドポイントテスト
    endpoint_results = test_university_api_endpoints()
    
    # データ品質テスト
    test_university_data_quality()
    
    print("\n✅ テスト完了")
