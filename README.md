---
category: technology
created_at: '2026-02-25T00:01:14+09:00'
doc_type: tutorial
entities:
- name: OpenRouter
  type: organization
- name: OpenAI
  type: organization
- name: Ollama
  type: organization
- name: Typer
  type: technology
- name: Rich
  type: technology
- name: httpx
  type: technology
- name: Pydantic
  type: technology
related_topics:
- metadata generation
- command-line interface
- large language models
- document management
- personal knowledge management
summary: mdh(markdown heritage)는 마크다운에 담긴 기록을 AI로 정리하고 분석하는 CLI 도구입니다.
tags:
- cli
- ai
- yaml
- frontmatter
- markdown
- knowledge-management
title: mdh — markdown heritage
updated_at: '2026-02-26T00:00:00Z'
---

# mdh — markdown heritage

마크다운에 담긴 기록을 **담고**, **정리**하고, **분석**하는 CLI 도구.

일기, 노트, 위키, 회의록, 에세이 — 누군가의 생각과 경험은 마크다운 파일 속에 쌓인다. `mdh`는 외부 소스에서 기록을 수집하고, 구조를 부여하며, 흩어진 문서들 사이에서 맥락을 찾아낸다.

```
mdh collect @username --browser          # 기록을 담는다 (Instagram)
mdh process ./my-notes                   # 기록에 메타데이터를 입힌다
mdh process ./collected --vision         # 이미지까지 분석한다 (멀티모달)
mdh query ./my-notes "AI 관련 문서를 정리해줘"  # 기록을 분석한다
```

## 동작 방식

### `mdh collect` — 기록 수집

외부 소스(Instagram)에서 데이터를 수집하여 마크다운으로 보존한다. 프로필 정보, 게시글, 릴스, 스토리, 하이라이트를 마크다운 + 미디어 파일로 아카이빙한다.

```bash
# 첫 실행: 브라우저 창이 열림 → Instagram 로그인 → Enter
mdh collect @username --browser --limit 3 -y

# 이후 실행: 자동 인증 (persistent context)
mdh collect @username --browser -y
```

> **Playwright persistent context:** 로그인 상태가 `~/.mdh/browser-profile/`에 저장되어, 한번 로그인하면 이후 자동 인증됩니다. 2FA, 캡차도 브라우저에서 직접 처리합니다.

### `mdh process` — 기록 정리

마크다운 파일을 스캔하여 AI가 YAML frontmatter 메타데이터를 자동 생성한다. 제목, 태그, 카테고리, 요약, 엔티티, 관련 주제 등을 추출하여 각 문서에 구조를 부여한다.

`--vision` 옵션을 사용하면 문서에 연결된 이미지를 함께 분석하여 시각 정보까지 반영한 메타데이터를 생성한다. Instagram 게시글처럼 이미지가 핵심인 콘텐츠에 특히 유용하다.

```bash
mdh process ./my-notes           # 기본: 텍스트만 분석
mdh process ./my-notes -f        # 강제: 모든 필드 덮어쓰기
mdh process ./my-notes -s -y     # 이미 처리된 파일 건너뛰기
mdh process ./collected --vision -s -y            # 이미지 포함 분석 (멀티모달)
mdh process ./collected --vision --vision-detail high  # 고해상도 분석 (비용 증가)
```

### `mdh query` — 기록 분석

frontmatter 메타데이터를 활용한 2단계 분석. 모든 문서의 메타데이터를 먼저 훑어 관련 문서를 선별한 뒤, 선별된 문서만 전체 읽어 LLM에 보낸다. 문서가 1000개여도 API 호출은 2회.

```bash
mdh query ./my-notes                              # 컬렉션 전체 요약
mdh query ./my-notes "최근 프로젝트 진행상황은?"    # 특정 질의
mdh query ./my-notes --max-docs 5                  # 읽을 문서 수 제한
mdh query ./my-notes -o result.md                  # 결과 저장 경로 지정
mdh query ./my-notes --no-save                     # 터미널 출력만
```

**분석 흐름:**
```
Phase 1 — 카탈로그 구축 (LLM 0회)
  모든 .md 파일의 frontmatter만 읽어 메타데이터 목록 생성

Phase 2a — 문서 선별 (LLM 1회)
  카탈로그 + 질의 → 관련 문서 선택

Phase 2b — 분석/답변 (LLM 1회)
  선별된 문서 전문 + 질의 → 분석 결과 생성
```

## 설치

```bash
git clone <repo-url>
cd markdown-frontmatterer

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -e .            # 기본 설치
pip install -e ".[dev]"     # 개발 의존성 포함

mdh --help                  # 설치 확인
```

## 설정

### .env 파일 생성

```bash
cp .env.example .env
```

`.env` 파일을 열고 API 키와 설정을 입력한다:

```env
# 필수 — LLM API 키
LLM_API_KEY=your-api-key-here

# 선택 — API 엔드포인트 (기본: OpenRouter)
LLM_BASE_URL=https://openrouter.ai/api/v1

# 선택 — 사용할 모델 (기본: google/gemini-flash-1.5)
LLM_MODEL=google/gemini-flash-1.5

# 선택 — CLI 출력 언어 (en / ko, 기본: en)
MDFM_LANG=en
```

### 환경변수 전체 목록

| 환경변수 | 기본값 | 설명 |
|----------|--------|------|
| `LLM_API_KEY` | (없음, 필수) | LLM API 인증 키 |
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` | OpenAI 호환 API 엔드포인트 |
| `LLM_MODEL` | `google/gemini-flash-1.5` | 사용할 LLM 모델명 |
| `LLM_MAX_CONTENT_CHARS` | `12000` | LLM에 전송할 문서 최대 글자 수 |
| `CONCURRENCY` | `5` | 동시 LLM 요청 수 |
| `MAX_RETRIES` | `3` | 429 에러 시 재시도 횟수 |
| `VISION_MAX_IMAGES` | `5` | `--vision` 사용 시 파일당 최대 이미지 수 |
| `VISION_DETAIL` | `low` | `--vision` 기본 상세도 (`low`/`high`/`auto`) |
| `MDFM_LANG` | `en` | CLI 출력 언어 (`en` / `ko`) |

`.env` 파일 대신 환경변수로 직접 설정해도 된다:

```bash
export LLM_API_KEY=your-api-key-here
mdh process ./my-notes
```

### LLM 제공자별 설정

**OpenRouter** (기본):
```env
LLM_API_KEY=sk-or-v1-xxxx
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=google/gemini-flash-1.5
```

**OpenAI**:
```env
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

**Ollama** (로컬):
```env
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.2
```

OpenAI 호환 API라면 `LLM_BASE_URL`만 변경하면 된다.

## CLI 레퍼런스

### `mdh collect`

```bash
mdh collect <TARGET> [OPTIONS]
```

Instagram 프로필 데이터를 수집하여 마크다운으로 저장한다.

| 옵션 | 단축 | 기본값 | 설명 |
|------|------|--------|------|
| `--browser` | `-b` | off | 브라우저를 열어 Instagram 로그인 (Playwright) — 권장 |
| `--login` | `-l` | None | 로그인에 사용할 Instagram 계정 (불안정) |
| `--password` | `-p` | None | 비밀번호 (생략 시 대화형 입력, 불안정) |
| `--session` | — | None | 세션 파일 경로 |
| `--output` | `-o` | `./collected` | 출력 디렉터리 |
| `--stories` | — | off | 스토리 수집 (로그인+팔로잉 필요) |
| `--highlights` | — | off | 하이라이트 수집 (로그인 필요) |
| `--reels/--no-reels` | — | on | 릴스 수집 |
| `--limit` | `-n` | None | 최대 게시글 수 |
| `--delay` | `-d` | 5.0 | 요청 간 대기 시간(초) |
| `--yes` | `-y` | off | 확인 프롬프트 건너뛰기 |

```bash
# 예시
mdh collect @instagram --browser                  # 브라우저로 로그인
mdh collect @instagram --browser --stories        # 스토리 포함
mdh collect @instagram --browser --limit 50 -y    # 50개 제한, 확인 생략
```

**출력 구조:**
```
collected/@username/
├── _profile.md        # 프로필 정보
├── _index.md          # 전체 인덱스
├── media/             # 미디어 파일 (사진, 동영상)
├── posts/             # 게시글 마크다운
├── reels/             # 릴스 마크다운
├── stories/           # 스토리 마크다운
└── highlights/        # 하이라이트
```

### `mdh process`

```bash
mdh process <PATH> [OPTIONS]
```

마크다운 파일(또는 디렉터리)을 처리하여 YAML frontmatter를 생성한다.

| 옵션 | 단축 | 기본값 | 설명 |
|------|------|--------|------|
| `--force` | `-f` | off | 기존 frontmatter 필드를 덮어쓰기 |
| `--dry-run` | `-n` | off | 파일 수정 없이 미리보기 |
| `--concurrency` | `-c` | 5 | 동시 LLM 요청 수 |
| `--model` | `-m` | .env 설정값 | 사용할 LLM 모델 |
| `--yes` | `-y` | off | 확인 프롬프트 건너뛰기 |
| `--skip-existing` | `-s` | off | 이미 frontmatter가 있는 파일 건너뛰기 |
| `--vision` | — | off | 이미지를 AI 분석에 포함 (멀티모달) |
| `--vision-detail` | — | `low` | 이미지 분석 상세도 (`low`/`high`/`auto`) |

```bash
# 예시
mdh process ./my-notes                        # 기본 실행 (텍스트 전용)
mdh process ./my-notes -n                     # 미리보기
mdh process ./my-notes -f -c 20              # 강제 덮어쓰기 + 높은 동시성
mdh process ./my-notes -s -y                  # frontmatter 있는 파일 건너뛰기
mdh process ./my-notes -m "openai/gpt-4o-mini"  # 모델 지정
mdh process ./single-file.md                  # 단일 파일 처리
mdh process ./collected --vision -s -y        # 이미지 포함 분석
mdh process ./collected --vision --vision-detail high  # 고해상도 분석
```

**Vision 동작 방식:**
- frontmatter의 `media_files` 배열 및 본문의 `![alt](path)` 패턴에서 이미지를 자동 탐색
- 지원 포맷: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`
- 파일당 최대 5장, 20MB 초과 이미지는 자동 스킵
- 이미지 없는 파일은 자동으로 텍스트 전용 분석으로 폴백
- `detail=low`(기본): 이미지당 ~85 토큰, `high`: ~765 토큰 (GPT-4o 기준)
- 비용 예시: 5000파일 × 이미지 1-2장 × `detail=low` ≈ **$1.75** (Gemini 2.5 Flash Lite)

### `mdh query`

```bash
mdh query <PATH> [PROMPT] [OPTIONS]
```

문서 컬렉션의 frontmatter 메타데이터를 기반으로 AI 분석을 수행한다.

| 옵션 | 단축 | 기본값 | 설명 |
|------|------|--------|------|
| `--model` | `-m` | .env 설정값 | 사용할 LLM 모델 |
| `--max-docs` | — | 자동 추정 | 전체 읽기할 최대 문서 수 |
| `--output` | `-o` | `./result/mdh-query-result.md` | 결과 저장 경로 |
| `--no-save` | — | off | 파일 저장 안 함 (터미널 출력만) |
| `--yes` | `-y` | off | 확인 프롬프트 건너뛰기 |

```bash
# 예시
mdh query ./my-notes                              # 전체 컬렉션 요약
mdh query ./my-notes "AI 관련 문서를 정리해줘"     # 특정 질의
mdh query ./my-notes --max-docs 10                # 최대 10개 문서만 읽기
mdh query ./my-notes -o ./분석결과.md             # 저장 경로 지정
mdh query ./my-notes --no-save -y                 # 터미널 출력만, 확인 생략
```

### 글로벌 옵션

| 옵션 | 설명 |
|------|------|
| `--lang` | CLI 출력 언어 (`en` / `ko`). `--help` 텍스트까지 바꾸려면 `MDFM_LANG=ko` 환경변수 사용 |

```bash
mdh --lang ko process ./my-notes
MDFM_LANG=ko mdh --help
```

## 생성되는 Frontmatter

```yaml
---
title: "문서 제목"
created_at: 2024-01-15T09:00:00
updated_at: 2026-02-24T14:30:00
tags: [python, async, web-scraping]
category: technology
doc_type: note
summary: "이 문서는 ~에 대해 설명한다"
entities:
  - name: "FastAPI"
    type: "technology"
  - name: "김철수"
    type: "person"
related_topics: [web-development, api-design]
image_description: "기타를 연주하는 손 클로즈업, 노래 제목 텍스트 오버레이"  # --vision 사용 시
---
```

| 필드 | 설명 | 가능한 값 |
|------|------|-----------|
| `title` | 문서 제목 | 본문에서 추론 |
| `created_at` | 최초 생성 시점 | git log → 파일 생성시간 → 현재시간 |
| `updated_at` | 마지막 처리 시점 | 실행 시 현재 시간 |
| `tags` | 키워드 태그 | 소문자, 하이픈 구분, 3-7개 |
| `category` | 문서 분류 | `technology`, `personal`, `work`, `research`, `creative`, `reference`, `other` |
| `doc_type` | 문서 유형 | `journal`, `note`, `wiki`, `meeting_notes`, `reference`, `tutorial`, `essay`, `log` |
| `summary` | 1-2문장 요약 | 문서 언어와 동일 |
| `entities` | 주요 개체 | `person`, `organization`, `technology`, `place`, `event`, `other` |
| `related_topics` | 관련 주제 | 넓은 범위의 테마, 2-5개 |
| `image_description` | 이미지 시각 설명 (`--vision` 사용 시) | 장면, 분위기, 주요 객체 1-2문장 |

### Merge 동작

| 모드 | 동작 |
|------|------|
| 기본 (merge) | 기존 frontmatter 필드 유지, 없는 필드만 추가 |
| `--force` | 모든 필드 덮어쓰기 (`created_at` 제외) |

## 테스트

```bash
source .venv/bin/activate
pytest -v
```

## 프로젝트 구조

```
src/markdown_frontmatterer/
├── cli.py              # Typer CLI (collect, process, query 커맨드)
├── config.py           # pydantic-settings 환경 설정
├── i18n.py             # 다국어 지원 (en/ko)
├── models.py           # Frontmatter/Entity Pydantic 모델
├── collect_models.py   # Collect 데이터 모델
├── collector.py        # Instagram 수집 파이프라인
├── collect_writer.py   # Collect 마크다운 생성 + 미디어 다운로드
├── query_models.py     # Query 응답 모델 (DocumentSelection, QueryAnswer)
├── query_prompts.py    # Query 프롬프트 템플릿
├── query.py            # Query 오케스트레이터 (카탈로그→선별→분석)
├── scanner.py          # .md 파일 재귀 탐색
├── frontmatter_io.py   # frontmatter 읽기/병합/쓰기
├── llm.py              # OpenAI 호환 async LLM 클라이언트
├── prompts.py          # Process 프롬프트 템플릿
└── processor.py        # Process 오케스트레이터 (스캔→분석→병합→저장)
```

## 기술 스택

- **CLI**: Typer + Rich (progress bar, 마크다운 렌더링, 결과 테이블)
- **LLM 호출**: httpx async + Semaphore 동시성 제어 + exponential backoff 재시도
- **Instagram 수집**: instaloader + Playwright (브라우저 persistent context 인증)
- **Frontmatter 처리**: python-frontmatter
- **설정**: pydantic-settings (.env 자동 로드)
- **검증**: Pydantic v2 (Literal 타입으로 category/doc_type 값 제한)
