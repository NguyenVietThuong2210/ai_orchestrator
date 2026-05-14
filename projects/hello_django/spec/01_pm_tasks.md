        # PM Task Breakdown

        | ID | Title | Priority | Status | Description |
        |----|-------|----------|--------|-------------|
        | T1 | Initialize Django project scaffold and configure settings | P1 | pending | Create projects/hello_django/ directory with manage.py, hello_django/ package (settings.py, urls.py, wsgi.py, asgi.py, __init__.py). Configure INSTALLED_APPS, DATABASES (SQLite), MIDDLEWARE. Create root urls.py. |
| T2 | Create Django app 'hello' and register it | P1 | pending | Create hello/ app directory with standard structure (__init__.py, views.py, urls.py, apps.py, models.py, tests.py, migrations/__init__.py). Add 'hello' to INSTALLED_APPS. |
| T3 | Implement 'Hello, World!' view | P1 | pending | Write hello/views.py with a view function that takes HttpRequest and returns HttpResponse('Hello, World!'). |
| T4 | Configure URL routing for root path | P1 | pending | Create hello/urls.py mapping root path '' to the hello view. Update root urls.py to include hello.urls with path(). |
| T5 | Create requirements.txt with dependencies | P1 | pending | Create requirements.txt in projects/hello_django/ listing Django>=4.2. |
| T6 | Document setup and run instructions | P2 | pending | Create README.md with installation steps (pip install -r requirements.txt), run command (python manage.py runserver), and access URL (http://localhost:8000/). |
