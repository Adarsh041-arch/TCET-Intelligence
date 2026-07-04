import os
import sys
import json
import time
import signal
import subprocess
import threading
from typing import Dict, Any, Optional
from pathlib import Path
from app.document_generation.config import doc_gen_config


class SandboxExecutor:
    def __init__(self):
        self._active_processes = {}
        self._lock = threading.Lock()

    def execute(self, generator_module: str, method: str, html: str, template: Optional[Dict] = None, metadata: Optional[Dict] = None, workspace: Optional[str] = None) -> bytes:
        if not doc_gen_config.sandbox_enabled:
            return self._execute_direct(generator_module, method, html, template, metadata, workspace)

        payload = {
            "generator_module": generator_module,
            "method": method,
            "html": html,
            "template": template or {},
            "metadata": metadata or {},
            "workspace": workspace or "",
        }

        payload_json = json.dumps(payload)
        worker_script = self._create_worker_script()

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        proc = subprocess.Popen(
            [sys.executable, "-c", worker_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=Path(__file__).parent.parent.parent.parent,
            text=False,
        )

        with self._lock:
            self._active_processes[proc.pid] = proc

        try:
            stdout, stderr = proc.communicate(
                input=payload_json.encode("utf-8"),
                timeout=doc_gen_config.max_execution_time,
            )

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace")
                raise RuntimeError(f"Sandbox worker failed (exit {proc.returncode}): {error_msg}")

            result = json.loads(stdout.decode("utf-8"))
            if result.get("error"):
                raise RuntimeError(result["error"])

            output_bytes = bytes(result["data"])
            return output_bytes

        except subprocess.TimeoutExpired:
            proc.kill()
            raise RuntimeError(f"Sandbox execution timed out after {doc_gen_config.max_execution_time}s")
        finally:
            with self._lock:
                self._active_processes.pop(proc.pid, None)

    def _execute_direct(self, generator_module: str, method: str, html: str, template: Optional[Dict], metadata: Optional[Dict], workspace: Optional[str]) -> bytes:
        import importlib
        module = importlib.import_module(generator_module)
        generator_cls = getattr(module, method)
        gen = generator_cls
        args = {"html": html, "template": template, "metadata": metadata}
        if workspace:
            gen = gen.__class__()
            if hasattr(gen, 'set_workspace'):
                gen.set_workspace(workspace)
        result = gen.generate(html, template, metadata)
        return result

    def _create_worker_script(self) -> str:
        return """
import sys, json, base64
payload = json.loads(sys.stdin.read())
try:
    import importlib
    module = importlib.import_module(payload["generator_module"])
    cls = None
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and hasattr(obj, 'generate'):
            cls = obj
            break
    if cls is None:
        raise ValueError(f"No generator class found in {payload['generator_module']}")
    gen = cls()
    result = gen.generate(payload["html"], payload.get("template"), payload.get("metadata"))
    if isinstance(result, str):
        result = result.encode("utf-8")
    output = {"data": list(result)}
    sys.stdout.write(json.dumps(output))
except Exception as e:
    sys.stdout.write(json.dumps({"error": str(e)}))
"""


sandbox_executor = SandboxExecutor()
