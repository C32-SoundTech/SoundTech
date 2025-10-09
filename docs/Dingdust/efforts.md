#### 2025.9.26

* 将项目重构为`FastAPI`实现 ? $/rightarrow$ 失败，存至`docs\Dingdust\storage`

* 探索MCP-Agent的使用(蚂蚁集团，AgentUniverse，多智能体协同框架)
* 探索数字人交互的使用(阿里云通义实验室，OpenAvatarChat & Live-Talking & 腾讯， MuseTalk)
* 探索代码沙箱的使用

#### 2025.10.1~

* 使用waitress部署Flask（uWSGI需要在LINUX的C语言环境下编译）

* 由于waitress默认不支持HTTPS，如若部署HTTPS，需要使用uWSGI或Flask默认的HTTPS支持
* 使用OpenSSL，进行HTTPS加密部署(参见OpenSSL.md)
