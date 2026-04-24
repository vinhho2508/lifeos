from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from src.core.database import settings

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_text(text)

async def get_embeddings(texts: List[str]):
    if not settings.OPENAI_API_KEY:
        # Mock embeddings
        return [[0.1] * 1536 for _ in texts]
    
    embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
    return await embeddings.aembed_documents(texts)
