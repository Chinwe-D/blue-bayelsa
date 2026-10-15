# Blue Bayelsa Invest

A web and Android platform for discovering blue-economy activities, enterprises, infrastructure gaps and investment opportunities across 24 survey communities in the eight Local Government Areas of Bayelsa State, Nigeria.

## Status

| Phase | State |
|---|---|
| 1. Requirements analysis | Done |
| 2. System architecture | Done |
| Foundation (backend skeleton) | **Done**: see below |
| Bulk upload engine | **Done** (backend); admin screens come next |
| 3. Data model | Waiting for the field questionnaire and the definition of the eight sectors |
| 4–11 | Not started |

### What the foundation includes

- **Reference data** from the project documents: 8 LGAs, 24 survey communities and 15 blue-economy activities. No GPS coordinates or sectors are invented; those fields stay empty until real data is supplied.
- **Roles**: Data entry officer, Reviewer and Administrator, plus a technical super-administrator. Permissions are enforced on the server.
- **Publication workflow** shared by every future data record: Draft → Submitted → Approved, with Return and Reject (a reason is required) and Archive (administrators only). Maker-checker is on by default, so nobody can approve their own record.
- **Data governance**: data sources, provenance fields, approval records, full version history of reference data, and an append-only audit log covering logins, failed logins, edits and workflow actions.
- **GPS validation**: points outside Bayelsa are rejected, and swapped latitude/longitude is detected.
- **API**: separate `/api/v1/public/` (published data only) and `/api/v1/admin/` (staff, role-checked) areas, plus `/api/v1/auth/`. OpenAPI docs are at `/api/v1/docs/` in development only.
- **Security**: Argon2 passwords, HttpOnly session cookies, CSRF protection including on login, a login rate limit, no hard deletion of reference data, and secrets only in environment variables.
- **Bulk upload engine** (`apps/imports`): Excel templates generated from the database (dropdown lists, red required headings, instructions sheet, pre-filled rows), safe reading of `.xlsx`/`.csv` (checks real file contents, size and row limits; formulas never run), row-by-row checks with plain-language messages and "Did you mean…?" suggestions, duplicate detection within the file, correcting or skipping individual rows, and import only after explicit confirmation. Every batch is kept for traceability and audited. The first importer is **Community GPS locations**; enterprises, indicators and opportunities plug into the same engine once the questionnaire defines them.
- **Tests**: 52 automated tests (`cd backend && pytest`).
- **Deployment**: Docker Compose with PostGIS, the Django API (Gunicorn) and Nginx.

## Run it with Docker

```bash
cp .env.example .env        # then edit every value
docker compose up -d --build
docker compose exec api python manage.py createsuperuser
```

The API is then available at `http://<server>/api/v1/public/lgas/`.

## Develop locally

Requirements: Python 3.12+, PostgreSQL 16 with PostGIS 3, GDAL.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
cd backend
# create backend/.env with SECRET_KEY, DEBUG=True, ALLOWED_HOSTS, DATABASE_URL=postgis://user:pass@localhost:5432/bluebayelsa
python manage.py migrate
python manage.py runserver
pytest
```

## Repository layout

```
backend/
  config/            settings (all from environment variables), URLs
  apps/accounts/     users, roles and capabilities, login/logout
  apps/audit/        append-only audit log
  apps/governance/   data sources, GovernedModel base class, publication workflow, GPS validation
  apps/geo/          LGAs, communities, sectors, activities (+ public and admin API)
  apps/imports/      bulk upload: templates, file reading, row checks, corrections, import
  apps/api/          URL routing for public / admin / auth
  tests/             automated tests
deploy/nginx/        Nginx configuration
docker-compose.yml
```

## Information still needed from the research team

1. The field questionnaire, which defines the indicators and enterprise variables.
2. The "eight blue-economy sectors" and which of the 15 activities belong to each.
3. GPS coordinates for the 24 communities.
4. A decision on publishing enterprise contact details (consent).
