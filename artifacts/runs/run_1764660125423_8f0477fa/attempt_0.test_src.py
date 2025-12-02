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

    def test_technical_404_response_with_non_existing_file(self):
        response = technical_404_response(self.create_mock_request('/non_existing_file/'), Http404("Not Found"))
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'404', response.content)

    def test_technical_404_response_with_existing_file(self):
        file_path = self.base_path / 'test_file.txt'
        file_path.write_text('This is a test file.')
        response = technical_404_response(self.create_mock_request('/test_file.txt'), Http404("Not Found"))
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'404', response.content)

    def test_default_urlconf_response(self):
        response = default_urlconf(self.create_mock_request('/'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Documentation version', response.content)

    def create_mock_request(self, path):
        from django.http import HttpRequest
        request = HttpRequest()
        request.path = path
        request.method = 'GET'
        return request