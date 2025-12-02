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
        self.file_path = self.document_root / "test_file.txt"
        self.file_path.write_text("This is a test file.")
        self.directory_path = self.document_root / "test_dir"
        self.directory_path.mkdir()
        self.directory_index_template = self.document_root / "static/directory_index.html"
        self.directory_index_template.parent.mkdir(parents=True, exist_ok=True)
        self.directory_index_template.write_text("<html><body>Index of {{ directory }}</body></html>")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_serve_valid_file(self):
        request = Mock(META={})
        response = serve(request, "test_file.txt", document_root=self.document_root)
        self.assertIsInstance(response, FileResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertIn("Last-Modified", response.headers)
        self.assertEqual(response['Content-Length'], str(len("This is a test file.")))
        self.assertEqual(response.content, b"This is a test file.")

    def test_serve_missing_file(self):
        request = Mock(META={})
        with self.assertRaises(Http404):
            serve(request, "missing_file.txt", document_root=self.document_root)

    def test_serve_directory_with_show_indexes(self):
        request = Mock(META={})
        response = serve(request, "test_dir", document_root=self.document_root, show_indexes=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Index of', response.content)
        self.assertIn(b'test_dir', response.content)

    def test_serve_directory_without_show_indexes(self):
        request = Mock(META={})
        with self.assertRaises(Http404):
            serve(request, "test_dir", document_root=self.document_root, show_indexes=False)

    def test_serve_file_with_if_modified_since(self):
        request = Mock(META={"HTTP_IF_MODIFIED_SINCE": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())})
        response = serve(request, "test_file.txt", document_root=self.document_root)
        self.assertIsInstance(response, HttpResponseNotModified)

    def test_directory_index(self):
        response = directory_index("test_dir", self.directory_path)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Index of test_dir', response.content)
        self.assertIn(b'test_file.txt', response.content)

    def test_was_modified_since_true(self):
        header = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() - 100))
        self.assertTrue(was_modified_since(header, time.time(), self.file_path.stat().st_size))

    def test_was_modified_since_false(self):
        header = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() + 100))
        self.assertFalse(was_modified_since(header, time.time(), self.file_path.stat().st_size))

    def test_was_modified_since_invalid_header(self):
        self.assertTrue(was_modified_since("invalid_header", 0, 0))

    def test_was_modified_since_no_header(self):
        self.assertTrue(was_modified_since(None, 0, 0))

    def test_serve_file_with_empty_if_modified_since(self):
        request = Mock(META={"HTTP_IF_MODIFIED_SINCE": ""})
        response = serve(request, "test_file.txt", document_root=self.document_root)
        self.assertIsInstance(response, FileResponse)

    def test_serve_directory_with_no_files(self):
        empty_dir = self.document_root / "empty_dir"
        empty_dir.mkdir()
        request = Mock(META={})
        response = serve(request, "empty_dir", document_root=self.document_root, show_indexes=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Index of empty_dir', response.content)
        self.assertIn(b'No files found', response.content)

    def test_serve_file_with_invalid_path(self):
        request = Mock(META={})
        with self.assertRaises(Http404):
            serve(request, "../test_file.txt", document_root=self.document_root)

    def test_directory_index_with_no_template(self):
        response = directory_index("test_dir", self.directory_path)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Index of test_dir', response.content)
        self.assertNotIn(b'Index of {{ directory }}', response.content)

    def test_serve_file_with_non_ascii_characters(self):
        non_ascii_file = self.document_root / "test_file_ñ.txt"
        non_ascii_file.write_text("This file has non-ASCII character.")
        request = Mock(META={})
        response = serve(request, "test_file_ñ.txt", document_root=self.document_root)
        self.assertIsInstance(response, FileResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"This file has non-ASCII character.")

    def test_serve_directory_with_special_characters(self):
        special_dir = self.document_root / "test dir @#"
        special_dir.mkdir()
        request = Mock(META={})
        response = serve(request, "test dir @#", document_root=self.document_root, show_indexes=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Index of test dir @#', response.content)

    def test_serve_file_with_large_size(self):
        large_file = self.document_root / "large_file.txt"
        large_file.write_text("A" * (10**6))  # 1 MB file
        request = Mock(META={})
        response = serve(request, "large_file.txt", document_root=self.document_root)
        self.assertIsInstance(response, FileResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Length'], str(10**6))

    def test_serve_file_with_invalid_method(self):
        request = Mock(META={}, method='POST')
        with self.assertRaises(Http404):
            serve(request, "test_file.txt", document_root=self.document_root)

    def test_directory_index_with_multiple_files(self):
        self.file_path.write_text("Another test file.")
        response = directory_index("test_dir", self.directory_path)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Index of test_dir', response.content)
        self.assertIn(b'test_file.txt', response.content)
        self.assertIn(b'Another test file.', response.content)