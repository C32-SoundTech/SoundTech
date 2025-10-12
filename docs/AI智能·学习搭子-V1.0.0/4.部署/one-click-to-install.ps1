curl https://gitee.com/dingdust/SoundTech/raw/main/V1.0.0-Windows.zip -o .\one-click-to-install.zip
New-Item -Path .\SoundTech -ItemType Directory
Expand-Archive -Path .\one-click-to-install.zip -DestinationPath .\SoundTech
Remove-Item -Path .\one-click-to-install.zip
Set-Location .\SoundTech
Clear-Host
deploy