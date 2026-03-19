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
from app.services.vector_store import vector_store
from app.models.database import db


class DocumentProcessor:
    def __init__(self):
        self.chunk_size = config.chunk_size
        self.chunk_overlap = config.chunk_overlap
        self.upload_dir = config.upload_directory
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)

    def process_file(
        self, file_content: bytes, filename: str, user_id: str
    ) -> Dict[str, Any]:
        file_hash = vector_store.compute_file_hash(file_content)

        existing_doc = db.get_document_by_hash(file_hash)
        if existing_doc:
            return {
                "success": False,
                "message": "Document already exists",
                "doc_id": existing_doc["doc_id"],
            }

        doc_id = str(uuid.uuid4())
        file_ext = os.path.splitext(filename)[1].lower()

        text = self._extract_text(file_content, file_ext)
        if not text:
            return {"success": False, "message": "Could not extract text from file"}

        chunks = self._chunk_text(text)
        if not chunks:
            return {"success": False, "message": "No content to index"}

        metadatas = [
            {
                "doc_id": doc_id,
                "filename": filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]

        success = vector_store.add_documents(chunks, metadatas, doc_id)

        if success:
            db.save_document(doc_id, filename, file_hash, file_ext, user_id)
            return {
                "success": True,
                "doc_id": doc_id,
                "filename": filename,
                "chunks_created": len(chunks),
            }
        else:
            return {"success": False, "message": "Failed to store embeddings"}

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
        vector_store.delete_document(doc_id)
        return db.delete_document(doc_id)


document_processor = DocumentProcessor()
