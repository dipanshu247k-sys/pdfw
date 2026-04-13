@echo off
setlocal enabledelayedexpansion

set "DST=%USERPROFILE%\Downloads\pdfw-tools"
set "TOOLS_DIR=%DST%\tools"
set "PDFW_SCRIPT_REPO=dipanshu247k-sys/pdfw"
set "PDFW_SCRIPT_REF=main"
if not exist "%DST%" mkdir "%DST%"
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

echo [1/5] Fetching latest poppler release info...
for /f "delims=" %%i in ('powershell -NoProfile -Command "$a=(Invoke-RestMethod 'https://api.github.com/repos/oschwartz10612/poppler-windows/releases/latest').assets; ($a | Where-Object { $_.name -match 'x86_64.*zip|win64.*zip|zip$' } | Select-Object -First 1).browser_download_url"') do set "POP_URL=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "$a=(Invoke-RestMethod 'https://api.github.com/repos/oschwartz10612/poppler-windows/releases/latest').assets; ($a | Where-Object { $_.name -match 'x86_64.*zip|win64.*zip|zip$' } | Select-Object -First 1).name"') do set "POP_NAME=%%i"

if "%POP_URL%"=="" (
  echo Could not resolve poppler asset URL.
  exit /b 1
)

echo [2/5] Downloading archive...
powershell -NoProfile -Command "Invoke-WebRequest '%POP_URL%' -OutFile '%DST%\%POP_NAME%'"

echo [3/5] Extracting archive...
powershell -NoProfile -Command "Expand-Archive -Force '%DST%\%POP_NAME%' '%DST%\poppler'"

set "PDFIMAGES_EXE="
for /f "delims=" %%i in ('dir /s /b "%DST%\poppler\pdfimages.exe" 2^>nul') do (
  set "PDFIMAGES_EXE=%%i"
  goto :found_pdfimages
)
:found_pdfimages

if "%PDFIMAGES_EXE%"=="" (
  echo Could not locate pdfimages.exe after extraction.
  exit /b 1
)

echo [4/5] Writing tool path metadata...
powershell -NoProfile -Command "$o=@{pdfimages_exe='%PDFIMAGES_EXE%'}; $o | ConvertTo-Json | Set-Content -Encoding UTF8 '%TOOLS_DIR%\pdfimages-path.json'"

echo [5/5] Downloading python helper scripts...
where curl >nul 2>nul
if errorlevel 1 (
  echo curl is not available on PATH.
  exit /b 1
)
curl -L "https://raw.githubusercontent.com/%PDFW_SCRIPT_REPO%/%PDFW_SCRIPT_REF%/tools/pdfw.py" -o "%TOOLS_DIR%\pdfw.py"
if errorlevel 1 (
  echo Failed to download python helper script from %PDFW_SCRIPT_REPO% at ref %PDFW_SCRIPT_REF%.
  exit /b 1
)
curl -L "https://raw.githubusercontent.com/%PDFW_SCRIPT_REPO%/%PDFW_SCRIPT_REF%/tools/dedup.py" -o "%TOOLS_DIR%\dedup.py"
if errorlevel 1 (
  echo Failed to download duplicate file deleter script from %PDFW_SCRIPT_REPO% at ref %PDFW_SCRIPT_REF%.
  exit /b 1
)

echo Finalizing setup...
echo Done. Tools extracted to: %DST%
echo Metadata and script are available in: %TOOLS_DIR%
endlocal
