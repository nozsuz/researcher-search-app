@echo off
echo ========================================
echo   研究者検索API サーバー起動スクリプト
echo ========================================

cd /d "C:\Users\nozsu\researcher-search-app"

echo.
echo 現在のディレクトリ: %CD%
echo.

echo Python環境確認中...
python --version
if %errorlevel% neq 0 (
    echo エラー: Pythonが見つかりません
    pause
    exit /b 1
)

echo.
echo 必要なファイル確認中...
if not exist "main.py" (
    echo エラー: main.pyが見つかりません
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo エラー: requirements.txtが見つかりません
    pause
    exit /b 1
)

echo.
echo 依存関係インストール中...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 警告: パッケージのインストールに問題がありました
)

echo.
echo ========================================
echo   サーバー起動中... (ポート: 8000)
echo ========================================
echo.
echo ブラウザで以下にアクセス:
echo   - API基本: http://localhost:8000
echo   - テストツール: http://localhost:8000/test_api.html
echo.
echo 停止するには Ctrl+C を押してください
echo.

python main.py

pause
