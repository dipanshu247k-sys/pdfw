@echo off
setlocal enabledelayedexpansion

set "DST=%USERPROFILE%\Downloads\pdfw-tools"
set "TOOLS_DIR=%DST%\tools"
set "PDFW_SCRIPT_REPO=dipanshu247k-sys/pdfw"
set "PDFW_SCRIPT_REF=main"
if not exist "%DST%" mkdir "%DST%"
if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

echo [1/7] Fetching latest qpdf release info...
for /f "delims=" %%i in ('powershell -NoProfile -Command "$a=(Invoke-RestMethod 'https://api.github.com/repos/qpdf/qpdf/releases/latest').assets; ($a | Where-Object { $_.name -match 'windows.*zip|win.*zip|msvc.*zip' } | Select-Object -First 1).browser_download_url"') do set "QPDF_URL=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "$a=(Invoke-RestMethod 'https://api.github.com/repos/qpdf/qpdf/releases/latest').assets; ($a | Where-Object { $_.name -match 'windows.*zip|win.*zip|msvc.*zip' } | Select-Object -First 1).name"') do set "QPDF_NAME=%%i"

echo [2/7] Fetching latest poppler release info...
for /f "delims=" %%i in ('powershell -NoProfile -Command "$a=(Invoke-RestMethod 'https://api.github.com/repos/oschwartz10612/poppler-windows/releases/latest').assets; ($a | Where-Object { $_.name -match 'x86_64.*zip|win64.*zip|zip$' } | Select-Object -First 1).browser_download_url"') do set "POP_URL=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "$a=(Invoke-RestMethod 'https://api.github.com/repos/oschwartz10612/poppler-windows/releases/latest').assets; ($a | Where-Object { $_.name -match 'x86_64.*zip|win64.*zip|zip$' } | Select-Object -First 1).name"') do set "POP_NAME=%%i"

if "%QPDF_URL%"=="" (
  echo Could not resolve qpdf asset URL.
  exit /b 1
)
if "%POP_URL%"=="" (
  echo Could not resolve poppler asset URL.
  exit /b 1
)

echo [3/7] Downloading archives...
powershell -NoProfile -Command "Invoke-WebRequest '%QPDF_URL%' -OutFile '%DST%\%QPDF_NAME%'"
powershell -NoProfile -Command "Invoke-WebRequest '%POP_URL%' -OutFile '%DST%\%POP_NAME%'"

echo [4/7] Extracting archives...
powershell -NoProfile -Command "Expand-Archive -Force '%DST%\%QPDF_NAME%' '%DST%\qpdf'"
powershell -NoProfile -Command "Expand-Archive -Force '%DST%\%POP_NAME%' '%DST%\poppler'"

set "QPDF_EXE="
set "PDFIMAGES_EXE="
for /f "delims=" %%i in ('dir /s /b "%DST%\qpdf\qpdf.exe" 2^>nul') do (
  set "QPDF_EXE=%%i"
  goto :found_qpdf
)
:found_qpdf
for /f "delims=" %%i in ('dir /s /b "%DST%\poppler\pdfimages.exe" 2^>nul') do (
  set "PDFIMAGES_EXE=%%i"
  goto :found_pdfimages
)
:found_pdfimages

if "%QPDF_EXE%"=="" (
  echo Could not locate qpdf.exe after extraction.
  exit /b 1
)
if "%PDFIMAGES_EXE%"=="" (
  echo Could not locate pdfimages.exe after extraction.
  exit /b 1
)

echo [5/7] Writing tool path metadata...
powershell -NoProfile -Command "$o=@{qpdf_exe='%QPDF_EXE%'}; $o | ConvertTo-Json | Set-Content -Encoding UTF8 '%TOOLS_DIR%\qpdf-path.json'"
powershell -NoProfile -Command "$o=@{pdfimages_exe='%PDFIMAGES_EXE%'}; $o | ConvertTo-Json | Set-Content -Encoding UTF8 '%TOOLS_DIR%\pdfimages-path.json'"

echo [6/7] Downloading python helper scripts...
where curl >nul 2>nul
if errorlevel 1 (
  echo curl is not available on PATH.
  exit /b 1
)
curl -L "https://raw.githubusercontent.com/%PDFW_SCRIPT_REPO%/%PDFW_SCRIPT_REF%/tools/pdfimages_to_pdfw.py" -o "%TOOLS_DIR%\pdfimages_to_pdfw.py"
if errorlevel 1 (
  echo Failed to download python helper script from %PDFW_SCRIPT_REPO% at ref %PDFW_SCRIPT_REF%.
  exit /b 1
)
curl -L "https://raw.githubusercontent.com/%PDFW_SCRIPT_REPO%/%PDFW_SCRIPT_REF%/tools/delete_duplicate_files.py" -o "%TOOLS_DIR%\delete_duplicate_files.py"
if errorlevel 1 (
  echo Failed to download duplicate file deleter script from %PDFW_SCRIPT_REPO% at ref %PDFW_SCRIPT_REF%.
  exit /b 1
)

echo [7/7] Finalizing setup...
echo Done. Tools extracted to: %DST%
echo Metadata and script are available in: %TOOLS_DIR%
endlocal
