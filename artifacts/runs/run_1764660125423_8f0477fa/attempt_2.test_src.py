import tempfile
import os
from pathlib import Path
from django.test import SimpleTestCase
from django.http import Http404, HttpResponseNotFound, HttpResponse
from django.views.debug import technical_404_response, default_urlconf

class DebugViewsTest(SimpleTestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_technical_404_response_with_existing_directory(self):
        dir_path = self.base_path / 'test_dir'
        dir_path.mkdir()
        response = technical_404_response(self.create_mock_request('/test_dir/'), Http404("Not Found"))
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'404', response.content)
        self.assertIn(b'Not Found', response.content)
        self.assertIn(b'test_dir', response.content)  # Additional assertion for directory name

    def test_technical_404_response_with_non_existing_file(self):
        response = technical_404_response(self.create_mock_request('/non_existing_file/'), Http404("Not Found"))
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'404', response.content)
        self.assertIn(b'Not Found', response.content)
        self.assertNotIn(b'Existing file', response.content)  # Ensure it does not mention existing files

    def test_technical_404_response_with_existing_file(self):
        file_path = self.base_path / 'test_file.txt'
        file_path.write_text('This is a test file.')
        response = technical_404_response(self.create_mock_request('/test_file.txt'), Http404("Not Found"))
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'404', response.content)
        self.assertIn(b'This is a test file.', response.content)
        self.assertIn(b'test_file.txt', response.content)  # Additional assertion for file name

    def test_default_urlconf_response(self):
        response = default_urlconf(self.create_mock_request('/'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Documentation version', response.content)
        self.assertIn(b'Python', response.content)  # Additional assertion for content

    def test_technical_404_response_with_empty_path(self):
        response = technical_404_response(self.create_mock_request(''), Http404("Not Found"))
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'404', response.content)
        self.assertIn(b'Not Found', response.content)  # Ensure it mentions the error

    def test_technical_404_response_with_invalid_key_access(self):
        with self.assertRaises(KeyError):
            technical_404_response(self.create_mock_request('/invalid_key/'), Http404("Not Found"))

    def create_mock_request(self, path):
        from django.http import HttpRequest
        request = HttpRequest()
        request.path = path
        request.method = 'GET'
        return request

    def test_technical_404_response_with_large_input(self):
        large_input = 'x' * 10000  # Simulating a large path
        response = technical_404_response(self.create_mock_request(f'/{large_input}/'), Http404("Not Found"))
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'404', response.content)
        self.assertIn(b'Not Found', response.content)  # Ensure it mentions the error

    def test_technical_404_response_with_special_characters(self):
        special_path = '/test_file_@#$%^&*()_+/'
        response = technical_404_response(self.create_mock_request(special_path), Http404("Not Found"))
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'404', response.content)
        self.assertIn(b'Not Found', response.content)

    def test_technical_404_response_with_unicode_path(self):
        unicode_path = '/test_file_ñáé/'
        response = technical_404_response(self.create_mock_request(unicode_path), Http404("Not Found"))
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'404', response.content)
        self.assertIn(b'Not Found', response.content)

    def test_technical_404_response_with_large_error_message(self):
        large_error_message = 'x' * 1000  # Simulating a large error message
        response = technical_404_response(self.create_mock_request('/large_error/'), Http404(large_error_message))
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'404', response.content)
        self.assertIn(large_error_message.encode(), response.content)  # Check for large error message

    def test_technical_404_response_with_different_http_methods(self):
        methods = ['POST', 'PUT', 'DELETE']
        for method in methods:
            request = self.create_mock_request('/test_file.txt')
            request.method = method
            response = technical_404_response(request, Http404("Not Found"))
            self.assertEqual(response.status_code, 404)
            self.assertIn(b'404', response.content)
            self.assertIn(b'Not Found', response.content)  # Ensure it mentions the error