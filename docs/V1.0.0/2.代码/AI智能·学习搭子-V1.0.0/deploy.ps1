Write-Host "正在下载Python 3.14.0 64位嵌入版本..."
curl https://www.python.org/ftp/python/3.14.0/python-3.14.0-embed-amd64.zip --output .\python314-embed.zip
Clear-Host

New-Item -Path .\python314-embed -ItemType Directory
Expand-Archive -Path .\python314-embed.zip -DestinationPath .\python314-embed
Remove-Item -Path .\python314-embed.zip
Clear-Host

Set-Location .\python314-embed
Set-Content -Path ".\python314._pth" -Value @"
python314.zip
.
..
import site
"@
Clear-Host
Write-Host "正在下载项目部署依赖..."
curl https://bootstrap.pypa.io/get-pip.py --output .\get-pip.py 
.\python.exe .\get-pip.py --no-warn-script-location
.\python.exe -m pip install -r ..\requirements.txt --index-url https://mirrors.aliyun.com/pypi/simple/ --no-warn-script-location
Clear-Host

Set-Location ..