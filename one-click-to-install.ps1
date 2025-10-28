# one-click-to-install.ps1 Windows-Version
# Get-ExecutionPolicy
# Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

Clear-Host
$rootDir = (Get-Location).Path
$pythonDir = Join-Path $rootDir 'python-3.11.9'
$itemsToRemove = @(
    $pythonDir,
    (Join-Path $rootDir 'agentic'),
    (Join-Path $rootDir 'config'),
    (Join-Path $rootDir 'handlers'),
    (Join-Path $rootDir 'logs'),
    (Join-Path $rootDir 'resources'),
    (Join-Path $rootDir 'static'),
    (Join-Path $rootDir 'templates'),
    (Join-Path $rootDir '.gitignore'),
    (Join-Path $rootDir 'app.py')
)

foreach ($p in $itemsToRemove) {
    if ($null -ne $p -and (Test-Path -LiteralPath $p)) {
        $isDir = $false
        try {
            $isDir = (Get-Item -LiteralPath $p).PSIsContainer
        } catch {
            $isDir = $false
        }
        if ($isDir) {
            Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue -Confirm:$false
        } else {
            Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue -Confirm:$false
        }
    }
}
New-Item -Path $pythonDir -ItemType Directory -Force | Out-Null

Clear-Host
Write-Host "Downloading python311.dll"
Invoke-WebRequest -Uri 'https://gitee.com/dingdust/SoundTech-Release/raw/main/python311/python311.dll' -OutFile "$pythonDir\python311.dll"
Write-Host "Downloading python311.zip"
Invoke-WebRequest -Uri 'https://gitee.com/dingdust/SoundTech-Release/raw/main/python311/python311.zip' -OutFile "$pythonDir\python311.zip"
Write-Host "Downloading libcrypto-3.dll"
Invoke-WebRequest -Uri 'https://gitee.com/dingdust/SoundTech-Release/raw/main/python311/libcrypto-3.dll' -OutFile "$pythonDir\libcrypto-3.dll"
Write-Host "Downloading python-3.11.9.zip"
Invoke-WebRequest -Uri 'https://gitee.com/dingdust/SoundTech-Release/raw/main/python311/python-3.11.9.zip' -OutFile "$rootDir\python-3.11.9.zip"
Expand-Archive -Path "$rootDir\python-3.11.9.zip" -DestinationPath $pythonDir -Force
Remove-Item -LiteralPath "$rootDir\python-3.11.9.zip" -Force -ErrorAction SilentlyContinue -Confirm:$false

Clear-Host
Write-Host "Downloading SoundTech-Release.zip"
Invoke-WebRequest -Uri 'https://gitee.com/dingdust/SoundTech-Release/raw/main/V2.0.0-Windows.zip' -OutFile "$rootDir\SoundTech-Release.zip"
Expand-Archive -Path "$rootDir\SoundTech-Release.zip" -DestinationPath $rootDir -Force
Write-Host "Downloading database.zip"
Remove-Item -LiteralPath "$rootDir\SoundTech-Release.zip" -Force -ErrorAction SilentlyContinue -Confirm:$false
Invoke-WebRequest -Uri 'https://gitee.com/dingdust/SoundTech-Release/raw/main/database.zip' -OutFile "$rootDir\static\database.zip"
Expand-Archive -Path "$rootDir\static\database.zip" -DestinationPath "$rootDir\static" -Force
Remove-Item -LiteralPath "$rootDir\static\database.zip" -Force -ErrorAction SilentlyContinue -Confirm:$false
Write-Host "Downloading chroma.zip"
Invoke-WebRequest -Uri 'https://gitee.com/dingdust/SoundTech-Release/raw/main/chroma.zip' -OutFile "$rootDir\static\chroma.zip"
Expand-Archive -Path "$rootDir\static\chroma.zip" -DestinationPath "$rootDir\static" -Force
Remove-Item -LiteralPath "$rootDir\static\chroma.zip" -Force -ErrorAction SilentlyContinue -Confirm:$false

Clear-Host
$env:Path = "$pythonDir;$env:Path"
python .\python-3.11.9\get-pip.py --index-url https://pypi.tuna.tsinghua.edu.cn/simple/ --no-warn-script-location 
Remove-Item -LiteralPath "$pythonDir\get-pip.py" -Force -ErrorAction SilentlyContinue -Confirm:$false

Clear-Host
$env:Path = "$pythonDir\Scripts;$env:Path"
pip install agentuniverse==0.0.18 --index-url https://pypi.tuna.tsinghua.edu.cn/simple/ --no-warn-script-location

Clear-Host
$api_key = Read-Host "Please enter your API key"
Set-Content -Path "$rootDir\config\custom_key.toml" -Encoding ascii -Value @"
[KEY_LIST]
DASHSCOPE_API_KEY='$api_key'
DASHSCOPE_API_BASE='https://dashscope.aliyuncs.com/compatible-mode/v1'
"@

Clear-Host
python app.py