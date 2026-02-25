# Instagram 크롤링 리서치

## 배경

`mdh collect` 커맨드의 첫 번째 소스로 Instagram을 선택. 개인 기록 보존(디지털 아카이빙) 목적.

## 라이브러리 비교

| | instaloader | instagrapi |
|---|---|---|
| 방식 | 웹 엔드포인트 리버스엔지니어링 | 모바일 private API |
| 읽기전용 | O | X (쓰기도 가능) |
| 밴 리스크 | 낮음 | 높음 |
| 유지보수 | 활발 (v4.15, 2025.11) | 활발 |
| 2FA | interactive_login()으로 자동 처리 | 지원 |
| 설치 | `pip install instaloader` | `pip install instagrapi` |

### 결론: instaloader 채택

- 읽기 전용 — 쓰기 API에 의한 밴 리스크 없음
- 세션 자동 관리 — `~/.config/instaloader/` 에 세션 저장
- 충분한 기능 — 프로필, 게시글, 릴스, 스토리, 하이라이트 모두 지원

## 접근 가능 데이터 (2026년 기준)

| 데이터 | 로그인 없이 | 로그인 시 |
|--------|:-:|:-:|
| 프로필 (소개, 이름, 사진) | 제한적 | O |
| 게시글 (사진, 캡션, 날짜) | 제한적 | O |
| 릴스 | 제한적 | O |
| 스토리 | X | O (팔로잉 필요) |
| 하이라이트 | X | O |

**참고**: 2026년 현재 익명 요청에 401 반환이 흔해 실질적으로 로그인 필수.

## instaloader 주요 API

### 인증

```python
import instaloader

L = instaloader.Instaloader()

# 방법 1: 비밀번호 로그인
L.login("username", "password")

# 방법 2: 대화형 로그인 (2FA 포함)
L.interactive_login("username")

# 방법 3: 세션 파일 로드
L.load_session_from_file("username")

# 세션 저장
L.save_session_to_file()
```

### 프로필 정보

```python
profile = instaloader.Profile.from_username(L.context, "target_user")
profile.username
profile.full_name
profile.biography
profile.mediacount
profile.followers
profile.followees
profile.profile_pic_url
profile.is_private
```

### 게시글 순회

```python
for post in profile.get_posts():
    post.shortcode         # 게시글 고유 ID
    post.date_utc          # datetime
    post.caption           # 캡션 텍스트
    post.likes             # 좋아요 수 (int 또는 -1)
    post.comments          # 댓글 수
    post.is_video          # bool
    post.video_url         # 동영상 URL (is_video일 때)
    post.url               # 이미지 URL
    post.typename          # GraphImage, GraphVideo, GraphSidecar
    post.location          # Location 객체 또는 None
    post.caption_hashtags  # list[str]
    post.caption_mentions  # list[str]

    # 캐러셀 (typename == "GraphSidecar")
    for node in post.get_sidecar_nodes():
        node.display_url
        node.is_video
        node.video_url
```

### 릴스

```python
for reel in profile.get_reels():
    reel.shortcode
    reel.video_url
    reel.video_duration     # float (초)
    reel.video_view_count   # int
```

### 스토리 & 하이라이트

```python
# 스토리 (로그인 + 팔로잉 필요)
for story in L.get_stories(userids=[profile.userid]):
    for item in story.get_items():
        item.mediaid
        item.date_utc
        item.is_video
        item.url / item.video_url

# 하이라이트
for highlight in L.get_highlights(profile.userid):
    highlight.title
    for item in highlight.get_items():
        # StoryItem과 동일 인터페이스
```

## 401 인증 오류 해결 (2026-02)

### 증상

- 세션 파일 로드 성공 (`Loaded session from ...`)
- 프로필 정보 가져오기 성공 (공개 메타데이터)
- `get_posts()`, `get_reels()` GraphQL 쿼리 → 401 "Please wait a few minutes"

### 원인

1. **instaloader의 `login()`/`interactive_login()`이 깨져 있음** (2024~)
   - HTTP 200을 받지만 `sessionid` 쿠키가 빈 값으로 저장됨
   - GitHub issues: #2487, #2610
2. **`load_session_from_file()`이 세션 유효성을 검증하지 않음**
   - 쿠키를 복원할 뿐 API 호출로 확인하지 않음
   - `is_logged_in`은 username 문자열 존재 여부만 체크

프로필은 공개 데이터라 인증 없이 접근 가능하지만, `get_posts()` GraphQL 엔드포인트는 유효한 세션 쿠키 필수.

### 해결: Playwright persistent context (2026-02 전환)

기존 `browser_cookie3` 방식은 macOS Chrome App-Bound Encryption으로 `sessionid` 읽기 불가.
`--sessionid` 수동 입력은 번거롭고 매번 DevTools를 열어야 함.

**Playwright 방식으로 전환:**
- 실제 브라우저를 열어 유저가 직접 로그인 (2FA, 캡차 자연스럽게 처리)
- `~/.mdh/browser-profile/`에 persistent context 저장 → 이후 자동 인증
- 쿠키 암호화 문제 없음 (브라우저 자체가 세션)
- 인증만 Playwright, 데이터 수집은 기존 instaloader 유지 (하이브리드)

```bash
# 첫 실행: 브라우저 창 열림 → Instagram 로그인 → Enter
mdh collect @username --browser --limit 3 -y

# 이후 실행: 자동 인증
mdh collect @username --browser -y
```

### (참고) browser_cookie3 방식의 한계

Chrome v127+(2024~)부터 macOS에서 쿠키를 App-Bound Encryption으로 보호.
`browser_cookie3`가 `csrftoken`, `ds_user_id` 등은 읽지만 `sessionid`은 복호화 불가.
instaloader의 `import_session()`도 X-CSRFToken 헤더 미설정 버그 있음.

## Rate Limiting

- instaloader는 자체 rate limiting + 429 자동 대기 기능 있음
- 추가로 `--delay` 옵션으로 요청 간 대기 시간 설정 (기본 5초)
- CDN URL은 시간이 지나면 만료 → 미디어는 발견 즉시 다운로드 필요

## 참고 링크

- https://instaloader.github.io/
- https://github.com/instaloader/instaloader
