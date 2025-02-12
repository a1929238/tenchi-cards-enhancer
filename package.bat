@echo off
chcp 65001
call .venv\Scripts\activate
pyinstaller 天知强卡器.spec
echo 清理构建文件...
rmdir /s /q build
pause