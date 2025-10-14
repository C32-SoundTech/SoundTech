# 安装、部署脚本（可实现在Windows系统上从零一键运行）
# Get-ExecutionPolicy
# Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

Clear-Host
Write-Host "Downloading SoundTech V1.0.0 Windows version..."
curl https://gitee.com/dingdust/SoundTech-Release/raw/main/V1.0.0-Windows.zip -o .\one-click-to-install.zip
New-Item -Path .\SoundTech -ItemType Directory
Expand-Archive -Path .\one-click-to-install.zip -DestinationPath .\SoundTech
Remove-Item -Path .\one-click-to-install.zip
Set-Location .\SoundTech

Clear-Host
Write-Host "Downloading Python 3.14.0 64-bit embedded version..."
curl https://gitee.com/dingdust/SoundTech-Release/raw/main/python-3.14.0-embed-amd64.zip -o .\python314-embed.zip

Clear-Host
Write-Host "Setting up Python 3.14.0 64-bit embedded version..."
New-Item -Path .\python314-embed -ItemType Directory
Expand-Archive -Path .\python314-embed.zip -DestinationPath .\python314-embed
Remove-Item -Path .\python314-embed.zip
Set-Location .\python314-embed
curl https://gitee.com/dingdust/SoundTech-Release/raw/main/python314.zip -o .\python314.zip 

Clear-Host
Write-Host "Downloading necessary requirements..."
curl https://gitee.com/dingdust/SoundTech-Release/raw/main/get-pip.py -o .\get-pip.py 
.\python.exe .\get-pip.py --no-warn-script-location
.\python.exe -m pip install -r ..\requirements.txt --index-url https://mirrors.aliyun.com/pypi/simple/ --no-warn-script-location
Set-Location ..

Clear-Host
.\python314-embed\python.exe .\app.py --port 8888
