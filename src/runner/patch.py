from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def apply_patch_to_code(code_src: str, code_path: str, patch_text: str) -> str:
    work_dir = tempfile.mkdtemp()

    code_file_path = Path(work_dir) / code_path
    code_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(code_file_path, "w") as code_file:
        code_file.write(code_src)

    patch_file_path = Path(work_dir) / "temp.patch"
    with open(patch_file_path, "w") as patch_file:
        patch_file.write(patch_text)

    print("Applying patch:")

    print(work_dir)

    # subprocess.run(
    #     ["patch", str(code_file_path), str(patch_file_path)],
    #     cwd=work_dir,
    # )

    with open(code_file_path, "r") as code_file:
        patched_code = code_file.read()

    # cleanup
    # os.remove(code_file_path)
    # os.remove(patch_file_path)
    # os.rmdir(work_dir)

    return patched_code
