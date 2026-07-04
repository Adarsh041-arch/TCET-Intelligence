import os
import uuid
import time
import shutil
import threading
from pathlib import Path
from typing import Optional
from app.document_generation.config import doc_gen_config


class FileStorage:
    def __init__(self):
        self.base_dir = Path(doc_gen_config.storage_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_thread.start()

    def create_workspace(self, job_id: Optional[str] = None) -> str:
        workspace_id = job_id or str(uuid.uuid4())
        workspace_path = self.base_dir / workspace_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        return str(workspace_path)

    def store_file(self, data: bytes, filename: str, job_id: str) -> str:
        workspace = self.base_dir / job_id
        workspace.mkdir(parents=True, exist_ok=True)
        filepath = workspace / filename
        with open(filepath, "wb") as f:
            f.write(data)
        return str(filepath)

    def read_file(self, filepath: str) -> Optional[bytes]:
        path = Path(filepath)
        if path.exists() and path.is_file():
            with open(path, "rb") as f:
                return f.read()
        return None

    def get_file_path(self, job_id: str, filename: str) -> str:
        return str(self.base_dir / job_id / filename)

    def cleanup_workspace(self, job_id: str):
        workspace = self.base_dir / job_id
        if workspace.exists():
            shutil.rmtree(str(workspace), ignore_errors=True)

    def _periodic_cleanup(self):
        while True:
            time.sleep(doc_gen_config.cleanup_interval_minutes * 60)
            now = time.time()
            for item in self.base_dir.iterdir():
                if item.is_dir():
                    age = now - item.stat().st_mtime
                    if age > doc_gen_config.cleanup_interval_minutes * 60 * 2:
                        shutil.rmtree(str(item), ignore_errors=True)

    def get_download_url(self, job_id: str, filename: str) -> str:
        return f"/api/document-gen/download/{job_id}/{filename}"


file_storage = FileStorage()
