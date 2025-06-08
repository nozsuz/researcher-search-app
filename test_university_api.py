#!/usr/bin/env python3
"""
大学API取得のテストスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

def test_university_normalizer():
    """正規化システムのテスト"""
    print("🧪 正規化システムテスト開始...")
    
    try:
        from university_normalizer import (
            normalize_university_name, 
            get_normalized_university_stats_query
        )
        
        # 正規化テスト
        test_cases = [
            "筑波大学附属病院",
            "東京大学史料編纂所", 
            "筑波大学医学医療系",
            "九州大学総合研究博物館",
            "北海道大学医学研究院"
        ]
        
        print("✅ 正規化モジュールインポート成功")
        
        for case in test_cases:
            normalized = normalize_university_name(case)
            status = "✅ 正規化" if case != normalized else "📝 保持"
            print(f"  '{case}' → '{normalized}' ({status})")
        
        # SQLクエリ生成テスト
        table_name = "apt-rope-217206.researcher_data.rd_250524"
        query = get_normalized_university_stats_query(table_name)
        print(f"\n✅ SQLクエリ生成成功: {len(query)}文字")
        
        return True
        
    except Exception as e:
        print(f"❌ 正規化システムエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gcp_connection():
    """GCP接続のテスト"""
    print("\n🔌 GCP接続テスト開始...")
    
    try:
        from gcp_auth import get_bigquery_client, get_gcp_status
        
        # GCPステータス確認
        status = get_gcp_status()
        print(f"📊 GCPステータス: {status}")
        
        # BigQueryクライアント取得
        bq_client = get_bigquery_client()
        
        if bq_client:
            print("✅ BigQueryクライアント取得成功")
            
            # 簡単なクエリテスト
            table_name = "apt-rope-217206.researcher_data.rd_250524"
            test_query = f"SELECT COUNT(*) as total FROM `{table_name}` LIMIT 1"
            
            print(f"🔍 テストクエリ実行: {test_query}")
            
            query_job = bq_client.query(test_query)
            results = list(query_job.result())
            
            total = results[0].total if results else 0
            print(f"✅ テストクエリ成功: {total}件の研究者データ")
            
            return True
        else:
            print("❌ BigQueryクライアントがNone")
            return False
            
    except Exception as e:
        print(f"❌ GCP接続エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_university_api():
    """大学API機能のテスト"""
    print("\n🏫 大学API機能テスト開始...")
    
    try:
        from gcp_auth import get_bigquery_client
        from university_normalizer import get_normalized_university_stats_query
        
        bq_client = get_bigquery_client()
        
        if not bq_client:
            print("❌ BigQueryクライアントが利用できません")
            return False
        
        # 正規化クエリを生成
        table_name = "apt-rope-217206.researcher_data.rd_250524"
        query = get_normalized_university_stats_query(table_name)
        
        print(f"🔍 正規化クエリ実行開始: {len(query)}文字")
        print(f"📄 クエリ先頭100文字: {query[:100]}...")
        
        # クエリ実行
        query_job = bq_client.query(query)
        
        print("⏳ クエリ実行中...")
        
        universities = []
        row_count = 0
        
        for row in query_job:
            row_count += 1
            university_data = {
                "name": row.university_name,
                "count": row.researcher_count
            }
            
            # 正規化の詳細情報
            if hasattr(row, 'original_names') and row.original_names:
                university_data["original_names"] = row.original_names
            
            universities.append(university_data)
            
            # 最初の10件を表示
            if row_count <= 10:
                original_info = ""
                if hasattr(row, 'original_names') and row.original_names and len(row.original_names) > 1:
                    original_info = f" (統合: {len(row.original_names)}校)"
                print(f"  {row_count}. {row.university_name}: {row.researcher_count}名{original_info}")
        
        print(f"\n✅ 大学API機能テスト成功: {len(universities)}校の大学")
        return True
        
    except Exception as e:
        print(f"❌ 大学API機能エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メインテスト実行"""
    print("🚀 大学API総合テスト開始")
    print("=" * 50)
    
    # 1. 正規化システムテスト
    normalizer_ok = test_university_normalizer()
    
    # 2. GCP接続テスト
    gcp_ok = test_gcp_connection()
    
    # 3. 大学API機能テスト
    api_ok = test_university_api() if gcp_ok else False
    
    print("\n" + "=" * 50)
    print("📊 テスト結果サマリー:")
    print(f"  正規化システム: {'✅ OK' if normalizer_ok else '❌ NG'}")
    print(f"  GCP接続: {'✅ OK' if gcp_ok else '❌ NG'}")
    print(f"  大学API機能: {'✅ OK' if api_ok else '❌ NG'}")
    
    if normalizer_ok and gcp_ok and api_ok:
        print("\n🎉 すべてのテストが成功しました！")
    else:
        print("\n⚠️ 一部のテストが失敗しました。上記のエラーを確認してください。")

if __name__ == "__main__":
    main()
