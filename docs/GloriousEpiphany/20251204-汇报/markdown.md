# 阶段性评审个人汇报

## 一、个人任务
本阶段我的主要任务集中在以下几个方面：

1.  **中继云服务器的配置与维护**：负责搭建项目的基础运行环境，确保开发与部署的稳定性。
2.  **第二个版本的成果物撰写**
3.  **Docker 容器化部署**：进行下一版本的Docker镜像的制作学习。
4.  **基于PyQt的应用端前端构建**

## 二、前几周学习的知识和成果

### 1. 中继云服务器配置
*   **完成情况**：已完成中继云服务器的基础配置与环境搭建。
    *   **服务连通性验证**：学习了基本的网络排查工具，验证了服务器的公网连通性和端口开放状态，成功部署了上一版本的系统。后续将持续维护服务器状态，并配合团队成员进行新功能的持续集成与部署。

### 2. Docker 部署
* **完成情况**：针对数字人有关部分的部署，学习了基于 `uv` 的容器构建方案。

*   **成果**：

    **（1）Dockerfile 的初步编写**
    
    ```dockerfile
    FROM python:3.11-slim
    
    RUN apt-get update && apt-get install -y \
        ffmpeg \
        libsndfile1 \
        git \
        && rm -rf /var/lib/apt/lists/*
        
    COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
    
    WORKDIR /app
    
    COPY pyproject.toml uv.lock ./
    
    COPY src/third_party ./src/third_party
    
    RUN uv sync --frozen --no-install-project
    
    COPY . .
    
    RUN uv sync --frozen
    
    EXPOSE 8000
    
    CMD ["uv", "run", "src/app.py", "--host", "0.0.0.0", "--port", "8000"]
    ```
    

### 3. 基于PyQt的应用端前端构建
* 进行了应用端前端的基础框架搭建与界面设计。

*   **学习与实践**：
    * **PyQt/PySide 框架**：学习了 Qt 的常用控件（QPushButton, QLabel, QLineEdit 等）及布局管理器（QVBoxLayout, QHBoxLayout, QGridLayout）的使用，实现了界面元素的自适应排列。
    
    * **界面原型开发**：设计并实现了应用端的登录界面与主交互窗口。通过 QSS (Qt Style Sheets) 对界面进行了初步美化。
    
      ![image-20251211085122130](C:\Users\29643\AppData\Roaming\Typora\typora-user-images\image-20251211085122130.png)


## 三、后续的任务

1.  **持续维护云服务器**：监控服务器资源使用情况，确保演示期间的稳定性。
2.  **跟进 Docker 部署优化**：待跨域问题修复代码合并后，重新构建镜像并验证部署，确保前后端服务通信正常。
3.  **应用端前端界面的构建与优化**：继续推进应用端前端界面构建。