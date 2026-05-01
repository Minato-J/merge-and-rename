@echo off
chcp 65001 >nul
title 图片工具箱

:: 进入脚本所在目录
cd /d "%~dp0"

:: 拖拽文件夹 → 直接拼接；双击 → 开启菜单
:: 支持: 图片拼接.bat "源文件夹" ["输出文件名"] ["输出文件夹"]
if not "%~1"=="" (
    if not "%~2"=="" (
        if not "%~3"=="" (
            python "%~dp0image_merger.py" "%~1" "%~2" "%~3"
        ) else (
            python "%~dp0image_merger.py" "%~1" "%~2"
        )
    ) else (
        python "%~dp0image_merger.py" "%~1"
    )
) else (
    python "%~dp0image_merger.py"
)

echo.
echo 按任意键退出...
pause >nul
