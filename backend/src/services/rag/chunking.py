"""Split parsed sections into token-sized chunks that keep page / heading metadata."""

from dataclasses import dataclass
from functools import lru_cache

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.services.rag.parsers import Section

ENCODING = "cl100k_base"
CHUNK_TOKENS = 400
OVERLAP_TOKENS = 60


@dataclass
class ChunkDraft:
    ordinal: int
    content: str  # shown to the model and in citations
    embed_text: str  # content plus a "filename › heading" header, for better recall
    token_count: int
    page: int | None = None
    heading_path: str | None = None


@lru_cache
def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding(ENCODING)


def count_tokens(text: str) -> int:
    return len(_encoding().encode(text, disallowed_special=()))


def chunk_sections(
    sections: list[Section],
    title: str,
    chunk_tokens: int = CHUNK_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[ChunkDraft]:
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name=ENCODING, chunk_size=chunk_tokens, chunk_overlap=overlap_tokens
    )
    drafts: list[ChunkDraft] = []
    for section in sections:
        for piece in splitter.split_text(section.text):
            piece = piece.strip()
            if not piece:
                continue
            header = " › ".join(p for p in (title, section.heading_path) if p)
            drafts.append(
                ChunkDraft(
                    ordinal=len(drafts),
                    content=piece,
                    embed_text=f"{header}\n\n{piece}",
                    token_count=count_tokens(piece),
                    page=section.page,
                    heading_path=section.heading_path,
                )
            )
    return drafts
