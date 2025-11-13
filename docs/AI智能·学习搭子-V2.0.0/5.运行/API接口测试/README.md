### API 接口测试说明（V2.0.0）
##### SoundTech® by Dingdust 2025.11.13
---
* 本说明用于 V2.0.0 新增接口的冒烟与基础验证。
---
* 开发默认 HTTPS：`https://localhost:443`（自签证书）；容器默认 HTTPS：`https://localhost:5000`；生产近似（waitress，HTTP）：`http://localhost:8000`。
---
* 若遇自签证书校验问题，可在命令行使用 `curl.exe -k` 或在本机信任证书后再调用。

#### 1. 目标与范围
- 在开发/部署环境下验证鉴权、入参与返回体结构。
- 覆盖 V2 新增接口与关键页面联动。

#### 2. 覆盖接口
- `POST /api/qa/ask`：题目答疑（问题文本/题号/上下文 → 答案、证据、置信度）
- `GET /api/rag/sources`：引用来源与命中详情
- `POST /api/feedback`：用户反馈（有用/无用/纠错）
- `GET /api/analytics/user`：个人统计
- `POST /api/workflows/run`：触发工作流（答疑/巩固/评估）

#### 3. 环境准备
- 开发访问：`https://localhost:443`
- 容器访问：`https://localhost:5000`
- waitress（HTTP）：`http://localhost:8000`
- 鉴权：建议先完成登录（如接口要求鉴权）；未登录应返回 `401/302`。

#### 4. 快速冒烟（示例命令）
- PowerShell（Invoke-RestMethod）：
  ```powershell
  $BASE = "https://localhost:443"
  $payload = @{ question = "测试问题" } | ConvertTo-Json
  Invoke-RestMethod -Uri "$BASE/api/qa/ask" -Method Post -Body $payload -ContentType "application/json"
  ```
- curl（Windows）：
  ```powershell
  curl.exe -k -X POST "https://localhost:443/api/qa/ask" -H "Content-Type: application/json" -d "{\"question\":\"测试问题\"}"
  ```
- 提示：根据环境将 `$BASE` 切换为容器或 waitress 地址，并按接口调整负载键名。

#### 5. 返回体与错误码规范
- 返回体统一：`code`、`message`、`data`。
- 常见状态码：`200` 成功；`400` 参数错误；`401/302` 未鉴权或重定向；`500` 服务错误。

#### 6. 集成测试建议（pytest）
- 推荐在 `tests/` 目录自建脚本，使用 Flask Test Client。
- 断言策略：对状态码采用宽松断言以兼容鉴权与参数校验差异（`200/400/401/302`）。
