"""URL configuration for hello_django project."""

from django.urls import include, path

urlpatterns = [
    path("", include("hello.urls")),
]
