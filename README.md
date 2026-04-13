# pdfw

Run this in Windows CMD to download and extract latest qpdf and poppler binaries into "%USERPROFILE%\Downloads\pdfw-tools":

```cmd
powershell -NoProfile -Command "$dst=Join-Path $env:USERPROFILE 'Downloads\pdfw-tools'; New-Item -ItemType Directory -Force -Path $dst | Out-Null; $q=(Invoke-RestMethod 'https://api.github.com/repos/qpdf/qpdf/releases/latest').assets | Where-Object {$_.name -match 'windows.*zip|win.*zip|msvc.*zip'} | Select-Object -First 1; $p=(Invoke-RestMethod 'https://api.github.com/repos/oschwartz10612/poppler-windows/releases/latest').assets | Where-Object {$_.name -match 'x86_64.*zip|win64.*zip|zip$'} | Select-Object -First 1; Invoke-WebRequest $q.browser_download_url -OutFile (Join-Path $dst $q.name); Invoke-WebRequest $p.browser_download_url -OutFile (Join-Path $dst $p.name); Expand-Archive -Force (Join-Path $dst $q.name) (Join-Path $dst 'qpdf'); Expand-Archive -Force (Join-Path $dst $p.name) (Join-Path $dst 'poppler'); Write-Host 'Done:' $dst"}
```
