FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# 本镜像从仓库根目录构建，保留backend.main_api包布局供API和Worker共同复用。
WORKDIR /app
COPY backend/main_api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
COPY backend /app/backend
COPY alembic.ini /app/alembic.ini

WORKDIR /app/backend/main_api
EXPOSE 6800
# /enter含一次性ticket，Uvicorn请求行日志必须关闭；安全审计由应用结构化日志提供。
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6800", "--no-access-log"]
