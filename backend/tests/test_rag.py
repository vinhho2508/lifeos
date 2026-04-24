import pytest
from src.services.rag_service import chunk_text

def test_chunk_text():
    text = "This is a long text that should be split into smaller chunks for processing."
    chunks = chunk_text(text, chunk_size=20)
    
    assert len(chunks) > 1
    assert all(len(c) <= 30 for c in chunks) # allowing some buffer
