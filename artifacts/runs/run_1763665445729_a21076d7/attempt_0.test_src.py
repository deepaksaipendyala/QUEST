import mimetypes
import tempfile
import unittest
from pathlib import Path
from django.http import Http404, HttpResponseNotModified, FileResponse
from django.views.static import serve, directory_index, was_modified_since

class StaticFileServeTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.document_root = Path(self.temp_dir.name)
        self.file_path = self.document_root / "test_file.txt"
        self.file_path.write_text("This is a test file.")
        self.directory_path = self.document_root / "test_dir"
        self.directory_path.mkdir()
        self.index_file_path = self.directory_path / "index.html"
        self.index_file_path.write_text("This is an index file.")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_serve_valid_file(self):
        response = serve(None, "test_file.txt", document_root=self.document_root)
        self.assertIsInstance(response, FileResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "This is a test file.")
        self.assertIn("Last-Modified", response.headers)

    def test_serve_missing_file(self):
        with self.assertRaises(Http404):
            serve(None, "missing_file.txt", document_root=self.document_root)

    def test_serve_directory_with_show_indexes(self):
        response = serve(None, "test_dir", document_root=self.document_root, show_indexes=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("<h1>Index of test_dir</h1>", response.content.decode())

    def test_serve_directory_without_show_indexes(self):
        with self.assertRaises(Http404):
            serve(None, "test_dir", document_root=self.document_root, show_indexes=False)

    def test_serve_directory_index_template(self):
        response = directory_index("test_dir", self.directory_path)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Index of test_dir", response.content.decode())
        self.assertIn("index.html", response.content.decode())

    def test_serve_directory_index_template_no_template(self):
        response = directory_index("nonexistent_dir", Path(self.document_root / "nonexistent_dir"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Index of nonexistent_dir", response.content.decode())

    def test_was_modified_since(self):
        header = "Wed, 21 Oct 2015 07:28:00 GMT; length=20"
        mtime = self.file_path.stat().st_mtime
        size = self.file_path.stat().st_size
        self.assertFalse(was_modified_since(header, mtime, size))

    def test_was_modified_since_not_modified(self):
        header = "Wed, 21 Oct 2015 07:28:00 GMT; length=20"
        mtime = self.file_path.stat().st_mtime + 1000  # Simulate a newer file
        size = self.file_path.stat().st_size
        self.assertTrue(was_modified_since(header, mtime, size))

    def test_was_modified_since_invalid_header(self):
        self.assertTrue(was_modified_since("invalid_header", 0, 0))

    def test_was_modified_since_no_header(self):
        self.assertTrue(was_modified_since(None, 0, 0))