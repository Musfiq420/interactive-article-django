# CMS Backend

Production-ready Django REST Framework backend for an interactive CMS.

## Features

- Article CRUD with nested interactive elements and expandable sections
- Public read access with admin-only writes
- HTML content storage for rich text editors
- Media upload support for image, audio, and video interactives
- YouTube URL validation
- PostgreSQL-ready settings with local SQLite fallback for development

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## API

- `GET /api/articles/`
- `POST /api/articles/`
- `GET /api/articles/{id}/`
- `PATCH /api/articles/{id}/`
- `DELETE /api/articles/{id}/`
- `GET /api/interactives/{key}/`
- `GET /api/sections/`
- `POST /api/sections/`

If the same interactive `key` exists in multiple articles, call
`/api/interactives/{key}/?article=<article-slug>` to disambiguate.
