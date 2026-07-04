from pydantic import BaseModel
from typing import Optional
import tempfile
import os


class DocumentGenConfig(BaseModel):
    storage_dir: str = os.path.join(tempfile.gettempdir(), "docgen")
    max_file_size: int = 50 * 1024 * 1024
    max_execution_time: int = 120
    max_memory_mb: int = 512
    sandbox_enabled: bool = True
    preview_enabled: bool = True
    template_dir: str = ""
    allowed_formats: list = ["docx", "pdf", "pptx", "xlsx"]
    cleanup_interval_minutes: int = 30
    max_concurrent_jobs: int = 4


doc_gen_config = DocumentGenConfig()
