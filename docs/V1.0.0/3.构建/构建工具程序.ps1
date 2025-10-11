Clear-Host

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "检测不到可执行的Python环境，请先安装Python！"
    Write-Host "https://www.python.org/"
    exit 1
}

Write-Host "正在创建Python虚拟环境......"
python -m venv .venv
.venv\Scripts\Activate
Clear-Host
Write-Host "正在安装项目依赖包......"
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
python.exe -m pip install --upgrade pip
Clear-Host
pip install -r requirements.txt
Clear-Host
Write-Host "项目依赖安装完成！"
