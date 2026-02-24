# Python 비동기 프로그래밍 가이드

Python의 asyncio를 사용한 비동기 프로그래밍에 대해 알아봅니다.

## async/await 기본

```python
import asyncio

async def fetch_data():
    await asyncio.sleep(1)
    return {"result": "data"}
```

## httpx로 비동기 HTTP 요청

httpx 라이브러리를 사용하면 async HTTP 클라이언트를 쉽게 만들 수 있습니다.

김철수 선배가 추천한 패턴입니다.
