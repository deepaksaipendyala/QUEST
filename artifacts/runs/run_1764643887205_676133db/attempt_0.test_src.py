import mimetypes
import tempfile
from pathlib import Path
from django.http import Http404, HttpResponseNotModified
from django.test import SimpleTestCase
from django.utils.http import http_date
from django.utils.translation import gettext as _

from django.views.static import serve, directory_index, was_modified_since

class StaticFileServeTests(SimpleTestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.document_root = Path(self.temp_dir.name)
        self.file_path = self.document_root / "test_file.txt"
        self.file_path.write_text("This is a test file.")
        self.directory_path = self.document_root / "test_directory"
        self.directory_path.mkdir()
        self.directory_index_template = self.document_root / "static/directory_index.html"
        self.directory_index_template.write_text("<html><body>Index of {{ directory }}</body></html>")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_serve_valid_file(self):
        response = serve(None, "test_file.txt", document_root=self.document_root)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "This is a test file.")
        self.assertEqual(response.headers["Content-Type"], "text/plain")
        self.assertEqual(response.headers["Last-Modified"], http_date(self.file_path.stat().st_mtime))

    def test_serve_missing_file(self):
        with self.assertRaises(Http404):
            serve(None, "missing_file.txt", document_root=self.document_root)

    def test_serve_directory_with_show_indexes(self):
        response = serve(None, "test_directory", document_root=self.document_root, show_indexes=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Index of test_directory", response.content)

    def test_serve_directory_without_show_indexes(self):
        with self.assertRaises(Http404):
            serve(None, "test_directory", document_root=self.document_root, show_indexes=False)

    def test_serve_if_modified_since(self):
        header = "Wed, 21 Oct 2015 07:28:00 GMT"
        response = serve(None, "test_file.txt", document_root=self.document_root)
        self.assertEqual(response.status_code, 200)

        # Simulate If-Modified-Since header
        self.file_path.touch()  # Update the file's modification time
        response = serve({"META": {"HTTP_IF_MODIFIED_SINCE": header}}, "test_file.txt", document_root=self.document_root)
        self.assertIsInstance(response, HttpResponseNotModified)

    def test_directory_index(self):
        response = directory_index("test_directory", self.directory_path)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Index of test_directory", response.content)

    def test_directory_index_template_not_exist(self):
        self.directory_index_template.unlink()  # Remove the template to trigger fallback
        response = directory_index("test_directory", self.directory_path)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Index of test_directory", response.content)

    def test_was_modified_since(self):
        self.assertTrue(was_modified_since(None, 0, 0))
        self.assertTrue(was_modified_since("Wed, 21 Oct 2015 07:28:00 GMT", 0, 0))
        self.assertFalse(was_modified_since("Wed, 21 Oct 2015 07:28:00 GMT", 1, 0))
        self.assertRaises(ValueError, was_modified_since, "invalid_header", 0, 0)