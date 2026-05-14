"""Tests for the hello app."""

from django.test import TestCase


class HelloWorldViewTests(TestCase):
    """Tests for the hello_world view at /."""

    def test_get_returns_200(self):
        """GET / responds with HTTP 200 OK."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_get_returns_hello_world(self):
        """GET / responds with the exact body 'Hello, World!'."""
        response = self.client.get("/")
        self.assertEqual(response.content, b"Hello, World!")

    def test_post_returns_405(self):
        """POST / responds with HTTP 405 Method Not Allowed."""
        response = self.client.post("/")
        self.assertEqual(response.status_code, 405)

    def test_put_returns_405(self):
        """PUT / responds with HTTP 405 Method Not Allowed."""
        response = self.client.put("/")
        self.assertEqual(response.status_code, 405)

    def test_delete_returns_405(self):
        """DELETE / responds with HTTP 405 Method Not Allowed."""
        response = self.client.delete("/")
        self.assertEqual(response.status_code, 405)
