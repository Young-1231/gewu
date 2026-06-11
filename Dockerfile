FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 先装依赖层（缓存友好），再装项目本体
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev

# 数据缓存放容器卷，密钥经环境变量注入（不要把 .env 打进镜像）
ENV GEWU_CACHE_DIR=/data/cache
VOLUME ["/data"]

ENTRYPOINT ["uv", "run", "gewu"]
CMD ["--help"]
