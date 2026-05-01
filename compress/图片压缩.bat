@echo off
chcp 65001 >nul
title 图片压缩工具箱

:: 进入脚本所在目录
cd /d "%~dp0"

:: 拖拽文件夹 → 直接压缩；双击 → 开启菜单
:: 支持: 图片压缩.bat ["源文件夹"] ["压缩质量"]
if not "%~1"=="" (
    if not "%~2"=="" (
        python "%~dp0image_compressor.py" "%~1" "%~2"
    ) else (
        python "%~dp0image_compressor.py" "%~1"
    )
) else (
    python "%~dp0image_compressor.py"
)

echo.
echo 按任意键退出...
pause >nul
