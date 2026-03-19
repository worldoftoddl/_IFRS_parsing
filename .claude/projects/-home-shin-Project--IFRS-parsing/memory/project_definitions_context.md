---
name: 용어 정의를 LLM 자동 컨텍스트로 제공
description: 용어 정의를 벡터DB 청크가 아닌 tool docstring/자동 컨텍스트 방식으로 LLM에 제공하는 전략
type: project
---

용어의 정의는 벡터DB에 청킹하는 것이 아니라, LLM이 기준서 검색 시 자동으로 읽는 컨텍스트로 제공한다. MCP 서버의 tool description이나 system prompt처럼 작동하게 한다.

**Why:** 벡터DB 검색은 유사도 기반이라 정의 텍스트가 검색 결과에 안 올라올 수 있음. 반면 tool docstring 방식이면 LLM이 검색 전에 용어를 이미 이해한 상태로 쿼리 가능.

**How to apply:** 2단계 파이프라인에서 definitions 섹션은 벡터DB 청크와 분리하여, 검색 tool의 context/description으로 자동 주입되도록 설계한다.
