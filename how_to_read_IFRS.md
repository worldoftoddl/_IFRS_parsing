# IFRS 기준서 구조와 회계기준 해석 위계 완전 가이드

IFRS 기준서는 **본문·부록(A/B/C)은 동등한 권위(authoritative)** 를 갖고, **적용사례(IE)·결론도출근거(BC)는 비권위적(non-authoritative)** 참고자료로 명확히 구분된다. IAS 8 문단 7~12가 정하는 해석 위계는 ① 해당 기준서 본문+적용지침+해석서 → ② 유사 기준서 유추 적용 → ③ 개념체계 → ④ 타 기준제정기구 문헌 순이며, 이 위계가 벡터 DB 청킹 시 권위 수준(authority level) 메타데이터의 핵심 설계 기준이 된다. K-IFRS는 IFRS를 무수정 번역·채택하되, 영업손익 표시 등 한국 고유 추가사항("한" 문단)과 이중 질의회신 체계(KASB·FSS)가 존재한다.

---

## 1. 개별 IFRS 기준서의 3단 구조

IFRS Foundation은 각 기준서를 **Part A(기준서 본체)**, **Part B(수반 지침)**, **Part C(결론도출근거)** 의 3단으로 편제한다. 각 기준서 서문(rubric)은 "All the paragraphs have equal authority"라고 명시하며, 어떤 문단과 부록이 기준서의 일부인지를 정의한다.

### Part A — 기준서 본체(Authoritative)

| 구성요소 | 역할 | 권위 수준 |
|---------|------|----------|
| **본문(Standard Text)** | 목적·범위·인식·측정·표시·공시 요구사항. 굵은 글씨 문단이 핵심 원칙, 일반 문단이 상세 요구사항 | **Authoritative** — 모든 문단 동등 권위 |
| **부록A: 용어 정의(Defined Terms)** | 기준서에서 사용하는 용어의 정의. 첫 사용 시 이탤릭 표시 | **Authoritative** — "integral part of the Standard" |
| **부록B: 적용지침(Application Guidance)** | 기준서 요구사항의 구체적 적용 방법. 복잡한 기준서(IFRS 9, 15, 16, 17)에서는 본문보다 분량이 많음 | **Authoritative** — "integral part of the Standard", 본문과 동등 권위 |
| **부록C: 경과규정(Effective Date & Transition)** | 시행일, 경과 조치, 타 기준서 수정사항 | **Authoritative** — "integral part of the Standard" |
| **부록D 이하(해당 시)** | 추가 의무 지침(예: IFRS 1의 면제 규정) | **Authoritative** — "integral part of the Standard" |

**핵심 원칙**: IAS 8은 "Guidance that is an integral part of the IFRSs is mandatory"라고 명시한다. 부록에 "This appendix is an integral part of the Standard"라는 문구가 있으면, 해당 부록은 본문과 완전히 동등한 구속력을 갖는다. 적용지침(AG) B1, B2… 문단은 본문 1, 2… 문단과 동일한 권위 수준이다.

### Part B — 수반 지침(Non-authoritative)

**적용사례(Illustrative Examples, IE)** 는 기준서의 적용 양상을 예시하지만 "해석적 지침을 제공하려는 것이 아니다(not intended to provide interpretative guidance)"라고 명시된다. 실무에서 자신의 해석이 IASB의 의도와 부합하는지 검증하는 데 널리 활용되지만, 법적 요구사항을 생성하지 않는다. "IE에 예시된 것과 다른 접근법으로도 기준서를 준수할 수 있다"는 점이 중요하다.

**이행지침(Implementation Guidance, IG)** 역시 "integral part"로 명시되지 않는 한 비권위적이다. IAS 8 결론도출근거는 "The term 'Appendix' is retained only for material that is part of an IFRS"라고 구분한다.

### Part C — 결론도출근거(Non-authoritative)

**결론도출근거(Basis for Conclusions, BC)** 는 IASB가 특정 결정에 이른 논리적 근거, 검토했으나 기각한 대안, 정책적 배경을 설명한다. "BC cannot override requirements in the Standard"라고 명시되어 있으며, 본문과 BC가 충돌하면 본문이 우선한다. 그러나 각 기준서의 rubric은 "The Standard should be read **in the context of** the Basis for Conclusions"라고 하여, 해석의 맥락적 참고자료로서의 역할을 공식 인정한다. **반대의견(Dissenting Opinions)** 도 Part C에 포함되며 비권위적이다.

---

## 2. IAS 8이 규정하는 해석 위계

IAS 8 "회계정책, 회계추정의 변경 및 오류" 문단 7~12는 IFRS 해석의 **공식 위계(hierarchy)** 를 정한다. IFRS Foundation이 2019년 11월 발간한 "Guide to Selecting and Applying Accounting Policies—IAS 8"은 이를 3단계 의사결정 흐름으로 정리한다.

### 1단계: 해당 기준서가 직접 적용되는 경우 (IAS 8.7)

거래에 직접 적용되는 IFRS가 존재하면, 해당 기준서(본문 + 적용지침)와 관련 이행지침을 적용한다. **개념체계와 충돌하더라도 개별 기준서가 우선한다.** 개념체계 자체가 문단 SP1.2에서 "Nothing in the Conceptual Framework overrides any Standard or any requirement in a Standard"라고 확인한다.

IAS 8.5에 의해 "IFRS"의 정의에는 IFRS(1~18호), IAS(1~41호), **IFRIC 해석서**, **SIC 해석서**가 모두 포함된다. IAS 8 결론도출근거는 "The Board decided not to rank Standards above Interpretations"라고 명시하여, **해석서와 기준서는 동등한 지위**를 갖는다.

### 2단계: 직접 적용되는 기준서가 없는 경우 (IAS 8.10~11)

직접 적용되는 IFRS가 없을 때, 경영진은 **반드시(shall)** 다음 출처를 **하향 순서(in descending order)** 로 참조하여 회계정책을 개발해야 한다:

**(a) 유사하고 관련된 사안을 다루는 IFRS 기준서의 요구사항** — 유추 적용(analogy). 2019년 IFRS Foundation 가이드는 "At the top of the hierarchy are the requirements in IFRS Standards dealing with similar and related issues"라고 확인한다. 유추 적용 시에는 공시 요구사항을 포함한 해당 기준서의 **모든 적용 가능한 측면**을 고려해야 한다.

**(b) 개념체계(Conceptual Framework)의 자산·부채·수익·비용에 대한 정의, 인식기준, 측정개념** — (a)에서도 유사 기준서를 찾을 수 없는 경우에만 적용된다.

### 3단계: 임의적 참고 (IAS 8.12)

경영진은 **선택적으로(may also consider)** 다음을 참고할 수 있다:

- 유사한 개념체계를 사용하는 **타 기준제정기구의 최근 공표물** (예: US GAAP/FASB ASC)
- **기타 회계문헌**
- **인정된 산업관행**

단, 이들은 2단계 출처(IAS 8.11)와 **충돌해서는 안 된다.** IAS 8 결론도출근거는 "The Board decided that considering such pronouncements is voluntary"라고 명시하며, 이는 응답자들이 US GAAP 전체를 검토해야 하는 부담을 우려했기 때문이다.

### IFRIC 안건결정(Agenda Decisions)의 특수한 위치

IFRIC 안건결정은 기술적으로 IFRS가 아니며 공식 면책 조항이 붙는다. 그러나 실무에서는 **사실상 준권위적(quasi-authoritative)** 지위를 갖는다. 전직 IFRIC 의장은 "many regulators see our agenda decisions as quasi-authoritative and accounting firms consider them to be 'in-substance mandatory'"라고 언급했으며, ESMA·FRC 등 규제기관이 집행 조치에서 안건결정을 참조한다. Big 4 회계법인은 안건결정을 내부 지침에 반영하고, KASB도 이를 번역·공표한다.

---

## 3. 권위적(Authoritative) vs 비권위적(Non-authoritative) 완전 분류

벡터 DB 메타데이터 설계의 핵심인 권위 수준 분류를 체계화하면 다음과 같다.

| 권위 수준 | 구성요소 | 근거 | 벡터 DB 우선순위 |
|-----------|---------|------|----------------|
| **Level 1: Authoritative (의무)** | 기준서 본문, 부록A(정의), 부록B(적용지침), 부록C(경과규정), IFRIC/SIC 해석서 | 각 기준서 rubric "integral part", IAS 8.5·8.7 | **최상위** — 항상 최우선 반환 |
| **Level 2: Quasi-authoritative** | IFRIC 안건결정(Agenda Decisions) | Due Process Handbook; 규제기관·Big 4 실무 | **상위** — Level 1과 함께 반환 |
| **Level 3: Framework** | 개념체계(Conceptual Framework) | IAS 8.11(b); CF SP1.2 "기준서를 override 불가" | **중위** — Level 1 매칭 없을 때 또는 보조 맥락 |
| **Level 4: Non-authoritative (참고)** | 결론도출근거(BC), 적용사례(IE), 비의무 이행지침(IG) | 각 rubric "not part of the Standard" | **하위** — 보충 맥락으로 반환, 비권위 명시 |
| **Level 5: External** | US GAAP(ASC), Big 4 출판물, 산업관행 | IAS 8.12 "may also consider" | **최하위** — 요청 시 또는 IFRS 결과 부족 시 |

**IAS 8의 공식 표현**: "Guidance that is an integral part of the IFRSs is mandatory. Guidance that is not an integral part of the IFRSs does not contain requirements for financial statements." 이 한 문장이 authoritative/non-authoritative 구분의 법적 근거다.

**IFRS Practice Statements**(예: Practice Statement 2 "Making Materiality Judgements")는 IAS 8.5 주석에서 "It is not a Standard. Therefore, its application is not required to state compliance with IFRS Standards"로 비의무임을 확인한다.

---

## 4. 실무에서 CPA가 기준서를 해석하는 8단계 절차

특정 거래의 회계처리를 결정할 때, 실무자가 따르는 단계적 절차를 정리한다. 이 절차는 IAS 8 위계를 실무적으로 구현한 것이다.

**1단계 — 거래의 경제적 실질 파악 및 해당 기준서 식별.** 법적 형식이 아닌 경제적 실질에 기초하여 거래를 분류하고, 어떤 기준서의 적용범위(scope)에 해당하는지 판단한다. 각 기준서의 범위 문단과 범위 제외 조항을 꼼꼼히 확인한다.

**2단계 — 기준서 본문(Standard Text) 정독.** 굵은 글씨의 핵심 원칙과 일반 문단의 상세 요구사항을 모두 검토한다. 인식·측정·표시·공시 요구사항을 확인하고, 본문에 내장된 타 기준서 참조(cross-reference)를 메모한다.

**3단계 — 적용지침(Application Guidance, Appendix B) 검토.** 본문과 동등한 권위를 가지므로 반드시 함께 읽어야 한다. IFRS 15의 경우 본문보다 적용지침 분량이 훨씬 크며, 실질적인 적용 판단 기준(indicators, factors)이 여기에 집중되어 있다.

**4단계 — IFRIC/SIC 해석서 및 안건결정 확인.** 해당 이슈를 다루는 IFRIC 해석서가 있는지 확인하고, IFRS Foundation이 기준서별로 정리·공표하는 **누적 안건결정(Cumulative Agenda Decisions)** 을 검토한다.

**5단계 — 직접 적용 기준서가 없으면 IAS 8 위계 적용.** 유사·관련 기준서의 요구사항을 유추 적용하고, 그래도 부족하면 개념체계를 참조한다.

**6단계 — BC·IE를 보충 참고자료로 활용.** BC는 IASB가 특정 요구사항을 채택한 이유, 기각한 대안, 정책적 배경을 담고 있어 **본문의 모호함을 해소**하는 데 핵심적이다. IE는 자신의 해석이 IASB 의도와 부합하는지 **교차 검증**하는 데 활용된다. 기술적 메모(position paper)에서 "BC4.111~BC4.120에서 논의된 바와 같이…"와 같이 인용하는 것이 일반적 관행이다.

**7단계 — 타 기준제정기구 문헌 참고.** US GAAP(ASC)이 가장 빈번히 참조되며, IAS 8.11의 출처와 충돌하지 않는 범위에서만 가능하다.

**8단계 — 기술적 메모 작성 및 문서화.** Big 4 회계법인의 표준 기술적 메모 구조는 이슈 기술 → 관련 사실 → 적용 기준서(문단 번호 특정) → 분석·대안 검토 → 결론 → 정량적 영향 → 분개 → 검토·승인 순이다. 본문·AG 문단은 의무 근거로, BC·IE는 보충 근거로 인용한다.

---

## 5. K-IFRS의 구조적 특수성

### 무수정 번역 채택 원칙과 한국 고유 추가사항

K-IFRS는 IFRS를 **무수정 번역(without modification)** 하여 채택한다. KASB와 IFRS Foundation 간 저작권 계약은 "번역자는 기준서의 실질과 내용을 어떠한 방식으로도 추가·축소·변경할 수 없다"고 규정한다. 한국에는 **carve-out(삭제·수정)이 전혀 없으며**, 대신 IFRS를 초과하는 **추가 표시·공시 요구사항(carve-in)** 이 존재한다. IFRS Foundation은 이를 "Such additions do not otherwise affect the jurisdiction's full compliance with IFRS Accounting Standards"라고 확인한다.

주요 한국 고유 추가사항은 다음과 같다:

- **영업손익(Operating Profit/Loss) 표시 의무** — K-IFRS 1001호에 "한82.1" 등 "한" 접두어 문단으로 추가. 원래 IAS 1은 영업이익 소계를 의무화하지 않았으나, 한국 자본시장의 오랜 관행을 반영하여 재무제표 본문 표시를 요구
- **이익잉여금처분계산서** — 상법 요구사항과의 정합성
- **전환사채 리픽싱(refixing) 조항 관련 추가 공시** — 한국 자본시장 특유의 전환사채 구조 반영
- **암호자산 추가 공시** — 보유자·수탁자·발행자의 중요 정보 공시
- **수익인식(K-IFRS 1115호) 투입법 관련 추가 공시** — 계약별 공시 포함
- **영업부문 추가 공시** — IFRS 8 초과 세부 공시

### 번호 체계와 "한" 문단

K-IFRS는 독자적 번호 체계를 사용한다: **IAS XX → K-IFRS 제10XX호**, **IFRS XX → K-IFRS 제11XX호**, **SIC XX → K-IFRS 제20XX호**, **IFRIC XX → K-IFRS 제21XX호**. 한국 고유 추가 문단에는 **"한" 접두어**(예: 한82.1)가 붙어 IFRS 원문 번역 문단과 시각적으로 구분된다. 벡터 DB 설계 시 이 "한" 문단을 별도 메타데이터로 태깅하면, 한국 고유 요구사항만 필터링하여 검색할 수 있다.

### 이중 질의회신 체계

한국에는 **KASB 질의회신**과 **FSS 질의회신**의 이중 해석 체계가 존재한다. KASB 질의회신은 금융위원회로부터 위임받은 공식 해석이지만, 회계기준(기업회계기준) 자체는 아니며 회계기준위원회의 정식 심의를 거치지 않는다. KASB 내에는 정규 질의회신(질의회신위원회 심의)과 **신속처리 질의회신**(개별 연구원 의견, KASB 공식 입장이 아닐 수 있음)이 구분된다. FSS 질의회신은 특정 사실관계에 기초한 감독 의견으로 "일반화된 지침으로 사용할 수 없다"는 면책이 붙는다. 벡터 DB에서 질의회신을 포함할 경우, **KASB 정규 > KASB 신속 > FSS 질의회신** 순으로 권위 수준을 차등 태깅해야 한다.

---

## 6. 벡터 DB 청킹을 위한 메타데이터 설계 권고

위 조사 결과를 종합하여, IFRS/K-IFRS 벡터 DB 청킹 시 각 청크에 부여할 메타데이터 스키마를 제안한다.

```
{
  "chunk_id": "IFRS15-B34-001",
  "standard_number": "IFRS 15" / "K-IFRS 1115",
  "component_type": "core_text | application_guidance | defined_terms | 
                     transition | illustrative_examples | basis_for_conclusions |
                     ifric_interpretation | agenda_decision | conceptual_framework |
                     kasb_qa | fss_qa",
  "authority_level": 1~5,
  "paragraph_ref": "B34-B38",
  "is_korean_addition": true/false,   // "한" 문단 여부
  "topic_tags": ["revenue", "performance_obligations"],
  "cross_references": ["IFRS15.22-30", "IFRS15.IE-Example5"],
  "effective_date": "2018-01-01",
  "last_amended": "2020-06-01"
}
```

**검색 우선순위 로직**: 쿼리 수신 시 ① Level 1(본문+AG+해석서) 최우선 검색 → ② Level 2(안건결정) 병행 반환 → ③ Level 1 매칭 부족 시 Level 3(개념체계) 확장 → ④ 연결된 BC/IE를 보충 맥락으로 반환(비권위 명시) → ⑤ 외부 문헌은 명시적 요청 시에만 반환. 모든 반환 결과에 `authority_level`을 포함시켜, LLM이 "IFRS 15.B58 [mandatory]에 따르면…" vs "결론도출근거 BC273 [non-authoritative]에서 시사하는 바…"와 같이 **권위 수준을 구분하여 응답을 생성**할 수 있도록 해야 한다.

**청킹 단위**: 고정 길이가 아닌 **논리적 의미 단위**(단일 개념을 다루는 문단 그룹)로 청킹하되, 문단 중간에서 분할하지 않아야 한다. 문단 번호를 반드시 보존하고, 기준서 간 상호 참조(cross-reference)를 메타데이터 배열과 별도 그래프 인덱스로 관리하면 다중 홉(multi-hop) 검색이 가능해진다.

---

## 결론: 설계 원칙 세 가지

첫째, **"integral part" 문구가 권위의 경계선**이다. 이 문구가 있는 부록은 본문과 동등한 Level 1, 없는 수반 자료는 Level 4로 기계적으로 분류할 수 있어 메타데이터 자동 태깅의 기준이 된다. 둘째, **IAS 8 위계는 검색 확장(query expansion)의 로직 그 자체**다. 직접 적용 기준서 → 유사 기준서 유추 → 개념체계로 확장하는 3단계는 벡터 DB의 fallback 검색 전략과 정확히 일치한다. 셋째, **K-IFRS 고유 요소("한" 문단, KASB/FSS 질의회신)는 별도 메타데이터 차원으로 관리**해야 한국 맥락의 정밀 검색과 글로벌 IFRS 원문 검색을 동시에 지원할 수 있다. 이 세 가지 원칙을 지키면, 권위 수준에 기반한 정확하고 신뢰할 수 있는 회계기준 RAG 시스템을 구축할 수 있다.