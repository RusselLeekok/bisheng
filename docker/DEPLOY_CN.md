# Bisheng Docker Compose 构建与部署

下面的命令默认在项目根目录执行，也就是 `c:\Users\sz966\bisheng`。

## 1. 本地构建前后端镜像

先准备镜像名。建议使用带日期或提交号的标签，后续服务器可以精确运行同一个版本。

```powershell
Copy-Item docker\.env.example docker\.env
notepad docker\.env
```

把 `docker\.env` 中的镜像名改成你的镜像仓库地址，例如：

```dotenv
BISHENG_BACKEND_IMAGE=registry.example.com/bisheng-backend:20260421
BISHENG_FRONTEND_IMAGE=registry.example.com/bisheng-frontend:20260421
DOCKER_VOLUME_DIRECTORY=.
```

构建镜像：

```powershell
docker compose --env-file docker\.env `
  -f docker\docker-compose.yml `
  -f docker\docker-compose.local-build.yml `
  -p bisheng build backend frontend
```

本地试运行整套服务：

```powershell
docker compose --env-file docker\.env `
  -f docker\docker-compose.yml `
  -f docker\docker-compose.local-build.yml `
  -p bisheng up -d

docker compose --env-file docker\.env `
  -f docker\docker-compose.yml `
  -f docker\docker-compose.local-build.yml `
  -p bisheng ps
```

浏览器访问 `http://localhost:3001`。

## 2. 上传镜像到服务器

推荐方式是推送到镜像仓库：

```powershell
docker login registry.example.com
docker push registry.example.com/bisheng-backend:20260421
docker push registry.example.com/bisheng-frontend:20260421
```

如果服务器不能访问镜像仓库，可以把镜像打包上传：

```powershell
# 如果你没有镜像仓库，也可以把 docker\.env 里的镜像名改成本地标签：
# BISHENG_BACKEND_IMAGE=bisheng-backend:local
# BISHENG_FRONTEND_IMAGE=bisheng-frontend:local

docker save -o bisheng-images.tar `
  bisheng-backend:local `
  bisheng-frontend:local

scp bisheng-images.tar user@server:/opt/bisheng/
ssh user@server "cd /opt/bisheng && docker load -i bisheng-images.tar"
```

如果服务器完全不能访问外网，还需要把 MySQL、Redis、Elasticsearch、Milvus、MinIO、etcd 这些第三方镜像也一起打包：

```powershell
$images = docker compose --env-file docker\.env `
  -f docker\docker-compose.yml `
  -f docker\docker-compose.deploy.yml `
  -p bisheng config --images

docker save -o bisheng-all-images.tar $images
scp bisheng-all-images.tar user@server:/opt/bisheng/
ssh user@server "cd /opt/bisheng && docker load -i bisheng-all-images.tar"
```

## 3. 上传 Compose 配置到服务器

首次部署只需要上传配置目录，不要上传本机已有的 `docker\data` 和 `docker\mysql\data`，否则会把本地运行数据混进服务器。

```powershell
ssh user@server "mkdir -p /opt/bisheng"

scp docker\docker-compose.yml user@server:/opt/bisheng/
scp docker\docker-compose.deploy.yml user@server:/opt/bisheng/
scp docker\.env user@server:/opt/bisheng/.env
scp -r docker\bisheng user@server:/opt/bisheng/
ssh user@server "mkdir -p /opt/bisheng/mysql /opt/bisheng/data"
scp -r docker\mysql\conf user@server:/opt/bisheng/mysql/
scp -r docker\nginx user@server:/opt/bisheng/
scp -r docker\redis user@server:/opt/bisheng/
```

如果你要迁移本地已有数据，应该单独做 MySQL dump、MinIO 数据迁移、Milvus/ES 数据迁移，避免直接复制正在运行的数据库目录。

## 4. 服务器启动

在服务器上执行：

```bash
cd /opt/bisheng
docker compose --env-file .env \
  -f docker-compose.yml \
  -f docker-compose.deploy.yml \
  -p bisheng up -d

docker compose --env-file .env \
  -f docker-compose.yml \
  -f docker-compose.deploy.yml \
  -p bisheng ps
```

访问地址：

```text
http://服务器IP:3001
```

服务器需要至少放行 `3001` 端口。调试期可以临时放行 `7860`、`3307`、`6379`、`9200`、`19530`、`9100`，正式环境建议只开放前端入口或通过 Nginx/网关转发。
