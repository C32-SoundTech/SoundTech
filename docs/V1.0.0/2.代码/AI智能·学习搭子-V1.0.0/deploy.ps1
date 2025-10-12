Clear-Host
Write-Host "Downloading Python 3.14.0 64-bit embedded version..."
curl https://www.python.org/ftp/python/3.14.0/python-3.14.0-embed-amd64.zip -o .\python314-embed.zip
Clear-Host

New-Item -Path .\python314-embed -ItemType Directory
Expand-Archive -Path .\python314-embed.zip -DestinationPath .\python314-embed
Remove-Item -Path .\python314-embed.zip
Clear-Host

Set-Location .\python314-embed
Set-Content -Path ".\python314._pth" -Encoding ascii -Value @"
python314.zip
.
..
import site
"@
Clear-Host
Write-Host "Downloading necessary requirements..."
curl https://bootstrap.pypa.io/get-pip.py -o .\get-pip.py 
.\python.exe .\get-pip.py --no-warn-script-location
.\python.exe -m pip install -r ..\requirements.txt --index-url https://mirrors.aliyun.com/pypi/simple/ --no-warn-script-location
Set-Location ..
Clear-Host

.\python314-embed\python.exe .\app.py