import json
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


class Config(BaseModel):
    project_name: str
    version: str
    ollama_base_url: str
    llm_model: str
    embedding_model: str
    small_document_threshold: int
    chroma_persist_directory: str
    user_chroma_persist_directory: str = "data/chroma_user"
    upload_directory: str
    mcp_allowed_directory: Optional[str] = None
    tcet_docs_directory: str = "data/tcet_docs"
    database_url: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    similarity_threshold: float
    admin_username: str
    admin_password: str
    secret_key: str
    default_web_search_provider: str = "tavily"
    sql_max_iterations: int = 4


def load_config(config_path: str = "config.json") -> Config:
    with open(config_path, "r") as f:
        config_data = json.load(f)
    
    # Allow overriding any config field using OS environment variables
    for env_key, env_val in os.environ.items():
        config_key = env_key.lower()
        if config_key in config_data:
            orig_val = config_data[config_key]
            if isinstance(orig_val, bool):
                config_data[config_key] = env_val.lower() in ("true", "1", "yes")
            elif isinstance(orig_val, int):
                config_data[config_key] = int(env_val)
            elif isinstance(orig_val, float):
                config_data[config_key] = float(env_val)
            else:
                config_data[config_key] = env_val
                
    return Config(**config_data)


config = load_config()
