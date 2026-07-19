import hashlib
import uuid
import os
from typing import List, Dict, Any, Optional
from app.core.config import config
from app.services.embeddings import embedding_service


def compute_file_hash(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()


class VectorStore:
    def __init__(self, persist_directory: str = None, collection_name: str = "documents"):
        self.persist_directory = persist_directory or config.chroma_persist_directory
        self.collection_name = collection_name
        
        # Determine PostgreSQL setup
        self.db_url = config.database_url
        self.is_postgres = self.db_url.startswith("postgresql://") or self.db_url.startswith("postgres://")
        self.store_type = "user" if "user" in self.collection_name.lower() or "user" in (self.persist_directory or "").lower() else "core"
        
        self._client = None
        self._collection = None
        
        if self.is_postgres:
            self._init_postgres_db()

    def _init_postgres_db(self):
        import psycopg2
        conn = psycopg2.connect(self.db_url)
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS chatbot_embeddings (
                            id TEXT PRIMARY KEY,
                            doc_id TEXT NOT NULL,
                            chunk_index INTEGER NOT NULL,
                            total_chunks INTEGER NOT NULL,
                            filename TEXT NOT NULL,
                            user_id TEXT,
                            content TEXT NOT NULL,
                            embedding vector,
                            store_type TEXT NOT NULL CHECK (store_type IN ('core', 'user'))
                        )
                    """)
        except Exception as e:
            print(f"Error initializing Postgres pgvector store: {e}")
        finally:
            conn.close()

    @property
    def client(self):
        if self._client is None and not self.is_postgres:
            import chromadb
            from chromadb.config import Settings
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False),
            )
        return self._client

    @property
    def collection(self):
        if self._collection is None and not self.is_postgres:
            try:
                self._collection = self.client.get_collection(name=self.collection_name)
            except Exception:
                self._collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                    get_or_create=True,
                )
        return self._collection

    def _parse_chroma_filter(self, filter_dict, params):
        if not filter_dict:
            return "", []
        
        sql_parts = []
        if "$and" in filter_dict:
            conditions = filter_dict["$and"]
            for cond in conditions:
                part, p = self._parse_chroma_filter(cond, params)
                if part:
                    sql_parts.append(f"({part})")
            return " AND ".join(sql_parts), params
        
        if "$or" in filter_dict:
            conditions = filter_dict["$or"]
            for cond in conditions:
                part, p = self._parse_chroma_filter(cond, params)
                if part:
                    sql_parts.append(f"({part})")
            return " OR ".join(sql_parts), params
        
        for key, val in filter_dict.items():
            if isinstance(val, dict):
                for op, op_val in val.items():
                    if op == "$in":
                        placeholders = ", ".join(["%s"] * len(op_val))
                        sql_parts.append(f"{key} IN ({placeholders})")
                        params.extend(op_val)
                    elif op == "$eq":
                        sql_parts.append(f"{key} = %s")
                        params.append(op_val)
            else:
                sql_parts.append(f"{key} = %s")
                params.append(val)
        
        return " AND ".join(sql_parts), params

    def add_documents(
        self, texts: List[str], metadatas: List[Dict[str, Any]], doc_id: str
    ) -> bool:
        if not self.is_postgres:
            try:
                embeddings = embedding_service.embed_texts(texts)
                ids = [f"{doc_id}_{i}" for i in range(len(texts))]
                self.collection.add(
                    embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids
                )
                return True
            except Exception as e:
                print(f"Error adding documents to Chroma: {e}")
                return False

        import psycopg2
        conn = psycopg2.connect(self.db_url)
        try:
            embeddings = embedding_service.embed_texts(texts)
            with conn:
                with conn.cursor() as cursor:
                    for i, text in enumerate(texts):
                        meta = metadatas[i]
                        cid = f"{doc_id}_{i}"
                        filename = meta.get("filename", "")
                        user_id = meta.get("user_id")
                        chunk_index = meta.get("chunk_index", i)
                        total_chunks = meta.get("total_chunks", len(texts))
                        emb = embeddings[i]
                        
                        emb_str = f"[{','.join(map(str, emb))}]"
                        
                        cursor.execute(
                            """
                            INSERT INTO chatbot_embeddings (id, doc_id, chunk_index, total_chunks, filename, user_id, content, embedding, store_type)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE SET
                                content = EXCLUDED.content,
                                embedding = EXCLUDED.embedding
                            """,
                            (cid, doc_id, chunk_index, total_chunks, filename, user_id, text, emb_str, self.store_type)
                        )
            return True
        except Exception as e:
            print(f"Error adding documents to Postgres pgvector: {e}")
            return False
        finally:
            conn.close()

    def retrieve_similar(
        self, query: str, top_k: Optional[int] = None, threshold: Optional[float] = None,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        if not self.is_postgres:
            try:
                k = top_k or config.top_k
                sim_threshold = threshold or config.similarity_threshold
                query_embedding = embedding_service.embed_text(query)
                kwargs = {
                    "query_embeddings": [query_embedding],
                    "n_results": k,
                    "include": ["documents", "metadatas", "distances"],
                }
                if filter_dict:
                    kwargs["where"] = filter_dict
                    
                results = self.collection.query(**kwargs)
                docs = []
                if results["documents"] and len(results["documents"]) > 0:
                    for i, doc in enumerate(results["documents"][0]):
                        distance = results["distances"][0][i] if results["distances"] else 0
                        similarity = 1 - distance
                        if similarity >= sim_threshold:
                            docs.append({
                                "content": doc,
                                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                                "similarity": similarity,
                            })
                return docs
            except Exception as e:
                print(f"Error retrieving documents from Chroma: {e}")
                return []

        import psycopg2
        k = top_k or config.top_k
        sim_threshold = threshold or config.similarity_threshold

        try:
            query_embedding = embedding_service.embed_text(query)
            emb_str = f"[{','.join(map(str, query_embedding))}]"
            
            sql_filter = ""
            params = [emb_str, self.store_type]
            
            if filter_dict:
                parsed_sql, parsed_params = self._parse_chroma_filter(filter_dict, [])
                if parsed_sql:
                    sql_filter = f" AND {parsed_sql}"
                    params.extend(parsed_params)
            
            query_sql = f"""
                SELECT doc_id, chunk_index, total_chunks, filename, user_id, content,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM chatbot_embeddings
                WHERE store_type = %s {sql_filter}
                ORDER BY embedding <=> %s::vector ASC
                LIMIT %s
            """
            params.extend([emb_str, k])
            
            conn = psycopg2.connect(self.db_url)
            docs = []
            try:
                with conn:
                    with conn.cursor() as cursor:
                        cursor.execute(query_sql, params)
                        rows = cursor.fetchall()
                        for row in rows:
                            similarity = row[6] if row[6] is not None else 0.0
                            if similarity >= sim_threshold:
                                docs.append({
                                    "content": row[5],
                                    "metadata": {
                                        "doc_id": row[0],
                                        "chunk_index": row[1],
                                        "total_chunks": row[2],
                                        "filename": row[3],
                                        "user_id": row[4]
                                    },
                                    "similarity": similarity
                                })
            finally:
                conn.close()
            return docs
        except Exception as e:
            print(f"Error retrieving documents from Postgres pgvector: {e}")
            return []

    def get_all_filenames(self, where: Optional[Dict[str, Any]] = None) -> List[str]:
        if not self.is_postgres:
            try:
                kwargs = {"include": ["metadatas"]}
                if where:
                    kwargs["where"] = where
                all_metadatas = self.collection.get(**kwargs)["metadatas"]
                filenames = set()
                for meta in all_metadatas:
                    if meta and "filename" in meta:
                        filenames.add(meta["filename"])
                return sorted(filenames)
            except Exception as e:
                print(f"Error getting filenames from Chroma: {e}")
                return []

        import psycopg2
        sql_filter = ""
        params = [self.store_type]
        if where:
            parsed_sql, parsed_params = self._parse_chroma_filter(where, [])
            if parsed_sql:
                sql_filter = f" AND {parsed_sql}"
                params.extend(parsed_params)

        query_sql = f"SELECT DISTINCT filename FROM chatbot_embeddings WHERE store_type = %s {sql_filter}"
        conn = psycopg2.connect(self.db_url)
        filenames = set()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query_sql, params)
                    rows = cursor.fetchall()
                    for row in rows:
                        filenames.add(row[0])
        except Exception as e:
            print(f"Error getting filenames from Postgres: {e}")
        finally:
            conn.close()
        return sorted(filenames)

    def get_all_chunks_by_filename(self, filename: str) -> List[Dict[str, Any]]:
        if not self.is_postgres:
            try:
                results = self.collection.get(
                    where={"filename": filename},
                    include=["documents", "metadatas"],
                )
                docs = []
                if results["documents"]:
                    for i, doc in enumerate(results["documents"]):
                        docs.append({
                            "content": doc,
                            "metadata": results["metadatas"][i] if results["metadatas"] else {},
                            "similarity": 1.0,
                        })
                docs.sort(key=lambda d: d["metadata"].get("chunk_index", 0))
                return docs
            except Exception as e:
                print(f"Error getting chunks from Chroma: {e}")
                return []

        import psycopg2
        query_sql = """
            SELECT doc_id, chunk_index, total_chunks, filename, user_id, content
            FROM chatbot_embeddings
            WHERE filename = %s AND store_type = %s
            ORDER BY chunk_index ASC
        """
        conn = psycopg2.connect(self.db_url)
        docs = []
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query_sql, (filename, self.store_type))
                    rows = cursor.fetchall()
                    for row in rows:
                        docs.append({
                            "content": row[5],
                            "metadata": {
                                "doc_id": row[0],
                                "chunk_index": row[1],
                                "total_chunks": row[2],
                                "filename": row[3],
                                "user_id": row[4]
                            },
                            "similarity": 1.0
                        })
        except Exception as e:
            print(f"Error getting chunks from Postgres: {e}")
        finally:
            conn.close()
        return docs

    def get_document_count(self) -> int:
        if not self.is_postgres:
            try:
                return self.collection.count()
            except Exception:
                return 0

        import psycopg2
        query_sql = "SELECT COUNT(*) FROM chatbot_embeddings WHERE store_type = %s"
        conn = psycopg2.connect(self.db_url)
        count = 0
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query_sql, (self.store_type,))
                    row = cursor.fetchone()
                    count = row[0] if row else 0
        except Exception as e:
            print(f"Error getting document count from Postgres: {e}")
        finally:
            conn.close()
        return count

    def delete_document(self, doc_id: str) -> bool:
        if not self.is_postgres:
            try:
                all_ids = self.collection.get()["ids"]
                ids_to_delete = [id for id in all_ids if id.startswith(f"{doc_id}_")]
                if ids_to_delete:
                    self.collection.delete(ids=ids_to_delete)
                return True
            except Exception as e:
                print(f"Error deleting document from Chroma: {e}")
                return False

        import psycopg2
        query_sql = "DELETE FROM chatbot_embeddings WHERE doc_id = %s AND store_type = %s"
        conn = psycopg2.connect(self.db_url)
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query_sql, (doc_id, self.store_type))
            return True
        except Exception as e:
            print(f"Error deleting document from Postgres: {e}")
            return False
        finally:
            conn.close()

    def clear_all(self) -> bool:
        if not self.is_postgres:
            try:
                self.client.delete_collection(name=self.collection_name)
                self._collection = None
                return True
            except Exception as e:
                print(f"Error clearing collection in Chroma: {e}")
                return False

        import psycopg2
        query_sql = "DELETE FROM chatbot_embeddings WHERE store_type = %s"
        conn = psycopg2.connect(self.db_url)
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query_sql, (self.store_type,))
            return True
        except Exception as e:
            print(f"Error clearing collection in Postgres: {e}")
            return False
        finally:
            conn.close()


# TCET managed documents store
vector_store = VectorStore()

# User uploaded documents store
user_vector_store = VectorStore(persist_directory=config.user_chroma_persist_directory, collection_name="user_documents")
