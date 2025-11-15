from __future__ import annotations
from typing import Dict
from src.core.types import RunnerRequest


def generate_minimal_request(repo: str, version: str, code_file: str) -> RunnerRequest:
    test_src = """import unittest
import time
from django.views.static import was_modified_since


class StaticUtilsTests(unittest.TestCase):
    def test_was_modified_since_not_modified(self):
        \"""
        When the If-Modified-Since header matches the mtime and size,
        was_modified_since() should return False.
        \"""
        mtime = int(time.time())
        header = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(mtime))

        # When header time == mtime and size matches, should return False.
        self.assertFalse(was_modified_since(f"{header}; length=10", mtime, 10))
"""

    return {"repo": repo, "version": version, "code_file": code_file, "test_src": test_src}
