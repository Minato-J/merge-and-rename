@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title 图片智能重命名工具 (带错误日志版)

:: 调用 PowerShell 执行逻辑（已修正 Skip 13）
powershell -NoProfile -ExecutionPolicy Bypass -Command "$env:TOOL_DIR='%~dp0'; Get-Content -LiteralPath '%~f0' -Encoding UTF8 | Select-Object -Skip 13 | Out-String | Invoke-Expression"

echo.
echo ---------------------------------------
echo 任务结束。
pause
exit /b

# --- PowerShell 脚本部分 ---
$dir = $env:TOOL_DIR
$exts = @('.jpg', '.png', '.jpeg', '.gif', '.bmp', '.webp')

# 1. 模式选择交互
Write-Host "请选择运行模式：" -ForegroundColor Cyan
Write-Host " [1] 预览模式 (仅查看结果，不修改文件)"
Write-Host " [2] 正式重命名 (直接修改文件)"
$choice = Read-Host "输入数字并按回车"

$isPreview = $true
if ($choice -eq '2') {
    $isPreview = $false
    Write-Host "`n--- 正在执行正式重命名 ---" -ForegroundColor Yellow
} else {
    Write-Host "`n--- 当前处于：预览模式 (只读) ---" -ForegroundColor Magenta
}

# 获取目录中的所有支持扩展名的文件
$files = Get-ChildItem -LiteralPath $dir -File | Where-Object { $exts -contains $_.Extension.ToLower() }

# 如果没有找到符合条件的文件
if ($files.Count -eq 0) {
    Write-Host "未发现支持的图片文件。" -ForegroundColor Gray
    exit
}

# 错误日志文件
$errorLogPath = Join-Path -Path $dir -ChildPath "error.txt"

# 开始遍历文件并进行重命名操作
foreach ($file in $files) {
    # 2. 初始清理：去除原文件名最左侧和最右侧的空格 (Trim)
    $name = $file.BaseName.Trim()
    $ext = $file.Extension

    try {
        # 3. 正则匹配
        if ($name -match '^(.*?)(\d+)$') {
            # 深度清理：提取前缀，并去除前缀末尾可能残留的空格、横杠或下划线 (TrimEnd)
            $prefix = $Matches[1].TrimEnd(' ', '_', '-')
            
            $numStr = $Matches[2]
            $num = [long]$numStr
            
            # 拼接新文件名：干净的前缀 + 两位数 + 扩展名
            $newName = "{0}{1:D2}{2}" -f $prefix, $num, $ext
        } else {
            # 如果没有数字，同样清理末尾的特殊符号再加 01
            $cleanName = $name.TrimEnd(' ', '_', '-')
            $newName = "{0}01{1}" -f $cleanName, $ext
        }

        $newPath = Join-Path -Path $dir -ChildPath $newName

        # 4. 执行逻辑与颜色输出
        if ($file.FullName -ne $newPath) {
            if ($isPreview) {
                Write-Host "拟重命名: " -NoNewline -ForegroundColor Gray
                Write-Host "$($file.Name)" -NoNewline -ForegroundColor White
                Write-Host " -> " -NoNewline -ForegroundColor Gray
                Write-Host "$newName" -ForegroundColor Cyan
            } else {
                if (-not (Test-Path -LiteralPath $newPath)) {
                    # 只有正式执行时才会触发这里的错误并被 catch 捕获
                    Rename-Item -LiteralPath $file.FullName -NewName $newName -ErrorAction Stop
                    Write-Host "成功: $($file.Name) -> $newName" -ForegroundColor Green
                } else {
                    Write-Host "跳过: $newName (目标已存在)" -ForegroundColor Yellow
                }
            }
        }
    } catch {
        # 错误信息输出到 error.txt 文件，增加了 -Encoding UTF8 防止中文乱码
        $errorMessage = "[$('{0:yyyy-MM-dd HH:mm:ss}' -f (Get-Date))] 错误: 无法修改文件 $($file.Name) - $($_.Exception.Message)"
        Write-Host $errorMessage -ForegroundColor Red
        $errorMessage | Out-File -Append -FilePath $errorLogPath -Encoding UTF8
    }
}
