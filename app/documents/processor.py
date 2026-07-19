import hashlib
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
            
            import json
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({
                    "page_count": page_count,
                    "estimated_tokens": estimated_tokens,
                    "filename": filename
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
                text_parts.append(f"=== Sheet: {sheet_name} ===")
                df = pd.read_excel(excel_file, sheet_name=sheet_name, engine="openpyxl")
                text_parts.append(
                    "Columns: " + ", ".join([str(col) for col in df.columns])
                )
                for idx, row in df.iterrows():
                    row_text = " | ".join(
                        [f"{col}: {val}" for col, val in row.items() if pd.notna(val)]
                    )
                    if row_text.strip():
                        text_parts.append(row_text)
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

    def _chunk_text(self, text: str) -> List[str]:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = text_splitter.split_text(text)
        return [chunk.strip() for chunk in chunks if chunk.strip()]

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
