# 彻底修复Git乱码问题的PowerShell脚本
Write-Host "开始彻底修复Git乱码问题..." -ForegroundColor Green

# 设置Git编码配置
Write-Host "1. 重新配置Git编码设置..." -ForegroundColor Yellow
git config --global core.quotepath false
git config --global i18n.commitencoding utf-8
git config --global i18n.logoutputencoding utf-8
git config --global core.editor "notepad"

# 设置控制台编码
Write-Host "2. 设置控制台编码为UTF-8..." -ForegroundColor Yellow
chcp 65001

# 备份当前分支
Write-Host "3. 备份当前分支..." -ForegroundColor Yellow
git branch backup-main

# 使用filter-branch重写提交历史
Write-Host "4. 重写提交历史，修复乱码..." -ForegroundColor Yellow
$env:FILTER_BRANCH_SQUELCH_WARNING=1

# 创建消息过滤器脚本
$filterScript = @'
#!/bin/bash
if [ "$GIT_COMMIT" = "975de02" ]; then
    echo "feat: Add enhanced features - Auto recharge and smart speed limiting"
elif [ "$GIT_COMMIT" = "0562473" ]; then
    echo "Initial commit: NiceHash automation mining bot"
else
    cat
fi
'@

$filterScript | Out-File -FilePath "msg_filter.sh" -Encoding UTF8

# 执行filter-branch
git filter-branch --msg-filter "bash msg_filter.sh" -- --all

# 清理临时文件
Remove-Item "msg_filter.sh" -ErrorAction SilentlyContinue

Write-Host "5. 检查修复结果..." -ForegroundColor Yellow
git log --oneline -10

Write-Host ""
Write-Host "修复完成！现在可以强制推送到GitHub。" -ForegroundColor Green
Write-Host "使用命令: git push --force-with-lease origin main" -ForegroundColor Cyan