### 前端接口接入测试说明（V2.0.0）
* 本说明用于在真实服务下验证核心页面与交互的可用性与接口联动。
---
* 开发默认 HTTPS：`https://localhost:443`（自签证书）；容器默认 HTTPS：`https://localhost:5000`；生产近似（waitress，HTTP）：`http://localhost:8000`。
---
* 若遇自签证书校验问题，建议使用 `curl.exe -k` 或配置 Playwright `ignoreHTTPSErrors: true`。

#### 1. 测试范围
- 路由与页面：`/`、`/browse`、`/login`、`/register`、`/statistics`、`/exam`、`/favorites`、`/history`、`/wrong`、`/timed_mode`
- 交互要点：
  - 搜索与过滤（桌面/移动搜索框、类型/难度筛选、分页/跳转）
  - 高级筛选弹窗（打开/关闭、参数生效）
  - 定时模式（倒计时、提交、结果提示）
  - 登录与注册（表单校验、错误提示）
  - 闪消息与移动菜单（显示/关闭、响应式行为）

#### 2. 快速冒烟（无需脚本）
- 使用 curl（Windows）：
  ```powershell
  curl.exe -k "https://localhost:443/" -I
  curl.exe -k "https://localhost:443/browse" -I
  curl.exe -k "https://localhost:443/login" -I
  ```
- 切换为容器或 waitress 时，将基地址改为 `https://localhost:5000` 或 `http://localhost:8000`。

#### 3. Playwright 冒烟（可选）
- 依赖安装：
  ```powershell
  pip install playwright
  python -m playwright install
  ```
- 示例脚本（可复制为 `playwright_smoke.py` 运行）：
  ```python
  import os
  from playwright.sync_api import sync_playwright
  
  BASE = os.getenv("BASE_URL", "https://localhost:443")
  
  def main():
      with sync_playwright() as p:
          browser = p.chromium.launch()
          context = browser.new_context(ignore_https_errors=True)
          page = context.new_page()
          for path in ["/", "/browse", "/login", "/register", "/statistics", "/exam", 
                       "/favorites", "/history", "/wrong", "/timed_mode"]:
              url = f"{BASE}{path}"
              print("Visiting", url)
              page.goto(url, wait_until="domcontentloaded")
              page.screenshot(path=f"screenshot_{path.strip('/').replace('/', '_') or 'home'}.png")
          browser.close()
  
  if __name__ == "__main__":
      main()
  ```
- 运行：
  ```powershell
  $env:BASE_URL = "https://localhost:443"
  python .\playwright_smoke.py
  ```

#### 4. 手工验证要点
- 路由与基本加载：各页面 200/302；无明显 JS 报错。
- 搜索与过滤：关键词、类型与难度筛选生效；分页正常。
- 登录与注册：表单校验与错误提示清晰；登录后状态持久。
- 定时模式：倒计时可见；提交后提示与结果展示合理。
- 响应式：移动端菜单与布局无遮挡或错位；闪消息可见且可关闭。

#### 5. 验收标准
- 页面响应正常（200/302），接口联动无明显异常；
- 关键交互（搜索、筛选、定时提交、登录注册）可用；
- 错误时提示清晰；移动端布局无明显问题。