@echo off
echo ============================================
echo  Zaneva Pose Generator - Setup & Run
echo ============================================
echo.

REM Cek Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan!
    echo.
    echo Cara install:
    echo 1. Buka https://python.org/downloads
    echo 2. Download Python 3.11 atau 3.12
    echo 3. SAAT INSTALL, CENTANG "Add Python to PATH" ^<-- PENTING!
    echo 4. Setelah install, TUTUP jendela ini dan buka lagi
    echo.
    pause
    exit /b 1
)

echo [OK] Python ditemukan:
python --version
echo.

echo [1/2] Install dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Gagal install dependencies!
    echo Coba jalankan CMD sebagai Administrator
    pause
    exit /b 1
)

echo.
echo [2/2] Jalankan app...
echo Buka browser: http://localhost:5003
echo Password: zaneva2024
echo.
echo JANGAN tutup jendela ini!
echo.
python app.py
pause
