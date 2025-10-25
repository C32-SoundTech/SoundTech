$rootDir = Get-Location
$pythonDir = "$rootDir\python-3.12.9"
if (Test-Path $pythonDir) {
    Remove-Item -Path $pythonDir -Recurse
}
New-Item -Path $pythonDir -ItemType Directory
Clear-Host
Write-Host "Downloading python312.dll"
curl https://gitee.com/dingdust/SoundTech-Release/raw/main/python312/python312.dll -o "$pythonDir\python312.dll"
Write-Host "Downloading python312.zip"
curl https://gitee.com/dingdust/SoundTech-Release/raw/main/python312/python312.zip -o "$pythonDir\python312.zip"
Write-Host "Downloading libcrypto-3.dll"
curl https://gitee.com/dingdust/SoundTech-Release/raw/main/python312/libcrypto-3.dll -o "$pythonDir\libcrypto-3.dll"
Write-Host "Downloading python-3.12.9.zip"
curl https://gitee.com/dingdust/SoundTech-Release/raw/main/python312/python-3.12.9.zip -o "$rootDir\python-3.12.9.zip"
Expand-Archive -Path "$rootDir\python-3.12.9.zip" -DestinationPath $pythonDir
Remove-Item -Path "$rootDir\python-3.12.9.zip"

Clear-Host
curl https://gitee.com/dingdust/SoundTech-Release/raw/main/V2.0.0-Windows.zip -o "$rootDir\SoundTech-Release.zip"
Expand-Archive -Path "$rootDir\SoundTech-Release.zip" -DestinationPath $rootDir
Remove-Item -Path "$rootDir\SoundTech-Release.zip"

Clear-Host
$env:Path = "$pythonDir;$env:Path"
python .\python-3.12.9\get-pip.py --no-warn-script-location
Remove-Item -Path "$pythonDir\get-pip.py"

Clear-Host
$env:Path = "$pythonDir\Scripts;$env:Path"
pip install agentuniverse --index-url https://mirrors.aliyun.com/pypi/simple/ --no-warn-script-location
pip install pypdf --index-url https://mirrors.aliyun.com/pypi/simple/ --no-warn-script-location

Clear-Host