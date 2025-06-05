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
