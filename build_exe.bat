@echo off
rem Gera dist\SemaforoCozinha.exe (executavel unico, sem console).
rem Requisitos: Python 3 instalado. O PyInstaller e instalado se faltar.

cd /d "%~dp0"

where pyinstaller >nul 2>nul
if errorlevel 1 (
    echo Instalando PyInstaller...
    pip install pyinstaller || goto :erro
)

if not exist semaforo.ico python gen_icon.py

pyinstaller --noconfirm --onefile --windowed --name SemaforoCozinha ^
    --icon semaforo.ico semaforo.py || goto :erro

echo.
echo Pronto! Executavel em: dist\SemaforoCozinha.exe
echo Dica: marque "Iniciar com o Windows" nas configuracoes (engrenagem)
echo para abrir automaticamente ao ligar o PC.
pause
exit /b 0

:erro
echo Falha no build.
pause
exit /b 1
