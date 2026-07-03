@echo off
echo ============================================
echo   DiskDuran - Generando instalador
echo ============================================
echo.

:: 1. Dependencias
echo [1/4] Instalando dependencias...
pip install -r requirements.txt >nul 2>&1
echo       Hecho.
echo.

:: 2. Generar icono si no existe
if not exist "icon.ico" (
    echo [2/4] Generando icono...
    python generate_icon.py
    echo       Hecho.
) else (
    echo [2/4] Icono encontrado.
)
echo.

:: 3. Crear .exe con PyInstaller
echo [3/4] Compilando ejecutable...
pyinstaller --noconfirm --onedir --windowed ^
    --name "DiskDuran" ^
    --icon "icon.ico" ^
    --add-data "static;static" ^
    --add-data "server.py;." ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import uvicorn.protocols.websockets ^
    --hidden-import uvicorn.protocols.websockets.auto ^
    --hidden-import uvicorn.lifespan ^
    --hidden-import uvicorn.lifespan.on ^
    --hidden-import uvicorn.lifespan.off ^
    --collect-all webview ^
    main.py
echo       Hecho.
echo.

:: 4. Crear instalador con Inno Setup
echo [4/4] Creando instalador...
where iscc >nul 2>&1
if %errorlevel%==0 (
    iscc installer.iss
    echo.
    echo ============================================
    echo   LISTO! Tu instalador esta en:
    echo   installer_output\DiskDuran_Setup.exe
    echo ============================================
) else (
    :: Buscar Inno Setup en rutas comunes
    set "ISCC="
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

    if defined ISCC (
        "%ISCC%" installer.iss
        echo.
        echo ============================================
        echo   LISTO! Tu instalador esta en:
        echo   installer_output\DiskDuran_Setup.exe
        echo ============================================
    ) else (
        echo.
        echo [!] Inno Setup no encontrado.
        echo     Descargalo de: https://jrsoftware.org/isdl.php
        echo     Instalalo y vuelve a ejecutar este script.
        echo.
        echo     Mientras tanto puedes usar directamente:
        echo     dist\DiskDuran\DiskDuran.exe
    )
)
echo.
pause
