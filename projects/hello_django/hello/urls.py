"""URL configuration for the hello app."""

from django.urls import path

from hello.views import hello_world

app_name = "hello"

urlpatterns = [
    path("", hello_world, name="hello-world"),
]
