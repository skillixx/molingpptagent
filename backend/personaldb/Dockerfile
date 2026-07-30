# 基础镜像允许隔离 UAT 使用测试机已缓存版本，默认仍保持 Python 3.12。
ARG PYTHON_BASE_IMAGE=python:3.12
FROM ${PYTHON_BASE_IMAGE}

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 LC_ALL=C.UTF-8 LANG=C.UTF-8

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

# Copy the rest of the application's code into the container at /app
COPY . .

# Expose port 9100 to the outside world
EXPOSE 9100

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9100"]
