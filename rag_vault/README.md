# RAG Vault: 지능형 지식 베이스 검색 및 챗봇

`rag_vault`는 `vault` 폴더 내의 마크다운 지식 베이스를 효율적으로 검색하고, 이를 바탕으로 인공지능 에이전트와 대화할 수 있는 RAG(Retrieval-Augmented Generation) 시스템입니다.

## 주요 특징

- **하이브리드 검색 엔진**: 
    - **FAISS**: 시맨틱 유사도 기반의 벡터 검색.
    - **BM25**: 키워드 기반의 정밀 검색.
    - **RRF (Reciprocal Rank Fusion)**: 두 검색 결과를 결합하여 최적의 순위 제공.
- **최신 임베딩 모델 지원**: Google의 최신 멀티모달 임베딩 모델인 `gemini-embedding-2`에 최적화되어 있으며, 3072차원의 고성능 벡터 임베딩을 지원합니다.
- **Agentic RAG**: LangGraph 기반의 ReAct 에이전트가 질문의 의도를 파악하여 여러 문서를 스스로 검색하고 읽으며 최적의 답변을 구성합니다.
- **실시간 UI**: Streamlit 기반의 웹 인터페이스를 통해 에이전트의 사고 과정(어떤 문서를 검색하고 읽는지)을 실시간으로 확인할 수 있습니다.

## 설치 및 설정

1. **의존성 설치**: 
   프로젝트 루트 디렉토리에서 `uv sync`를 실행합니다. `rag_vault`는 루트 워크스페이스에 통합되어 관리됩니다.
2. **환경 변수 설정**: 
   루트 폴더의 `.env` 파일에 다음 항목이 설정되어 있어야 합니다:
   - `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`
   - `VERTEX_MODEL` (예: `gemini-1.5-flash`)
   - `VERTEX_EMBEDDING_MODEL` (예: `gemini-embedding-2` 또는 `text-multilingual-embedding-002`)

## 사용 방법

### 1. 인덱싱 (Indexing)
`vault` 폴더의 문서들을 분석하여 벡터 인덱스를 생성합니다. 문서가 추가되거나 변경된 경우 실행해야 합니다.
```bash
uv run ingest.py
```
*참고: `gemini-embedding-2` 모델 사용 시 배치 처리를 지원하지 않으므로 순차적으로 인덱싱이 진행됩니다.*

### 2. CLI 검색 (CLI Search)
터미널에서 즉시 하이브리드 검색 결과를 확인합니다.
```bash
uv run search.py "검색어"
```

### 3. 웹 챗봇 실행 (Web UI)
에이전트와 대화할 수 있는 웹 인터페이스를 실행합니다.
```bash
uv run streamlit run app.py
```

## 파일 구조

- `ingest.py`: 문서를 로드하고 FAISS/BM25 인덱스를 구축 및 저장합니다.
- `search.py`: 하이브리드 검색 로직 및 CLI 검색 인터페이스입니다.
- `agent_logic.py`: LangGraph를 이용한 지능형 에이전트의 사고 흐름을 정의합니다.
- `tools.py`: 에이전트가 사용하는 도구(문서 검색, 문서 읽기)를 정의합니다.
- `app.py`: Streamlit 기반의 채팅 인터페이스 및 이벤트 스트리밍 로직입니다.
- `utils.py`: 모델 및 임베딩 설정을 통합 관리합니다.
