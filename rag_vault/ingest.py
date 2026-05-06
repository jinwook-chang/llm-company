import os
import glob
import pickle
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from utils import get_embeddings

# Paths
VAULT_DIR = "../vault"
INDEX_PATH = "faiss_index"
DOCS_CACHE_PATH = "docs_cache.pkl"

def load_documents(data_dir=VAULT_DIR):
    """Loads markdown documents from the vault and extracts domain info."""
    print(f"Loading documents from {data_dir}...")
    md_files = glob.glob(os.path.join(data_dir, "**/*.md"), recursive=True)
    documents = []
    
    for md_file in md_files:
        try:
            # For vault, we'll just use the relative path as domain
            relative_path = os.path.relpath(md_file, data_dir)
            domain = os.path.dirname(relative_path) or "root"
            
            loader = TextLoader(md_file, encoding="utf-8")
            doc_list = loader.load()
            if doc_list:
                for doc in doc_list:
                    doc.metadata["source"] = md_file
                    doc.metadata["domain"] = domain
                    documents.append(doc)
        except Exception as e:
            print(f"Error loading {md_file}: {e}")
    
    # Save document cache
    with open(DOCS_CACHE_PATH, "wb") as f:
        pickle.dump(documents, f)
        
    return documents

def create_indexes(documents):
    """Creates FAISS vector index and saves it to disk."""
    embeddings = get_embeddings()
    
    # Check if we are using gemini-embedding-2 which requires individual processing
    is_gemini_2 = "gemini-embedding-2" in getattr(embeddings, "model", "")
    
    print(f"Creating FAISS index for {len(documents)} documents...")
    
    # If gemini-embedding-2, process documents one by one to ensure unique embeddings
    if is_gemini_2:
        print("Detected Gemini Embedding 2: Processing documents individually (Batch Prediction not supported)...")
        results = []
        for i, doc in enumerate(documents):
            # Using from_documents with a single document list
            vs = FAISS.from_documents([doc], embeddings)
            results.append(vs)
            if (i + 1) % 5 == 0 or (i + 1) == len(documents):
                print(f"Progress: {i+1}/{len(documents)} documents completed...")
            # Slight delay to respect rate limits if needed
            time.sleep(0.1)
    else:
        # Standard batch processing for other models
        batch_size = 20
        doc_chunks = [documents[i:i + batch_size] for i in range(0, len(documents), batch_size)]
        total_chunks = len(doc_chunks)
        
        results = []
        print(f"Starting sequential embedding (Total {total_chunks} batches)...")
        for i, chunk in enumerate(doc_chunks):
            if i > 0:
                time.sleep(1) # Avoid quota limits
            vs = FAISS.from_documents(chunk, embeddings)
            results.append(vs)
            print(f"Progress: {i+1}/{total_chunks} batches completed...")
    
    print("Merging and saving FAISS index...")
    vectorstore = results[0]
    for next_vs in results[1:]:
        vectorstore.merge_from(next_vs)
    vectorstore.save_local(INDEX_PATH)
    
    print("✅ FAISS index saved successfully.")

def main():
    print("🚀 Vault 인덱싱을 시작합니다...")
    start_time = time.time()

    # Reset index and cache
    if os.path.exists(DOCS_CACHE_PATH):
        os.remove(DOCS_CACHE_PATH)
    if os.path.exists(INDEX_PATH):
        shutil.rmtree(INDEX_PATH)

    # 1. Load documents
    documents = load_documents(VAULT_DIR)
    if not documents:
        print(f"❌ '{VAULT_DIR}' 폴더에 마크다운 파일이 없습니다.")
        return
    print(f"총 {len(documents)}개의 문서를 로드했습니다.")

    # 2. Create index
    create_indexes(documents)

    duration = time.time() - start_time
    print(f"\n✅ 인덱싱 완료! (소요 시간: {duration:.2f}초)")

if __name__ == "__main__":
    main()
