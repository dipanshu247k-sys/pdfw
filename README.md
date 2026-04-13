# pdfw

Run this in Windows CMD to download and extract latest qpdf and poppler binaries into "%USERPROFILE%\Downloads\pdfw-tools":

```cmd
curl -L "https://raw.githubusercontent.com/dipanshu247k-sys/pdfw/main/setup-tools.cmd" -o "%TEMP%\setup-tools.cmd" && "%TEMP%\setup-tools.cmd"
```

After setup, `%USERPROFILE%\Downloads\pdfw-tools\tools` will contain:
- `qpdf-path.json` (resolved `qpdf.exe` path)
- `pdfimages-path.json` (resolved `pdfimages.exe` path)
- `pdfimages_to_pdfw.py` (helper script downloaded from this repository)
- `delete_duplicate_files.py` (duplicate file deleter that removes all copies of duplicated content)

Use the helper script by passing a PDF path as argument:

```cmd
python "%USERPROFILE%\Downloads\pdfw-tools\tools\pdfimages_to_pdfw.py" "C:\path\to\input.pdf"
```

Use the duplicate-file deleter by passing a target folder:

```cmd
python "%USERPROFILE%\Downloads\pdfw-tools\tools\delete_duplicate_files.py" "C:\path\to\folder" --recursive
```
