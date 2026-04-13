# pdfw

Run this in Windows CMD to download and extract latest qpdf and poppler binaries into "%USERPROFILE%\Downloads\pdfw-tools":

```cmd
curl -L "https://raw.githubusercontent.com/dipanshu247k-sys/pdfw/main/setup-tools.cmd" -o "%TEMP%\setup-tools.cmd" && "%TEMP%\setup-tools.cmd"
```

After setup, `%USERPROFILE%\Downloads\pdfw-tools\tools` will contain:
- `qpdf-path.json` (resolved `qpdf.exe` path)
- `pdfimages-path.json` (resolved `pdfimages.exe` path)
- `pdfw.py` (helper script downloaded from this repository)
- `dedup.py` (duplicate file deleter that removes all copies of duplicated content)

Use the helper script by passing either a PDF path or a folder path:

```cmd
python "%USERPROFILE%\Downloads\pdfw-tools\tools\pdfw.py" "C:\path\to\input.pdf"
python "%USERPROFILE%\Downloads\pdfw-tools\tools\pdfw.py" "C:\path\to\folder"
```

When given a folder, `pdfw.py` recursively processes all PDFs and writes outputs under `source_folder\pdfw-pdfs\`.

`pdfw.py` automatically runs `dedup.py` on the extracted images folder immediately after `pdfimages` finishes.

Use the duplicate-file deleter by passing a target folder:

```cmd
python "%USERPROFILE%\Downloads\pdfw-tools\tools\dedup.py" "C:\path\to\folder" --recursive
```
