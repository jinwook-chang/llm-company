import os
import pandas as pd
import io
import contextlib
from langchain_core.tools import tool
from typing import Dict, Union, List
from search import get_retriever

# 캐시 (필요에 따라)
_retriever = None

def get_shared_retriever():
    global _retriever
    if _retriever is None:
        _retriever = get_retriever()
    return _retriever

@tool
def search_documents(query: str) -> str:
    """Vault 내의 지식 베이스 문서를 검색합니다.
    사용자의 질문과 관련된 파일 경로와 본문 일부를 반환합니다.
    반환된 파일 경로를 보고 더 자세한 내용이 필요하면 read_documents 도구를 사용하십시오.
    """
    retriever = get_shared_retriever()
    results = retriever.invoke(query)

    formatted_results = []
    for doc in results:
        source = doc.metadata.get("source", "Unknown")
        snippet = (
            doc.page_content[:500] + "..."
            if len(doc.page_content) > 500
            else doc.page_content
        )
        formatted_results.append(f"Source: {source}\nSnippet: {snippet}\n---")

    return "\n\n".join(formatted_results)

@tool
def read_documents(file_path: str) -> str:
    """지정된 파일 경로의 마크다운 문서 전체 내용을 읽어옵니다.
    반환된 내용을 바탕으로 사용자의 질문에 대한 근거를 포함하여 답변하십시오.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"파일을 읽는 중 오류가 발생했습니다 ({file_path}): {e}"

def get_tools():
    return [search_documents, read_documents]
