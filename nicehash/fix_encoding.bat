@echo off
chcp 65001
echo 解决Git中文乱码问题
echo.

echo 1. 设置Git编码配置...
git config --global core.quotepath false
git config --global i18n.commitencoding utf-8
git config --global i18n.logoutputencoding utf-8
git config --global core.editor "notepad"

echo 2. 设置控制台编码为UTF-8...
chcp 65001

echo 3. 检查当前提交状态...
git log --oneline -3

echo.
echo 配置完成！现在Git应该能正确处理中文了。
echo 如果仍有乱码，请重新提交有问题的提交。
pause
