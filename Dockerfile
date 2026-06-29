FROM python:3.11-slim

# 安装中文字体支持 + 编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-wqy-zenhei \
    fonts-noto-cjk \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# matplotlib 非交互后端 + UTF-8 编码
ENV MPLBACKEND=Agg
ENV PYTHONIOENCODING=utf-8

WORKDIR /app

# 先复制依赖文件，充分利用 Docker 层缓存
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# 复制入口脚本（需要在 COPY . 之前单独复制，确保权限正确）
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 复制项目代码（排除规则由 .dockerignore 控制）
COPY . .

# 预构建 matplotlib 字体缓存，避免运行时报错
RUN python -c "import matplotlib; matplotlib.font_manager._load_fontmanager(try_read_cache=False)"

# 默认执行入口脚本
CMD ["/entrypoint.sh"]
