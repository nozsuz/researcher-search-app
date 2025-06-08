import os
import shutil

# 削除するファイルのリスト
files_to_delete = [
    # バックアップファイル
    "api_endpoints.py.backup",
    "api_server.py.backup",
    "real_search_original.py.backup",
    "real_search_without_evaluation.py.backup",
    "researcher_search_app.py.backup",
    "simple_api.py.backup",
    "start_server.py.backup",
    "test-ai-analysis.html.bak",
    
    # 重複ファイル
    "full_api.py",
    "requirements_simple.txt",
    
    # 古いドキュメント
    "railway-env-guide.md",
    "railway-env-setup.txt",
    "railway_env_setup.md",
    
    # 開発用ファイル
    "test_auth.py",
    "test_local.sh",
    "check_permissions.md",
    
    # 新しく追加された不要なファイル
    # テストファイル群
    "test_national_university_complete.py",
    "test_national_university_fix.py",
    "test_simple_normalizer.py",
    "test_sql_tokai.py",
    "test_tokai_fix.py",
    "test_tokai_normalization.py",
    "test_university_api.py",
    "test_university_filtering_fix.py",
    "test_university_fix.py",
    "test_university_normalizer.py",
    "test_university_status.py",
    "university_final_tester.py",
    "university_perfect_tester.py",
    "quick_test_tokai.py",
    
    # 重複した正規化ファイル
    "university_normalizer_complete.py",
    "university_normalizer_final.py",
    "university_normalizer_fixed.py",
    "university_normalizer_perfect.py",
    "university_normalizer_safe.py",
    "university_normalizer_simple.py",
    
    # 重複したAPIファイル
    "university_api_enhanced.py",
    "university_api_final.py",
    
    # その他の重複・不要ファイル
    "university_cleanup_strategy.py",
    "safe_normalization_queries.py",
    "normalization_report_generator.py",
    "investigate_university_data.py",
    "check_railway_status.py",
    "deploy_fix.sh",
    "railway_fix.py",
    "setup_auth.py",
    "TOKAI_FIX_REPORT.md",
    "DEPLOYMENT_GUIDE.md",
    "API_INTEGRATION_GUIDE.md",
    
    # 残った不要ファイル（精査済み）
    "analysis_storage.py",    # 分析結果保存機能（未使用確認済み）
    # "evaluation_system.py",  # 研究者評価システム（real_search.pyで使用中、無効化済み）
    # "gcp_auth.py",           # GCP認証（main.pyとreal_search.pyで重要モジュール）
    "university_normalizer.py",  # 壊れた大学名正規化ファイル（代替版使用中）
    
    # その他
    ".railway-disable"
]

# 削除するディレクトリのリスト
dirs_to_delete = [
    ".streamlit_backup",
    "test_env",
    "__pycache__"
]

# ファイルを削除
for file in files_to_delete:
    file_path = os.path.join(os.path.dirname(__file__), file)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"✅ 削除成功: {file}")
        except Exception as e:
            print(f"❌ 削除失敗: {file} - {e}")
    else:
        print(f"⚠️ ファイルが見つかりません: {file}")

# ディレクトリを削除
for dir in dirs_to_delete:
    dir_path = os.path.join(os.path.dirname(__file__), dir)
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
            print(f"✅ ディレクトリ削除成功: {dir}")
        except Exception as e:
            print(f"❌ ディレクトリ削除失敗: {dir} - {e}")
    else:
        print(f"⚠️ ディレクトリが見つかりません: {dir}")

print("\n🎉 クリーンアップ完了！")
