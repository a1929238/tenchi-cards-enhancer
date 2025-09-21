@echo off
chcp 65001 >nul

:: 激活虚拟环境
call "F:\My RTE\Python\Venv\tenchi-cards-enhancer\Scripts\activate"

:: 打包
pyinstaller "F:\My Project\Python\tenchi-cards-enhancer\TenchiCardEnhancer.py" ^
--name="天知强卡器" ^
--noconfirm ^
--console ^
--icon="F:\My Project\Python\tenchi-cards-enhancer\items\icon\furina.ico" ^
--add-data="GUI;GUI" ^
--add-data="items;items" ^
--upx-dir="D:\Program Files\upx-4.2.4-win64" ^
--clean
--exclude-module="PyQt6.QtQuickWidgets" ^
--exclude-module="PyQt6.QtOpenGL" ^
--exclude-module="PyQt6.QtPositioning" ^
--exclude-module="PyQt6.QtQml" ^
--hidden-import="plyer.platforms.win.notification" ^

:: 清理构建文件
echo 清理构建文件...
rmdir /s /q build >nul 2>&1

pause