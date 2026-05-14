# Hello Django

A minimal Django "Hello, World!" web application.

## Installation

It is recommended to use a Python virtual environment:

```bash
python -m venv .venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the development server

```bash
python manage.py runserver
```

Then open your browser at: http://localhost:8000/

If port 8000 is already in use, specify a different port:

```bash
python manage.py runserver 8080
```

## Notes

- `DEBUG=True` is set for local development only. Set `DEBUG=False` for any production or public-facing deployment.
- `ALLOWED_HOSTS = ['*']` is set for local convenience. Restrict this to explicit hostnames before deploying.
- The `SECRET_KEY` in `settings.py` is for development only. Load it from an environment variable for any real deployment.
