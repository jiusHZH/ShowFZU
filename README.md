# ShowFZU

ShowFZU 是一个面向福州大学校园展示与社区互动的网站项目。网站界面和默认演示内容按产品需求使用英文，功能包括 Official FZU Introduction 静态展示页、公开帖子浏览与搜索、分类浏览、自建账号注册和登录、点赞、收藏、评论以及个人资料管理。

## 技术栈

- 前端：React、Vite、TypeScript、React Router
- 后端：Python 3.12+、FastAPI、SQLAlchemy、Alembic
- 生产数据库和媒体存储：Supabase Postgres、Supabase Storage
- 认证：由 FastAPI 自建 HTTP-only cookie session，session 有效期为 7 天；不使用 Supabase Auth

仓库为 monorepo：

```text
ShowFZU/
  frontend/     React application
  backend/      FastAPI application and migrations
  docs/         product and architecture requirements
  resource/     source documents, photos, and videos
  scripts/      static asset and demo content generation scripts
```

产品与架构规则以 `docs/requirements.md` 和 `docs/architecture.md` 为准。

## 本地运行所需环境

常规本地开发必须准备：

- Windows PowerShell 或命令提示符
- Node.js 与 `npm`
- Python 3.12 或更高版本

下列内容不是通过 `pip` 或 `npm` 就能完整解决的依赖，需要按功能手动准备：

- 系统命令 `ffmpeg` 与 `ffprobe`：视频缩略图处理、从 `resource/` 生成演示视频帖子时需要。安装后需确保它们在系统 `PATH` 中可执行。
- Supabase 项目凭据：真实图片、视频和头像上传由后端写入 Supabase Storage，因此需要手工配置密钥。本仓库不提供密钥，也不得提交密钥。
- `resource/` 下的原始 Word 文档与媒体：仅在重新生成官方展示素材或演示帖子媒体时需要。

Python 依赖清单采用标准文件名 `requirements.txt`，可直接供 `pip` 使用。

## 第一次本地安装

在 Windows 中操作：

1. 按 `Win + R`，输入 `cmd`，回车。
2. 进入项目根目录。请在资源管理器中找到项目实际位置，并替换下面的示例路径：

   ```bat
   cd C:\<project-parent-directory>\ShowFZU
   ```

3. 安装前端依赖：

   ```bat
   npm install
   ```

4. 如果本机还没有可用的 `backend\.venv`，创建后端 Python 虚拟环境并安装依赖：

   ```bat
   py -3.12 -m venv backend\.venv
   backend\.venv\Scripts\python.exe -m pip install --upgrade pip
   backend\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

5. 创建本地后端配置文件：

   ```bat
   copy backend\.env.example backend\.env
   ```

默认开发配置使用本地 SQLite 数据库，足以启动网站、浏览页面和进行基础账号/帖子数据测试。生产环境不得使用示例中的占位 session secret。

## 如何在本地启动

第一个终端启动后端：

1. 按 `Win + R`，输入 `cmd`，回车。
2. 进入项目根目录：

   ```bat
   cd C:\<project-parent-directory>\ShowFZU
   ```

3. 启动 FastAPI 后端：

   ```bat
   cd backend
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

第二个终端启动前端：

4. 再打开一个命令提示符窗口，并再次进入项目根目录：

   ```bat
   cd C:\<project-parent-directory>\ShowFZU
   ```

5. 启动 Vite 前端：

   ```bat
   npm --workspace frontend run dev -- --host 127.0.0.1 --port 5173
   ```

6. 在浏览器中访问：

   ```text
   http://127.0.0.1:5173/
   ```

后端健康检查地址：

```text
http://127.0.0.1:8000/api/health
```

## 初始化演示内容

仓库包含脚本，可根据提供的素材文档和媒体文件生成英文演示帖子及官方展示页素材。

如需向本地 SQLite 数据库写入演示账号和帖子，在项目根目录运行：

```bat
cd C:\<project-parent-directory>\ShowFZU
npm run seed:demo
```

演示种子流程会处理 `resource/` 中的视频，因此运行该命令前必须自行安装 `ffmpeg` 与 `ffprobe` 并加入 `PATH`。

如需重新生成 Official FZU Introduction 静态素材：

```bat
cd C:\<project-parent-directory>\ShowFZU
backend\.venv\Scripts\python.exe scripts\build_official_guide.py
```

## 媒体上传与 Supabase 配置

本地 SQLite 模式足以启动应用并浏览静态或演示媒体。真实用户上传的媒体必须经过 `frontend -> FastAPI -> Supabase Storage` 链路，不允许前端直接写入 Supabase。

如需启用真实上传，请手工配置 `backend\.env`：

```env
SHOWFZU_SUPABASE_URL=https://epkgspfhfwlsxsesteof.supabase.co
SHOWFZU_SUPABASE_SERVICE_KEY=<your-service-role-key>
SHOWFZU_STORAGE_POSTS_BUCKET=post-media
SHOWFZU_STORAGE_AVATARS_BUCKET=avatars
SHOWFZU_STORAGE_GUIDE_BUCKET=official-guide
```

注意事项：

- 不得提交 `backend\.env`、Supabase service role key、数据库密码或 session secret。
- 使用上传功能前，需要在关联的 Supabase 项目中准备对应 Storage bucket。
- Storage bucket 面向公开可见媒体，但写入和删除操作只能由后端控制。
- 如部署到 Supabase Postgres，需要通过 `SHOWFZU_DATABASE_URL` 配置数据库连接，并在目标环境执行 Alembic migration。

## 如何停止本地服务

如果前端与后端分别在两个终端窗口中运行，请在每个终端窗口中按 `Ctrl + C`。

如需在 Windows 中查看是否仍有服务占用端口：

```powershell
Get-NetTCPConnection -State Listen -LocalPort 5173,8000 -ErrorAction SilentlyContinue
```

## 校验命令

在项目根目录执行：

```bat
npm run lint:frontend
npm run build:frontend
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```
