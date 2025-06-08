"""
現在のRailway環境の状況確認スクリプト
認証情報が設定済みの場合の診断ツール
"""

import os
import requests
import json

def check_railway_deployment():
    """Railway デプロイメント状況確認"""
    print("🚂 Railway デプロイメント状況確認")
    print("="*40)
    
    # Railway URLを確認（環境変数またはユーザー入力）
    railway_url = os.getenv("RAILWAY_STATIC_URL") or input("Railway アプリのURL (例: https://your-app.railway.app): ").strip()
    
    if not railway_url.startswith("http"):
        railway_url = f"https://{railway_url}"
    
    endpoints_to_check = [
        ("/", "基本ヘルスチェック"),
        ("/health", "詳細ヘルスチェック"),
        ("/test/gcp", "GCP接続テスト"),
        ("/test/real-search", "実際の検索テスト"),
        ("/api/search?query=人工知能&method=keyword&max_results=2", "検索API"),
        ("/test/env", "環境変数確認")
    ]
    
    results = {}
    
    for endpoint, description in endpoints_to_check:
        print(f"\n🔍 {description} テスト...")
        print(f"   URL: {railway_url}{endpoint}")
        
        try:
            response = requests.get(f"{railway_url}{endpoint}", timeout=30)
            results[endpoint] = {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text[:200]
            }
            
            if response.status_code == 200:
                print(f"   ✅ 成功 (200)")
                
                # 特定エンドポイントの詳細確認
                if endpoint == "/health":
                    data = response.json()
                    gcp_status = data.get("gcp_details", {})
                    print(f"   📊 BigQuery: {'✅' if gcp_status.get('bigquery_ready') else '❌'}")
                    print(f"   📊 Vertex AI: {'✅' if gcp_status.get('vertex_ai_ready') else '❌'}")
                    print(f"   📊 認証情報: {'✅' if gcp_status.get('credentials_available') else '❌'}")
                
                elif endpoint == "/test/gcp":
                    data = response.json()
                    bigquery_status = data.get("tests", {}).get("bigquery", {})
                    vertex_ai_status = data.get("tests", {}).get("vertex_ai", {})
                    print(f"   📊 BigQuery: {bigquery_status.get('status', '❓')}")
                    print(f"   📊 Vertex AI: {vertex_ai_status.get('status', '❓')}")
                
                elif endpoint == "/test/real-search":
                    data = response.json()
                    print(f"   📊 検索ステータス: {data.get('test_status', '❓')}")
                    print(f"   📊 実行方法: {data.get('result_summary', {}).get('method', '❓')}")
                
                elif "api/search" in endpoint:
                    data = response.json()
                    print(f"   📊 検索ステータス: {data.get('status', '❓')}")
                    print(f"   📊 実行情報: {data.get('executed_query_info', 'N/A')[:50]}...")
                    print(f"   📊 結果件数: {data.get('total', 0)}件")
                
            else:
                print(f"   ❌ エラー ({response.status_code})")
                print(f"   📝 エラー内容: {response.text[:100]}...")
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ タイムアウト (30秒)")
            results[endpoint] = {"error": "timeout"}
        except requests.exceptions.ConnectionError:
            print(f"   🔌 接続エラー")
            results[endpoint] = {"error": "connection_error"}
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            results[endpoint] = {"error": str(e)}
    
    return results, railway_url

def analyze_results(results):
    """結果分析"""
    print("\n📊 結果分析")
    print("="*20)
    
    # 問題の特定
    issues = []
    recommendations = []
    
    if "/health" in results:
        health_result = results["/health"]
        if health_result.get("success"):
            data = health_result.get("data", {})
            gcp_details = data.get("gcp_details", {})
            
            if not gcp_details.get("bigquery_ready"):
                issues.append("BigQuery接続失敗")
                recommendations.append("BigQuery認証情報とテーブルアクセス権を確認")
            
            if not gcp_details.get("vertex_ai_ready"):
                issues.append("Vertex AI接続失敗")
                recommendations.append("Vertex AI認証情報とAPI有効化を確認")
        else:
            issues.append("ヘルスチェック失敗")
    
    if "/test/real-search" in results:
        search_result = results["/test/real-search"]
        if search_result.get("success"):
            data = search_result.get("data", {})
            if data.get("test_status") == "error":
                issues.append("実際の検索機能エラー")
                recommendations.append("GCP認証情報と権限を確認")
    
    if "api/search" in str(results.keys()):
        for endpoint, result in results.items():
            if "api/search" in endpoint and result.get("success"):
                data = result.get("data", {})
                executed_info = data.get("executed_query_info", "")
                if "モック" in executed_info:
                    issues.append("検索がモックモードで動作")
                    recommendations.append("GCP初期化設定とテーブルアクセスを確認")
    
    # 結果表示
    if not issues:
        print("✅ すべて正常に動作しています！")
        print("🎉 実際のAPI検索が有効になっています")
    else:
        print("⚠️ 検出された問題:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        
        print("\n💡 推奨対策:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")

def check_local_vs_railway():
    """ローカル環境との比較"""
    print("\n🏠 ローカル環境との比較")
    print("="*25)
    
    print("ローカル環境での確認をしますか？")
    choice = input("y/n: ").strip().lower()
    
    if choice == 'y':
        try:
            print("\n📍 ローカル環境テスト...")
            
            # ローカルのGCP設定確認
            from gcp_auth import get_gcp_status
            local_status = get_gcp_status()
            
            print("🏠 ローカルGCP状況:")
            for key, value in local_status.items():
                print(f"  {key}: {value}")
                
        except Exception as e:
            print(f"❌ ローカル環境エラー: {e}")

def main():
    """メイン関数"""
    print("🔍 Railway環境診断ツール（認証情報設定済み版）")
    print("="*50)
    
    try:
        results, railway_url = check_railway_deployment()
        analyze_results(results)
        check_local_vs_railway()
        
        print(f"\n🔗 Railway アプリURL: {railway_url}")
        print("\n📋 確認完了！")
        
        if any("モック" in str(result.get("data", "")) for result in results.values()):
            print("\n⚠️ 検索がモックモードです。以下を確認してください：")
            print("1. ENABLE_GCP_INITIALIZATION=true が設定されているか")
            print("2. BigQueryテーブルへのアクセス権があるか")
            print("3. railway.jsonが正しくmain.pyを指しているか")
        
    except KeyboardInterrupt:
        print("\n\n👋 診断を終了しました")
    except Exception as e:
        print(f"\n❌ 診断エラー: {e}")

if __name__ == "__main__":
    main()
