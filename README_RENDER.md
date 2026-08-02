Render deployment notes

This branch adds Render-friendly deployment configuration (Dockerfile + render.yaml) and a .dockerignore.

How to deploy on Render:
1. Push (merge) this branch to your main branch on GitHub.
2. Go to https://render.com and create a new Web Service.
   - Connect your GitHub account and select this repository.
   - Render will detect render.yaml and/or the Dockerfile. If asked, choose Docker (the Dockerfile at repo root).
3. Environment variables (set in Render dashboard for the service):
   - SECRET_KEY: a long random secret for Flask sessions (required in production)
   - ADMIN_USER (optional): default is "vernex"
   - ADMIN_PASS (optional): default is "vernex@16vx"
   - DATA_DB (optional): path to an external DB if you don't want SQLite in the container. Default uses local data.db inside the container (not persistent across deploys).
4. Render will build the Docker image and run the container. The app listens on the $PORT provided by Render.

Local testing (Docker):
  docker build -t ft-gateway .
  docker run --rm -e PORT=8080 -p 8080:8080 ft-gateway
  curl http://127.0.0.1:8080/health

Notes:
- SQLite is used by default and stored in data.db inside the container. For production, use an external DB (Postgres) and change the app to use it or mount a volume.
- Change SECRET_KEY in Render environment variables before going public.
