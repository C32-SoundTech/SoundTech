## 安装 OpenSSL

* 双击`tools\openssl-installer.exe`

* 添加环境变量`C:\Program Files\OpenSSL-Win64\bin`

* 运行以下代码

* ```bash
  openssl req -newkey rsa:2048 -nodes -keyout ./static/localhost.key -x509 -days 365 -out ./static/localhost.crt
  ```