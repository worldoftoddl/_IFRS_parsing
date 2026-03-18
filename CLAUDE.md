# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

K-IFRS(한국채택국제회계기준) 원문 .docx 파일을 파싱하여 벡터 DB용 청크로 변환하기 위한 소스 데이터 저장소. 실제 파싱 파이프라인과 검색 엔진 코드는 `/home/shin/Study/_database/`에 위치한다.

## 저장소 구조

```
IFRS_docx/
├── IAS_10XX/       ← IAS 계열 (IASC 발행 기준서) — 25개
├── IFRS_11XX/      ← IFRS 계열 (IASB 발행 기준서) — 16개
├── SIC_20XX/       ← SIC 해석서 (IASC 해석위원회) — 4개
├── IFRIC_21XX/     ← IFRIC 해석서 (IASB 해석위원회) — 15개
└── 개념체계/        ← 개념체계 + 실무서 — 3개
```

- `how_to_read_IFRS.md` — IFRS 기준서의 3단 구조(Part A/B/C), IAS 8 해석 위계, 권위 수준(authority level) 분류, K-IFRS 고유 특수성, 벡터 DB 메타데이터 설계 권고를 정리한 핵심 참조 문서

## K-IFRS 번호 체계 (2×2 매트릭스)

첫째 자리가 기준서(1) vs 해석서(2), 둘째 자리가 구(舊)기구(0) vs 신(新)기구(1)를 구분한다.

|  | 구(舊) IASC (~2000) | 신(新) IASB (2001~) |
|---|---|---|
| **기준서** | 제**10**XX호 (IAS) | 제**11**XX호 (IFRS) |
| **해석서** | 제**20**XX호 (SIC) | 제**21**XX호 (IFRIC) |

IAS와 IFRS는 체계 설계 철학이 다르다. IAS는 선택적 회계처리를 폭넓게 허용, IFRS는 선택지를 줄이는 방향. 문서 구조(부록 편제, AG 분량 등)도 상당히 다를 수 있어 파서 설계 시 감안 필요.

## 핵심 도메인 지식

### 권위 수준 5단계 (벡터 DB 메타데이터 설계 기준)

| Level | 구성요소 | 검색 우선순위 |
|-------|---------|-------------|
| 1 (Authoritative) | 기준서 본문, 부록A(정의), 부록B(적용지침), 부록C(경과규정), IFRIC/SIC 해석서 | 최상위 |
| 2 (Quasi-authoritative) | IFRIC 안건결정 | 상위 |
| 3 (Framework) | 개념체계 | 중위 |
| 4 (Non-authoritative) | 결론도출근거(BC), 적용사례(IE), 이행지침(IG) | 하위 |
| 5 (External) | US GAAP, Big 4 출판물 | 최하위 |

### 권위 수준 자동 태깅 기준 (K-IFRS 한국어 표현)

.docx 파일 내에서 아래 패턴을 정규식 매칭하여 `authority_level` 메타데이터를 기계적으로 분류할 수 있다.

| K-IFRS 한국어 표현 | 영문 원문 | 판정 |
|---|---|---|
| **"이 부록은 이 기준서의 일부를 구성한다"** | "integral part of the Standard" | **Authoritative (Level 1)** |
| **"이 기준서의 다른 부분과 동등한 권위를 지니고 있다"** | "equal authority" | **Authoritative 확인** |
| **"이 기준서의 일부를 구성하는 것은 아니다"** | "not part of the Standard" | **Non-authoritative (Level 4)** |
| **"모든 문단에는 동등한 권위가 부여되어 있다"** | "All paragraphs have equal authority" | **서문 포괄 선언** |

실제 검색 결과: 긍정 표현 45건, 부정 표현 88건 확인됨.

### K-IFRS 고유 요소

- "한" 접두어 문단(예: 한82.1): 한국 고유 추가 요구사항 (carve-in). `is_korean_addition` 메타데이터로 태깅
- K-IFRS는 IFRS를 무수정 번역 채택, carve-out 없음. 추가 표시·공시 요구사항만 존재
- 이중 질의회신 체계: 권위 순서 KASB 정규 > KASB 신속 > FSS 질의회신

## .docx 파일 접근 시 유의사항

- .docx 내부 경로가 Windows 스타일 백슬래시 (`word\document.xml`)로 되어 있음. `zipfile`로 열 때 경로 구분자 처리 필요
- 파일명에 한글·괄호·공백이 포함되어 있어 shell 명령어 시 이스케이프 필요

## 관련 프로젝트

파싱 파이프라인, 임베딩, 검색 코드: `/home/shin/Study/_database/`
