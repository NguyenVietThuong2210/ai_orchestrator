"""Views for the hello app."""

from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def hello_world(request: HttpRequest) -> HttpResponse:
    """Return 'Hello, World!' with HTTP 200 for GET requests.

    Any other HTTP method (POST, PUT, DELETE, PATCH, …) is rejected
    with 405 Method Not Allowed by the @require_http_methods decorator.
    """
    return HttpResponse("Hello, World!")
