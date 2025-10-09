#### 2025.9.26

* 将项目重构为`FastAPI`实现 ? $/rightarrow$ 失败，存至`docs\Dingdust\storage`

#### 2025.10.1~

* 使用waitress部署Flask（uWSGI需要在LINUX的C语言环境下编译）

* 由于waitress默认不支持HTTPS，如若部署HTTPS，需要使用uWSGI或Flask默认的HTTPS支持
* 使用OpenSSL，进行HTTPS加密部署(参见OpenSSL.md)
