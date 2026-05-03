# LLM Company Wiki

`raw/` 문서 트리를 Obsidian vault 형태의 사내 위키로 빌드하는 도구입니다.

전체 흐름은 다음과 같습니다.

```text
raw/
-> preprocessed/
-> vault/
-> LLM 기반 vault 정리(refinement)
-> .wiki_build/ 리포트
```

## 설치

의존성을 설치합니다.

```bash
uv sync --extra dev
```

`.env.example`을 참고해서 `.env`를 만들고 provider 인증 정보를 넣습니다. 기본 provider는 OpenAI이고 기본 모델은 `gpt-5.4-mini`입니다.

```dotenv
LLM_WIKI_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.4-mini
```

선택적으로 Azure OpenAI나 Vertex AI도 사용할 수 있습니다.

```dotenv
LLM_WIKI_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_DEPLOYMENT=...
```

```dotenv
LLM_WIKI_PROVIDER=vertex
GOOGLE_CLOUD_PROJECT=...
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_MODEL=gemini-2.5-pro
```

## 1. `raw/`에는 무엇을 넣나

`raw/`에는 위키의 원천 자료가 되는 파일을 넣습니다. 이 트리 구조가 이후 요약 context 계층이 됩니다.

권장 구조:

```text
raw/
  level1/
    level2/
      level3/
        document.md
        document.pdf
```

예시:

```text
raw/samsung-electronics-public/
  business/
    ds/
      memory-business.md
      foundry-and-nodes.md
    dx/
      mobile-ai.md
      networks-vran-oran.md
  company/
    profile/
      overview.md
    management/
      leadership.md
```

넣을 수 있는 파일:

- Markdown, text, JSON, YAML, CSV, XML
- PDF, 이미지, Office 문서 등 binary 파일
- 위키 지식으로 변환하고 싶은 공개 자료 또는 사내 자료

주의할 점:

- `raw/`는 ground truth입니다. 생성된 `preprocessed/`, `vault/`, `.wiki_build/` 산출물을 다시 `raw/`에 넣지 마세요.
- `.DS_Store` 같은 hidden file은 자동으로 건너뜁니다.
- 사내 자료를 사용할 경우, 외부 API provider로 전송된다는 점을 반드시 인지해야 합니다.

## 2. Preprocess

실행:

```bash
uv run llm-wiki preprocess --raw raw --out preprocessed
```

삼성전자 예제만 실행:

```bash
uv run llm-wiki preprocess \
  --raw raw/samsung-electronics-public \
  --out preprocessed/samsung-electronics-public
```

동작 방식:

- `raw/`의 모든 파일을 순회합니다.
- 같은 상대 경로를 유지해서 `preprocessed/` 아래에 Markdown을 씁니다.
- 출력 확장자는 항상 `.md`입니다.
- text/Markdown 파일은 기본적으로 직접 읽습니다.
- 현재 LLM provider가 지원하는 MIME type이면 원본 파일을 LLM에 보내 Markdown 추출을 요청합니다.
- 지원하지 않는 MIME type은 docling으로 fallback합니다.
- LLM 추출이 실패해도 docling으로 fallback합니다.
- source hash가 이전과 같으면 기본적으로 건너뜁니다. 다시 처리하려면 `--force`를 사용합니다.

경로 보존 예:

```text
raw/company/profile/overview.pdf
-> preprocessed/company/profile/overview.md
```

각 preprocessed 파일에는 YAML frontmatter가 붙습니다.

```yaml
source_path: business/ds/memory-business.md
source_sha256: ...
processed_at: ...
processor: direct
mime_type: text/markdown
llm_provider: openai
fallback_used: false
```

자주 쓰는 옵션:

```bash
uv run llm-wiki preprocess --raw raw --out preprocessed --force
uv run llm-wiki preprocess --raw raw --out preprocessed --concurrency 8
uv run llm-wiki preprocess --raw raw --out preprocessed --dry-run
```

## 3. Build

실행:

```bash
uv run llm-wiki build --preprocessed preprocessed --vault vault
```

삼성전자 예제만 실행:

```bash
uv run llm-wiki build \
  --preprocessed preprocessed/samsung-electronics-public \
  --vault vault/samsung-electronics-public
```

동작 방식:

1. 계층 요약을 만듭니다.
   - level1 요약을 먼저 만듭니다.
   - level2 요약에는 부모 level1 요약이 context로 들어갑니다.
   - level3 요약에는 부모 level1, level2 요약이 context로 들어갑니다.
2. 각 preprocessed 파일에서 여러 concept page를 추출합니다.
   - LLM에는 파일 본문과 관련 계층 요약이 함께 들어갑니다.
   - LLM은 `title`, `aliases`, `tags`, `concept_type`, `confidence`, Markdown body를 구조화해서 반환합니다.
3. 초기 Obsidian Markdown 파일을 `vault/`에 씁니다.
   - 이 시점에는 같은 개념이 여러 파일에서 추출되어 `concept-2.md`, `concept-3.md`처럼 임시 중복 파일이 생길 수 있습니다.
4. LLM 기반 vault refinement가 자동으로 실행됩니다.
5. 링크를 정리하고 리포트를 씁니다.

생성되는 위키 페이지 frontmatter 예:

```yaml
title: Memory Business
aliases:
  - Samsung Memory Business
tags:
  - memory
  - semiconductor
source_paths:
  - business/ds/memory-business.md
concept_type: business
confidence: 0.94
```

## 4. Clean Up / Refine

`build`는 자동으로 refinement를 실행합니다. 이미 만들어진 vault만 다시 정리하고 싶을 때는 `refine`을 직접 실행합니다.

```bash
uv run llm-wiki refine --vault vault/samsung-electronics-public
```

동작 방식:

- vault의 모든 Markdown 페이지를 읽습니다.
- title, alias, 숫자 suffix를 기준으로 중복 후보 그룹을 찾습니다.
- 예: `young-hyun-jun.md`, `young-hyun-jun-2.md`
- 각 중복 그룹을 active LLM provider에 보내 하나의 canonical page로 병합합니다.
- `source_paths`는 코드에서 보존하므로 출처 정보가 사라지지 않습니다.
- 기존 링크를 canonical title로 다시 씁니다.
- page index를 다시 생성합니다.

중요한 정책:

- 본문 병합은 LLM 기반입니다. 단순 문자열 이어붙이기 방식이 아닙니다.
- LLM refinement가 실패하면 조용히 낮은 품질로 병합하지 않고 빌드가 실패해야 합니다.
- title과 alias는 입력 후보를 기준으로 guard가 걸려 있어, 모델이 새 식별자를 자유롭게 발명하지 못하게 합니다.

리포트:

```text
.wiki_build/reports/refine_report.md
.wiki_build/reports/unresolved_links.md
.wiki_build/reports/build_report.json
```

## 5. 전체 실행

`raw/`부터 `vault/`까지 한 번에 실행하려면 `all`을 사용합니다.

```bash
uv run llm-wiki all --raw raw --preprocessed preprocessed --vault vault
```

삼성전자 예제 전체 rebuild:

```bash
rm -rf preprocessed vault .wiki_build
uv run llm-wiki all \
  --raw raw/samsung-electronics-public \
  --preprocessed preprocessed/samsung-electronics-public \
  --vault vault/samsung-electronics-public \
  --concurrency 4 \
  --force
```

생성되는 주요 산출물:

```text
preprocessed/samsung-electronics-public/
vault/samsung-electronics-public/
.wiki_build/summaries/
.wiki_build/index/pages.json
.wiki_build/reports/
```

## 6. 단계별 내부 처리 방식

### Preprocess 내부 동작

Preprocess는 파일 단위 병렬 작업입니다.

- `raw/`를 순회합니다.
- hidden file을 건너뜁니다.
- MIME type을 감지합니다.
- direct read, LLM extraction, docling fallback 중 하나를 선택합니다.
- source metadata가 포함된 Markdown을 씁니다.

### Summary 내부 동작

Summary는 경로 계층을 기준으로 만듭니다.

- 첫 세 path level을 context hierarchy로 봅니다.
- level1 디렉터리 요약은 병렬로 생성합니다.
- level2 요약에는 부모 level1 요약이 들어갑니다.
- level3 요약에는 부모 level1, level2 요약이 들어갑니다.
- 결과는 `.wiki_build/summaries/`에 저장됩니다.

예:

```text
preprocessed/business/ds/memory-business.md
```

이 파일에서 concept page를 만들 때 사용할 수 있는 context:

```text
.wiki_build/summaries/business.md
.wiki_build/summaries/business/ds.md
```

### Concept Extraction 내부 동작

Concept extraction은 preprocessed 파일 단위 병렬 작업입니다.

각 파일마다 LLM에 들어가는 것:

- 관련 계층 요약
- source path
- Markdown body

LLM은 하나의 파일에서 여러 concept page를 반환할 수 있습니다.

예를 들어 `memory-business.md` 하나에서 다음 page들이 나올 수 있습니다.

```text
Memory Business
HBM4
Enterprise SSD
Server DDR5
AI Inference Workload
```

### Refinement 내부 동작

Refinement는 vault 전체를 기준으로 동작합니다.

- 생성된 vault page를 모두 읽습니다.
- 중복 가능성이 높은 page들을 그룹으로 묶습니다.
- 각 그룹을 LLM에 보내 canonical page 하나로 병합합니다.
- 링크를 canonical title로 다시 씁니다.
- `.wiki_build/index/pages.json`을 다시 생성합니다.

이 단계에서 다음과 같은 중복이 하나로 정리됩니다.

```text
young-hyun-jun.md
young-hyun-jun-2.md
```

### Link Resolution 내부 동작

Link resolution은 title/alias index를 만들고 모든 `[[...]]` 링크를 검사합니다.

- 알려진 alias는 canonical title로 바꿉니다.
- `Businesses` -> `Business` 같은 단순 복수형, 대소문자 차이, suffix 차이를 일부 정규화합니다.
- 그래도 못 찾는 링크는 `.wiki_build/reports/unresolved_links.md`에 남깁니다.

## 7. 자주 쓰는 명령어

```bash
# 완전 초기화 후 전체 rebuild
rm -rf preprocessed vault .wiki_build
uv run llm-wiki all --raw raw --preprocessed preprocessed --vault vault --force

# preprocess만 다시 실행
uv run llm-wiki preprocess --raw raw --out preprocessed --force

# 기존 preprocessed를 사용해 wiki build만 다시 실행
uv run llm-wiki build --preprocessed preprocessed --vault vault

# 기존 vault cleanup/refine만 다시 실행
uv run llm-wiki refine --vault vault

# API 호출 없이 구조 테스트용 mock provider 사용
uv run llm-wiki all --raw raw --preprocessed preprocessed --vault vault --provider mock
```

## 8. Git과 산출물 정책

이 repo는 공개 예제 raw만 추적합니다.

```text
raw/samsung-electronics-public/
```

생성 산출물은 git ignore 상태입니다.

```text
preprocessed/
vault/
.wiki_build/
```

이렇게 해서 사내 raw 또는 생성된 vault가 실수로 commit되는 것을 막습니다.

Codex/Gemini/opencode 같은 에이전트에서 사용할 때는 `skills/llm-wiki-builder`를 Skill wrapper로 사용하면 됩니다.

