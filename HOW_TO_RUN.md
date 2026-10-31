# How to run Brightloop Subscriptions

**One command starts everything.** The database, the backend (FastAPI) and the frontend (React) each run in their own Docker container, and `docker compose up` starts all three together. You don't run `npm run dev`, `uvicorn` or Postgres yourself, and you don't need Python, Node or Postgres installed.

## Prerequisite

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (on Windows, use the WSL 2 backend). Make sure it's running before you use any of the commands below.

## 1. Get the code (first time only)

```bash
git clone <repo-url> brightloop
cd brightloop
```

## 2. Start the frontend, backend and database

From the repo root:

```bash
docker compose up --build
```

- The first run downloads images and installs dependencies, which takes a few minutes. Later starts take seconds.
- `--build` rebuilds the images when dependencies have changed, and is quick when nothing has.
- The logs from all three services stream in this terminal. Leave it open while you work.

## 3. Open the app

| URL | What it is |
|---|---|
| http://localhost:5173 | Frontend (the web app) |
| http://localhost:8000/api/docs | Backend API docs (also at http://localhost:5173/api/docs) |
| http://localhost:8000/api/health | Backend health check |
| `localhost:5433` | Postgres, for a database GUI. User, password and database are all `brightloop` |

## 4. Stop it

Press `Ctrl+C` in the terminal that's running `docker compose up`, or use one of these:

| Command | What it does |
|---|---|
| `docker compose down` | Stops everything and keeps your database data |
| `docker compose down -v` | Stops everything and permanently deletes the data in your local database |

### What `docker compose down -v` deletes

It erases only the data in **your own local database**:

- **Deleted for good:** every table and row in it, such as the users, subscriptions and invoices you created while testing, plus the separate test database.
- **Not touched:** your code, your git history, the Docker images, your teammates' databases, and any Postgres installed directly on your machine.

On the next start, the API recreates the tables from the migrations and creates the demo accounts again automatically. You only lose records you entered by hand. To keep your data, stop with plain `docker compose down`.

## Running in the background

To keep your terminal free, start with `-d` and read the logs when you need them:

```bash
docker compose up -d --build   # start in the background
docker compose ps              # see what's running
docker compose logs -f api     # follow the backend logs (Ctrl+C stops following, not the app)
docker compose logs -f web     # follow the frontend logs
docker compose down            # stop everything
```

## Restarting one part

| Task | Command |
|---|---|
| Restart only the backend | `docker compose restart api` |
| Restart only the frontend | `docker compose restart web` |

## When your changes show up

- Edits in `backend/app` and `frontend/src` reload automatically, so you don't need to restart anything.
- After you change `requirements*.txt`, `package.json`, `vite.config.ts` or a Dockerfile, stop the stack and run `docker compose up --build` again.

## If something goes wrong

See [Troubleshooting in the README](README.md#troubleshooting) for port conflicts, migration errors and other common problems.
