@echo off
chcp 65001 >nul
title AI Trading Bot

echo ══════════════════════════════════════════
echo     🤖 AI Trading Bot - نظام التداول الذكي
echo ══════════════════════════════════════════
echo.

:: التحقق من Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python غير مثبت!
    echo    قم بتثبيت Python 3.10+ من: https://python.org
    pause
    exit /b 1
)

:: التحقق من .env
if not exist "%~dp0.env" (
    echo ⚠️  ملف .env غير موجود
    echo    جارٍ نسخ .env.example...
    copy "%~dp0.env.example" "%~dp0.env" >nul
    echo ✅ تم إنشاء .env - قم بتعديله وأضف المفاتيح
    echo.
    echo 📝 افتح الملف: %~dp0.env
    echo    وأضف:
    echo    - BINANCE_API_KEY
    echo    - BINANCE_API_SECRET
    echo    - TELEGRAM_BOT_TOKEN
    echo    - TELEGRAM_CHAT_ID
    echo.
    pause
    exit /b 0
)

:: التحقق من المكتبات
echo 📦 التحقق من المكتبات...
pip install -r "%~dp0requirements.txt" --quiet 2>nul

:: إنشاء المجلدات
if not exist "%~dp0logs" mkdir "%~dp0logs"
if not exist "%~dp0models" mkdir "%~dp0models"

echo.
echo ✅ كل شيء جاهز!
echo 🚀 بدء التشغيل...
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

:: التشغيل مع إعادة التشغيل التلقائي
:loop
python "%~dp0main.py"
echo.
echo ⚠️  البوت توقف. إعادة التشغيل خلال 10 ثواني...
echo    اضغط Ctrl+C للإيقاف النهائي
timeout /t 10 /nobreak >nul
goto loop
