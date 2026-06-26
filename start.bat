@echo off
chcp 65001 >nul
title 智慧管理中心

echo ==========================================
echo    智慧管理中心启动中...
echo ==========================================
echo.

cd /d "%~dp0"

echo 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python
    pause
    exit /b 1
)

echo 安装依赖（首次运行）...
pip install flask flask-cors -q

echo.
echo 启动服务...
echo 请访问: http://localhost:5001
echo 按 Ctrl+C 停止服务
echo.

python app.py

pause
