import os
import pickle
import sys
from collections import defaultdict
from typing import List
from pydantic import Field, ConfigDict

from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from utils import get_embeddings

INDEX_PATH = "faiss_index"
DOCS_CACHE_PATH = "docs_cache.pkl"

class SimpleEnsembleRetriever(BaseRetriever):
    retrievers: List[BaseRetriever]
    weights: List[float] = Field(default_factory=lambda: [0.5, 0.5])
    c: int = 60

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        all_docs = [
            r.invoke(query, config={"callbacks": run_manager.get_child() if run_manager else None}) 
            for r in self.retrievers
        ]
        
        rrf_score = defaultdict(float)
        doc_map = {}
        
        for docs, weight in zip(all_docs, self.weights):
            for rank, doc in enumerate(docs):
                doc_id = doc.page_content
                rrf_score[doc_id] += weight / (rank + self.c)
                if doc_id not in doc_map:
                    doc_map[doc_id] = doc
        
        sorted_docs = sorted(rrf_score.items(), key=lambda x: x[1], reverse=True)
        return [doc_map[doc_id] for doc_id, score in sorted_docs]

def get_retriever():
    embeddings = get_embeddings()
    
    if not os.path.exists(INDEX_PATH):
        raise FileNotFoundError("FAISS 인덱스가 없습니다. 'python ingest.py'를 먼저 실행하세요.")
    
    vectorstore = FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    
    if not os.path.exists(DOCS_CACHE_PATH):
        raise FileNotFoundError("문서 캐시가 없습니다. 'python ingest.py'를 먼저 실행하세요.")
    
    with open(DOCS_CACHE_PATH, "rb") as f:
        documents = pickle.load(f)
    
    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = 5
    
    return SimpleEnsembleRetriever(retrievers=[vector_retriever, bm25_retriever], weights=[0.5, 0.5])

def search(query):
    try:
        retriever = get_retriever()
        docs = retriever.invoke(query)
        
        print(f"\n🔍 '{query}'에 대한 검색 결과:\n")
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "Unknown")
            print(f"[{i+1}] Source: {source}")
            # Print a snippet
            content = doc.page_content[:200].replace('\n', ' ')
            print(f"   Snippet: {content}...")
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ 검색 중 오류 발생: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search.py \"your search query\"")
    else:
        query = " ".join(sys.argv[1:])
        search(query)
