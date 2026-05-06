# RAG Vault Search

이 폴더는 `vault` 폴더 내의 마크다운 문서들을 검색하기 위한 RAG(Retrieval-Augmented Generation) 기능을 제공합니다. `rag-agent`의 로직을 기반으로 구현되었습니다.

## 설치 및 설정

1. **환경 변수 설정**:
   `rag-agent/.env.example`을 참고하여 이 폴더(`rag_vault`) 또는 프로젝트 루트에 `.env` 파일을 생성하고 필요한 API 키를 입력하세요.

2. **의존성 설치**:
   프로젝트 루트에서 `uv sync`가 완료된 상태여야 합니다.

## 사용 방법

### 1. 인덱싱 (Indexing)
`vault` 폴더의 문서들을 벡터 인덱스로 변환합니다.
```bash
uv run ingest.py
```

### 3. UI 실행 (Streamlit)
웹 브라우저에서 챗봇 인터페이스를 사용합니다.
```bash
uv run streamlit run app.py
```

## 구조
- `ingest.py`: `vault` 폴더의 문서를 로드하여 FAISS 및 BM25 인덱스 생성.
- `search.py`: 생성된 인덱스를 사용하여 하이브리드 검색 수행.
- `utils.py`: 모델 및 임베딩 설정.
