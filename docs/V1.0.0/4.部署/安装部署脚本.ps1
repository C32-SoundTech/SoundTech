Clear-Host

Write-Host "此脚本适用于创建HTTPS协议所需的SSL自签名证书，请确保已安装OpenSSL！"

if (-not (Get-Command openssl -ErrorAction SilentlyContinue)) {
    Write-Host "检测不到可执行的OpenSSL环境，请先安装OpenSSL！"
    Write-Host "https://www.openssl.org/"
    exit 1
}

openssl req -newkey rsa:2048 -nodes -keyout ./static/localhost.key -x509 -days 365 -out ./static/localhost.crt
Clear-Host
Write-Host "自签名证书创建完成！"
