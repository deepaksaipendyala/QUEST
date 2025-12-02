import tempfile
import unittest
from unittest.mock import Mock
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
        request = Mock()
        response = serve(request, "test_file.txt", document_root=self.document_root)
        self.assertIsInstance(response, FileResponse)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertEqual(response['Last-Modified'], self.file_path.stat().st_mtime)

    def test_serve_missing_file(self):
        request = Mock()
        with self.assertRaises(Http404):
            serve(request, "missing_file.txt", document_root=self.document_root)

    def test_serve_directory_with_show_indexes(self):
        request = Mock()
        response = serve(request, "test_dir", document_root=self.document_root, show_indexes=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Index of test_dir', response.content)

    def test_serve_directory_without_show_indexes(self):
        request = Mock()
        with self.assertRaises(Http404):
            serve(request, "test_dir", document_root=self.document_root, show_indexes=False)

    def test_serve_if_modified_since(self):
        request = Mock()
        request.META = {
            "HTTP_IF_MODIFIED_SINCE": "Wed, 21 Oct 2015 07:28:00 GMT"
        }
        response = serve(request, "test_file.txt", document_root=self.document_root)
        self.assertIsInstance(response, FileResponse)

        # Modify the file to test If-Modified-Since
        self.file_path.write_text("This is an updated test file.")
        response = serve(request, "test_file.txt", document_root=self.document_root)
        self.assertIsInstance(response, FileResponse)

    def test_directory_index(self):
        response = directory_index("test_dir", self.directory_path)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Index of test_dir', response.content)
        self.assertIn(b'index.html', response.content)

    def test_was_modified_since_true(self):
        self.assertTrue(was_modified_since(None, 0, 0))

    def test_was_modified_since_invalid_header(self):
        self.assertTrue(was_modified_since("invalid_header", 0, 0))

    def test_was_modified_since_valid(self):
        header = "Wed, 21 Oct 2015 07:28:00 GMT"
        mtime = self.file_path.stat().st_mtime
        self.assertFalse(was_modified_since(header, mtime, self.file_path.stat().st_size))

    def test_was_modified_since_size_mismatch(self):
        header = "Wed, 21 Oct 2015 07:28:00 GMT; length=100"
        mtime = self.file_path.stat().st_mtime
        self.assertTrue(was_modified_since(header, mtime, self.file_path.stat().st_size))


if __name__ == "__main__":
    unittest.main()