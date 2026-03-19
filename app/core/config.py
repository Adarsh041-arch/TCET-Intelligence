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
    chroma_persist_directory: str
    upload_directory: str
    database_url: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    similarity_threshold: float
    admin_username: str
    admin_password: str
    secret_key: str


def load_config(config_path: str = "config.json") -> Config:
    with open(config_path, "r") as f:
        config_data = json.load(f)
    return Config(**config_data)


config = load_config()
