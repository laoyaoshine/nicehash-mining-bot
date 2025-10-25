@echo off
echo Attempting to push to GitHub...
git push origin main
if %errorlevel% neq 0 (
    echo Push failed, trying alternative method...
    git push --set-upstream origin main
)
pause
