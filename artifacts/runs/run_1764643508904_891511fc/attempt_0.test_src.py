import tempfile
import unittest
from unittest.mock import Mock
from django.http import Http404, HttpResponseNotModified, FileResponse
from django.views.static import serve, directory_index, was_modified_since
from pathlib import Path
import time

class StaticFileServeTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.document_root = Path(self.temp_dir.name)
        self.file_path = self.document_root / "testfile.txt"
        self.file_path.write_text("This is a test file.")
        self.directory_path = self.document_root / "testdir"
        self.directory_path.mkdir()
        self.directory_file_path = self.directory_path / "index.html"
        self.directory_file_path.write_text("<html>Index</html>")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_serve_valid_file(self):
        request = Mock(META={})
        response = serve(request, "testfile.txt", document_root=self.document_root)
        self.assertIsInstance(response, FileResponse)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertEqual(response['Last-Modified'], time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(self.file_path.stat().st_mtime)))

    def test_serve_missing_file(self):
        request = Mock(META={})
        with self.assertRaises(Http404):
            serve(request, "missingfile.txt", document_root=self.document_root)

    def test_serve_directory_with_show_indexes(self):
        request = Mock(META={})
        response = serve(request, "testdir", document_root=self.document_root, show_indexes=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Index of testdir', response.content)

    def test_serve_directory_without_show_indexes(self):
        request = Mock(META={})
        with self.assertRaises(Http404):
            serve(request, "testdir", document_root=self.document_root, show_indexes=False)

    def test_serve_if_modified_since(self):
        request = Mock(META={"HTTP_IF_MODIFIED_SINCE": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(self.file_path.stat().st_mtime))})
        response = serve(request, "testfile.txt", document_root=self.document_root)
        self.assertIsInstance(response, HttpResponseNotModified)

    def test_directory_index(self):
        response = directory_index("testdir", self.directory_path)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Index of testdir', response.content)

    def test_directory_index_template_not_exist(self):
        Path(self.directory_path / "static/directory_index.html").unlink()
        response = directory_index("testdir", self.directory_path)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Index of testdir', response.content)

    def test_was_modified_since_true(self):
        self.assertTrue(was_modified_since(None, self.file_path.stat().st_mtime, self.file_path.stat().st_size))

    def test_was_modified_since_false(self):
        header = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(self.file_path.stat().st_mtime))
        self.assertFalse(was_modified_since(header, self.file_path.stat().st_mtime, self.file_path.stat().st_size))

    def test_was_modified_since_invalid_header(self):
        self.assertTrue(was_modified_since("invalid_header", self.file_path.stat().st_mtime, self.file_path.stat().st_size))

    def test_was_modified_since_length_mismatch(self):
        header = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(self.file_path.stat().st_mtime)) + "; length=100"
        self.assertTrue(was_modified_since(header, self.file_path.stat().st_mtime, self.file_path.stat().st_size))

if __name__ == '__main__':
    unittest.main()