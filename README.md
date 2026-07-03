# ShowFZU

ShowFZU is an English-language campus showcase and community website for Fuzhou University. It includes a static Official FZU Introduction exhibition, public post browsing and search, category feeds, custom account registration and login, likes, favorites, comments, and profile management.

## Technology Stack

- Frontend: React, Vite, TypeScript, and React Router
- Backend: Python 3.12+, FastAPI, SQLAlchemy, and Alembic
- Production database and media storage: Supabase Postgres and Supabase Storage
- Authentication: a custom FastAPI HTTP-only cookie session with a seven-day lifetime; Supabase Auth is not used

This repository is a monorepo:

```text
ShowFZU/
  frontend/     React application
  backend/      FastAPI application and migrations
  docs/         product and architecture requirements
  resource/     optional local source documents and media (not included)
  scripts/      static asset and demo content generation scripts
```

`docs/requirements.md` and `docs/architecture.md` are the sources of truth for product and architecture decisions.

## Local Development Requirements

Standard local development requires:

- Windows PowerShell or Command Prompt
- Node.js and `npm`
- Python 3.12 or later

The following dependencies require additional setup:

- `ffmpeg` and `ffprobe`: required for video thumbnail generation and for generating demo video posts from `resource/`. Both commands must be available on the system `PATH`.
- Supabase project credentials: the backend uploads real images, videos, and avatars to Supabase Storage. Credentials must be configured locally and must never be committed.
- Source Word documents and media under `resource/`: optional local inputs required only when regenerating official showcase assets or demo post media. They are excluded from the source submission because of their size.

Python dependencies are listed in the standard root-level `requirements.txt` file.

## First-Time Local Setup

On Windows:

1. Press `Win + R`, enter `cmd`, and press Enter.
2. Open the project root. Replace the example path with the actual location:

   ```bat
   cd C:\<project-parent-directory>\ShowFZU
   ```

3. Install frontend dependencies:

   ```bat
   npm install
   ```

4. If `backend\.venv` does not exist, create the backend virtual environment and install its dependencies:

   ```bat
   py -3.12 -m venv backend\.venv
   backend\.venv\Scripts\python.exe -m pip install --upgrade pip
   backend\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

5. Create the local backend configuration:

   ```bat
   copy backend\.env.example backend\.env
   ```

The default development configuration uses a local SQLite database. It is sufficient for starting the website, browsing pages, and testing basic account and post flows. Never use the placeholder session secret in production.

## Starting the Application Locally

Start the backend in the first terminal:

1. Press `Win + R`, enter `cmd`, and press Enter.
2. Open the project root:

   ```bat
   cd C:\<project-parent-directory>\ShowFZU
   ```

3. Start the FastAPI backend:

   ```bat
   cd backend
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

Start the frontend in a second terminal:

4. Open another Command Prompt window and return to the project root:

   ```bat
   cd C:\<project-parent-directory>\ShowFZU
   ```

5. Start the Vite frontend:

   ```bat
   npm --workspace frontend run dev -- --host 127.0.0.1 --port 5173
   ```

6. Open the application:

   ```text
   http://127.0.0.1:5173/
   ```

Backend health check:

```text
http://127.0.0.1:8000/api/health
```

## Initializing Demo Content

The repository includes scripts that generate English demo posts and official showcase assets when the optional source documents and media are available under `resource/`.

To seed demo accounts and posts into the local SQLite database, run this command from the project root:

```bat
cd C:\<project-parent-directory>\ShowFZU
npm run seed:demo
```

The demo seed process handles videos from `resource/`, so `ffmpeg` and `ffprobe` must be installed and available on `PATH`.

To regenerate static assets for the Official FZU Introduction:

```bat
cd C:\<project-parent-directory>\ShowFZU
backend\.venv\Scripts\python.exe scripts\build_official_guide.py
```

## Media Uploads and Supabase

Local SQLite mode is sufficient for starting the application and browsing static or demo media. Real user media must follow the `frontend -> FastAPI -> Supabase Storage` path. The frontend must never write directly to Supabase.

To enable real uploads, configure `backend\.env` manually:

```env
SHOWFZU_SUPABASE_URL=<your-supabase-project-url>
SHOWFZU_SUPABASE_SERVICE_KEY=<your-backend-only-service-role-or-secret-key>
SHOWFZU_STORAGE_POSTS_BUCKET=post-media
SHOWFZU_STORAGE_AVATARS_BUCKET=avatars
SHOWFZU_STORAGE_GUIDE_BUCKET=official-guide
```

Important:

- Never commit `backend\.env`, a Supabase service role or secret key, a database password, or a session secret.
- Create the required Supabase Storage buckets before testing uploads.
- Storage buckets provide public read access to media, while all writes and deletions remain backend-only.
- A Supabase Postgres deployment requires `SHOWFZU_DATABASE_URL` and the latest Alembic migration on the target database.

## Stopping Local Services

If the frontend and backend are running in separate terminal windows, press `Ctrl + C` in each window.

To check whether either local port is still in use on Windows:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 5173,8000 -ErrorAction SilentlyContinue
```

## Validation

Run these commands from the project root:

```bat
npm run lint:frontend
npm run build:frontend
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```
