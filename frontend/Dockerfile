# 基础镜像可由隔离 UAT 指向测试机缓存，正式构建继续使用默认版本。
ARG NODE_BASE_IMAGE=node:22-alpine
ARG NGINX_BASE_IMAGE=nginx:stable-alpine
FROM ${NODE_BASE_IMAGE} AS build
WORKDIR /app

# SSO开关和门户URL是公开构建配置，不允许把Token或密钥作为build arg。
ARG VITE_SSO_ENABLED=false
ARG VITE_MOLING_PORTAL_URL=
ENV VITE_SSO_ENABLED=${VITE_SSO_ENABLED} \
    VITE_MOLING_PORTAL_URL=${VITE_MOLING_PORTAL_URL}

COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM ${NGINX_BASE_IMAGE}
WORKDIR /usr/share/nginx/html
RUN rm -rf ./* && mkdir -p /etc/nginx/snippets
COPY --from=build /app/dist ./
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY nginx-security-headers.conf /etc/nginx/snippets/trainppt-security-headers.conf

# 只替换部署变量，保留$host、$uri等Nginx运行时变量。
ENV SERVER_NAME=ppt.axicomin.cn \
    MAIN_API_UPSTREAM=main_api:6800 \
    TRUSTED_PROXY_IP=172.29.23.1 \
    NGINX_ENVSUBST_FILTER="^(SERVER_NAME|MAIN_API_UPSTREAM|TRUSTED_PROXY_IP)$"

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
