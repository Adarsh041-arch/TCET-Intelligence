import hashlib
import re
import uuid
import os
import tempfile
from typing import List, Dict, Any, Optional
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
import PyPDF2
import docx
import pandas as pd
from app.core.config import config
from app.services.vector_store import vector_store, user_vector_store, compute_file_hash
from app.models.database import db


class DocumentProcessor:
    def __init__(self):
        self.chunk_size = config.chunk_size
        self.chunk_overlap = config.chunk_overlap
        self.upload_dir = config.upload_directory
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)

    def process_file(
        self, file_content: bytes, filename: str, user_id: str,
        extra_metadata: Optional[Dict[str, Any]] = None,
        target_store: Optional[Any] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        store = target_store or user_vector_store
        # Hash incorporates user_id to ensure same file uploaded by different users has different hashes
        file_hash = compute_file_hash(file_content + user_id.encode())

        existing_doc = db.get_document_by_hash(file_hash)
        if existing_doc:
            if not force:
                return {
                    "success": True,
                    "message": "Document already exists",
                    "doc_id": existing_doc["doc_id"],
                    "filename": existing_doc["filename"],
                }
            else:
                # Force re-indexing: clean up old document metadata and embeddings first
                self.delete_document(existing_doc["doc_id"])

        doc_id = str(uuid.uuid4())
        file_ext = os.path.splitext(filename)[1].lower()

        text = self._extract_text(file_content, file_ext)
        if not text:
            return {"success": False, "message": "Could not extract text from file"}

        # Count pages if PDF
        page_count = 0
        if file_ext == ".pdf":
            try:
                import io
                pdf_file = io.BytesIO(file_content)
                reader = PyPDF2.PdfReader(pdf_file)
                page_count = len(reader.pages)
            except Exception as e:
                print(f"Error counting PDF pages: {e}")
        
        estimated_tokens = int(len(text) / 4)
        # We only skip vector store indexing for user-uploaded documents (user_vector_store).
        # Core documents (vector_store) must always be indexed in the vector database.
        is_user_store = (store == user_vector_store)
        is_large = not is_user_store or (page_count > 30 or estimated_tokens > 30000)

        # If it's a large file, compute embeddings and index it in the vector store
        chunks_created = 0
        if is_large:
            chunks = self._chunk_text(text)
            if not chunks:
                return {"success": False, "message": "No content to index"}
            chunks_created = len(chunks)

            metadatas = []
            for i in range(len(chunks)):
                meta = {
                    "doc_id": doc_id,
                    "filename": filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "user_id": user_id,  # Keep user isolation in vector db
                }
                if extra_metadata:
                    meta.update(extra_metadata)
                metadatas.append(meta)

            success = store.add_documents(chunks, metadatas, doc_id)
            if not success:
                return {"success": False, "message": "Failed to store embeddings"}

        # Write sidecar files in the upload directory
        txt_path = os.path.join(self.upload_dir, f"{doc_id}.txt")
        meta_path = os.path.join(self.upload_dir, f"{doc_id}.json")
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)

            # Save original binary for image files (multimodal chat)
            is_image = file_ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
            orig_path = ""
            if is_image:
                orig_path = os.path.join(self.upload_dir, f"{doc_id}{file_ext}")
                with open(orig_path, "wb") as f:
                    f.write(file_content)

            import json
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({
                    "page_count": page_count,
                    "estimated_tokens": estimated_tokens,
                    "filename": filename,
                    "file_ext": file_ext,
                    "orig_path": orig_path,
                }, f)
        except Exception as e:
            print(f"Error writing sidecar files: {e}")

        db.save_document(doc_id, filename, file_hash, file_ext, user_id)
        return {
            "success": True,
            "doc_id": doc_id,
            "filename": filename,
            "chunks_created": chunks_created,
        }

    def _extract_text(self, file_content: bytes, file_ext: str) -> Optional[str]:
        file_ext = file_ext.lower()
        extractors = {
            ".pdf": self._extract_pdf,
            ".docx": self._extract_docx,
            ".txt": lambda _: file_content.decode("utf-8", errors="ignore"),
            ".xlsx": self._extract_excel,
            ".xls": self._extract_excel,
            ".xlsm": self._extract_excel,
            ".csv": self._extract_csv,
            ".json": self._extract_json,
            ".html": self._extract_html,
            ".htm": self._extract_html,
            ".png": self._extract_image,
            ".jpg": self._extract_image,
            ".jpeg": self._extract_image,
            ".gif": self._extract_image,
            ".bmp": self._extract_image,
            ".webp": self._extract_image,
        }

        extractor = extractors.get(file_ext)
        if extractor:
            try:
                return extractor(file_content)
            except Exception as e:
                print(f"Error extracting text from {file_ext}: {e}")
                return None
        return None

    def _extract_pdf(self, file_content: bytes) -> str:
        text_parts = []
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            reader = PyPDF2.PdfReader(tmp_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass

        return "\n\n".join(text_parts)

    def _extract_docx(self, file_content: bytes) -> str:
        text_parts = []
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            doc = docx.Document(tmp_path)
            text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass

        return "\n\n".join(text_parts)

    def _extract_excel(self, file_content: bytes) -> str:
        text_parts = []
        ext = ".xlsx"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            excel_file = pd.ExcelFile(tmp_path, engine="openpyxl")
            for sheet_name in excel_file.sheet_names:
                text_parts.append(f"<<<SHEET: {sheet_name}>>>")
                df = pd.read_excel(excel_file, sheet_name=sheet_name, engine="openpyxl")
                if df.empty:
                    text_parts.append("(empty sheet)")
                    text_parts.append("")
                    continue

                # ── Pre-computed stats ──
                stats = []
                for col in df.columns:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        vals = df[col].dropna()
                        if not vals.empty:
                            stats.append(
                                f"{col}: count={len(vals)}, min={vals.min()}, "
                                f"max={vals.max()}, avg={vals.mean():.2f}"
                            )
                if stats:
                    text_parts.append("[Stats] " + " | ".join(stats))

                # ── Markdown table ──
                headers = [str(c) for c in df.columns]
                text_parts.append("| " + " | ".join(headers) + " |")
                text_parts.append("| " + " | ".join(["---"] * len(headers)) + " |")
                for _, row in df.iterrows():
                    cells = []
                    for c in df.columns:
                        v = row[c]
                        cells.append(str(v) if pd.notna(v) else "")
                    text_parts.append("| " + " | ".join(cells) + " |")
                text_parts.append("")
        except Exception as e:
            print(f"Excel extraction error: {e}")
            raise
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass

        return "\n".join(text_parts) if text_parts else ""

    def _extract_csv(self, file_content: bytes) -> str:
        text_parts = []
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            df = pd.read_csv(tmp_path)
            text_parts.append("Columns: " + ", ".join([str(col) for col in df.columns]))
            for idx, row in df.iterrows():
                row_text = " | ".join(
                    [f"{col}: {val}" for col, val in row.items() if pd.notna(val)]
                )
                if row_text.strip():
                    text_parts.append(row_text)
        except Exception as e:
            print(f"CSV extraction error: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass

        return "\n".join(text_parts) if text_parts else ""

    def _extract_json(self, file_content: bytes) -> str:
        import json

        try:
            data = json.loads(file_content.decode("utf-8", errors="ignore"))
            return json.dumps(data, indent=2, ensure_ascii=False)
        except:
            return file_content.decode("utf-8", errors="ignore")

    def _extract_html(self, file_content: bytes) -> str:
        from bs4 import BeautifulSoup

        try:
            soup = BeautifulSoup(
                file_content.decode("utf-8", errors="ignore"), "html.parser"
            )
            text = soup.get_text(separator="\n", strip=True)
            return text
        except:
            return file_content.decode("utf-8", errors="ignore")

    def _extract_image(self, file_content: bytes) -> str:
        try:
            import pytesseract
            from PIL import Image
            import io

            image = Image.open(io.BytesIO(file_content))
            text = pytesseract.image_to_string(image)
            return text.strip() if text.strip() else "[No text detected in image]"
        except ImportError:
            return "[Image uploaded. OCR library (pytesseract) not installed. Install with: pip install pytesseract]"
        except Exception as e:
            print(f"Image OCR error: {e}")
            return "[Could not extract text from image]"

    def _chunk_text(self, text: str) -> List[str]:
        # Table-aware chunking: keep <<<SHEET: ...>>> blocks atomic.
        # Split by sheet markers first, then by row boundaries if still too large.
        sheet_pattern = r"(<<<SHEET: [^>]+>>>)"
        parts = re.split(sheet_pattern, text)
        sheet_blocks: List[str] = []
        i = 0
        while i < len(parts):
            if parts[i].startswith("<<<SHEET:"):
                block = parts[i] + (parts[i + 1] if i + 1 < len(parts) else "")
                sheet_blocks.append(block.strip())
                i += 2
            else:
                leftover = parts[i].strip()
                if leftover:
                    sheet_blocks.append(leftover)
                i += 1

        chunks: List[str] = []
        for block in sheet_blocks:
            if len(block) <= self.chunk_size:
                chunks.append(block)
            else:
                # Split large block at markdown table row boundaries
                lines = block.split("\n")
                current = []
                current_len = 0
                for line in lines:
                    line_len = len(line) + 1
                    if current_len + line_len > self.chunk_size and current:
                        chunks.append("\n".join(current))
                        current = []
                        current_len = 0
                    current.append(line)
                    current_len += line_len
                if current:
                    chunks.append("\n".join(current))

        return [c.strip() for c in chunks if c.strip()]

    def delete_document(self, doc_id: str) -> bool:
        user_vector_store.delete_document(doc_id)
        vector_store.delete_document(doc_id)
        
        # Delete sidecar files if they exist
        txt_path = os.path.join(self.upload_dir, f"{doc_id}.txt")
        meta_path = os.path.join(self.upload_dir, f"{doc_id}.json")
        try:
            if os.path.exists(txt_path):
                os.remove(txt_path)
            if os.path.exists(meta_path):
                os.remove(meta_path)
        except Exception as e:
            print(f"Error deleting sidecar files: {e}")
            
        return db.delete_document(doc_id)


document_processor = DocumentProcessor()
