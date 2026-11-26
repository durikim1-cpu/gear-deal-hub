# GearCompare Hub — 무자본(0원) 글로벌·국내 제휴 수익화 전략 및 에이전트 인수인계 문서

> **For AI Coding & Operations Agents (Claude Code, Gemini, Codex, Antigravity, Cursor):**
> 이 문서는 본 저장소(`gear-deal-hub`)의 비즈니스 수익 구조, 현재 개통 완료된 제휴/채널 자산, 남은 작업, 그리고 향후 AI 에이전트가 코드를 고도화하거나 자동 운영할 때 반드시 지켜야 할 전략·제약사항을 정의합니다. 작업 전 본 문서를 먼저 읽고 맥락을 유지하세요.

---

## 1. 핵심 비즈니스 전제: 왜 단순 '가격비교 사이트'가 아니라 '브릿지 + 푸시 스나이퍼'인가?

1. **냉정한 시장 현실 (Pull의 한계):**
   - 이미 살 제품을 정한 한국 소비자는 다나와·네이버쇼핑으로 가기 때문에, 개인이 만든 정적 시세 사이트만 덩그러니 띄워두면 자연 유입만으로 수익이 나지 않는다.
2. **실제로 돈이 찍히는 구조 (Push + Bridge + 24시간 장바구니 쿠키):**
   - **24시간 장바구니 효과:** 유저가 내 제휴 링크를 클릭해 쿠팡·아마존·알리에 진입하면 해당 상품을 안 사더라도 **24시간(또는 세션 쿠키 기간) 이내 결제하는 모든 생필품·가전 금액의 수수료(쿠팡 3%, 아마존 2.5~4%, 알리 4~9%)**가 정산된다.
   - **양자택일 가두리 UI:** 단일 링크만 걸면 "비싸네" 하고 이탈하지만, 글로벌 공통 모델(소형 IT·데스크 기어)에 대해 **`[빠른 배송·AS (쿠팡/아마존)] vs [직구 최저가 (알리)]`** 두 버튼을 나란히 배치하면 급한 유저와 알뜰한 유저 중 어느 쪽을 클릭해도 수익으로 연결된다.
   - **본진 웹사이트의 진짜 역할 2가지:**
     1. 쿠팡 파트너스 · 알리익스프레스 포털 · 아마존 어소시에이트 **가입 심사 및 API 발급을 통과하는 정식 간판**
     2. 쓰레드·X·핀터레스트·레딧 등에서 제휴 단축링크 직접 도배 시 걸리는 **스팸 차단(섀도우밴)을 우회하는 고신뢰 브릿지 랜딩페이지**
   - **실제 트래픽을 물어오는 쌍발 엔진 (전략 A + 전략 B):**
     - **전략 A (국내·글로벌 실시간 핫딜·할인코드 스나이퍼):** 다나와가 반영하지 못하는 **알리 프로모션 코드·코인딜·역대가** 신호를 실시간 포착해 텔레그램 직격 알림 및 쓰레드/X 2단 포스트(본문 무링크 + 첫 답글 브릿지 링크)로 푸시한다.
     - **전략 B (해외 핀터레스트 비주얼 검색 자동화):** 다나와 같은 통합 직구 비교표가 드문 영미권 시장을 겨냥해, `1000×1500` 세로형 가격·단점 비교 인포그래픽 PNG를 자동 생성하고 핀터레스트 공식 RSS 자동 발행으로 영문 상세 페이지(`/en/p/<slug>/`) 유입을 누적시킨다.

---

## 2. 현재 구축 및 개통 완료된 자산 현황 (2026-11-26 기준)

| 구분 | 상태 | 식별자 / URL | 비고 |
| :--- | :--- | :--- | :--- |
| **GitHub 저장소** | ✅ 운영 중 | `https://github.com/durikim1-cpu/gear-deal-hub` | 6시간 주기 GitHub Actions 무료 실행 |
| **국내 비교 허브** | ✅ 배포됨 | `https://durikim1-cpu.github.io/gear-deal-hub/ko/` | 69종 모델 · 11개 분류 · 패싯 시세표 |
| **글로벌 비교 허브** | ✅ 배포됨 | `https://durikim1-cpu.github.io/gear-deal-hub/en/` | 영문 Amazon US vs AliExpress 비교 |
| **핀터레스트 RSS** | ✅ 배포됨 | `https://durikim1-cpu.github.io/gear-deal-hub/en/pinterest-feed.xml` | `1000×1500` PNG 30종 자동 연결 피드 |
| **국내 시세 RSS** | ✅ 배포됨 | `https://durikim1-cpu.github.io/gear-deal-hub/ko/feed.xml` | 국내 자동화 연동용 RSS 2.0 |
| **텔레그램 국내 채널** | ✅ 운영 중 | `https://t.me/gearcompare_kr` (`@gearcompare_kr`) | 익명 설정 완료, 초기 시세글 게시됨 |
| **텔레그램 해외 채널** | ✅ 운영 중 | `https://t.me/gearcompare_en` (`@gearcompare_en`) | 익명 설정 완료, 초기 영문글 게시됨 |
| **텔레그램 발송 봇** | ✅ 연동됨 | `@gearcompare_hub_bot` | 토큰은 `config.local.json` 및 GitHub Secrets 저장 |
| **쿠팡 파트너스** | ✅ 승인됨 | **`AF8784203`** (`AUTO_APPROVED`) | 웹사이트·텔레그램 캡처 증빙 완료, `AFFSRP` 추적 적용됨 |
| **아마존 어소시에이트** | ✅ 발급됨 | **`gearcomparehu-20`** (미국 US) | **가입 후 180일 이내 적격 판매 3건 필수** |
| **알리익스프레스 포털** | ⏳ 심사 중 | `portals.aliexpress.com` (`2026-11-25` 제출) | 1시간~2영업일 내 메일 승인 시 `Tracking ID` 반영 필요 |
| **핀터레스트 비즈니스** | ✅ 무인 가동 중 | `https://www.pinterest.com/gearcomparehub` | 도메인 인증 완료 + `Desk & Tech Gear Deals` 보드에 RSS 자동 발행 연결 완료 |
| **GitHub Secrets** | ✅ 등록됨 | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID_KO/EN`, `COUPANG_PARTNERS_ID`, `AMAZON_ASSOCIATE_TAG` | 추후 `ALIEXPRESS_TRACKING_ID` 등만 추가 |

---

## 3. 남은 후속 작업 체크리스트 (우선순위순)

### [즉시 완료 가능 — 5분]
1. **최신 로컬 커밋 GitHub 푸시:**
   ```powershell
   cd C:\Users\user\.gemini\antigravity\scratch\gear-deal-hub
   git push origin main
   ```
   *(이 푸시 한 번으로 쿠팡 `AF8784203` 정식 추적 링크, 아마존 `gearcomparehu-20` 태그, 핀터레스트 인증 메타태그 `c942f8f94af69430d13208288ac28bf9`가 실제 배포 사이트에 동시에 반영됨)*
2. **핀터레스트 웹사이트 소유권 확인 & RSS 무인 자동 발행 연결:**
   - 푸시 약 1분 뒤 `https://kr.pinterest.com/settings/claim/` → 웹사이트 **소유권 표시(Claim)** → `HTML 태그 추가` 계속 → 사이트 주소 입력 후 확인 클릭.
   -*(참고: 만약 핀터레스트 서버가 하위 경로 `/gear-deal-hub` 대신 루트 도메인 `https://durikim1-cpu.github.io/` 에만 메타태그를 요구할 경우, GitHub에 `durikim1-cpu.github.io` 이름의 공개 저장소 하나를 만들고 `<meta name="p:domain_verify" content="c942f8f94af69430d13208288ac28bf9">`가 들어간 `index.html` 1개만 올리면 루트 도메인 전체 소유권이 즉시 통과됨!)*
   - 소유권 통과 직후 `https://kr.pinterest.com/settings/bulk-create-pins/` (`자동 게시 → RSS 피드 연결`)에 `https://durikim1-cpu.github.io/gear-deal-hub/en/pinterest-feed.xml` 등록 → 하루 최대 수십 개 비교 핀이 영구 무인 발행됨.
3. **구글 서치콘솔(`search.google.com/search-console`) 사이트맵 제출:**
   - URL 접두어(`https://durikim1-cpu.github.io/gear-deal-hub/`) 등록(HTML 태그 인증 시 동일하게 `_head`에 메타태그 1줄 추가 가능) 후 `sitemap.xml` 제출 → 164개 페이지(69개 모델 상세 + 22개 분류 시세표) 검색 색인 시작.

### [알리 승인 메일 도착 후 — 5분]
4. **알리익스프레스 `Tracking ID` 및 공식 API 연결:**
   - `durikim1@snu.ac.kr`로 승인 메일이 오면 `portals.aliexpress.com` → `Settings → Tracking ID`에서 ID 확인(예: `default` 또는 `gearhub`).
   - `config.local.json`, `config.example.json`, GitHub Secrets(`ALIEXPRESS_TRACKING_ID`)에 등록.
   - `Portals Open Platform`에서 무료 API Key(`AppKey`, `AppSecret`)를 발급받으면 `src/affiliate.py` 및 `src/collector.py`에 실시간 할인가·딥링크(`s.click.aliexpress.com`) 자동 변환기를 붙일 수 있음.

---

## 4. 코드 아키텍처 맵 (AI 에이전트 작업 가이드)

```text
gear-deal-hub/
├── run_pipeline.py          # 통합 실행 엔트리: 수집 -> 증식 -> 검수 -> 웹빌드 -> 핀터레스트 PNG/RSS -> 핫딜 스나이퍼/발송
├── config.example.json      # 공개 설정 템플릿 (절대 비밀 토큰 기입 금지)
├── config.local.json        # 로컬 전용 비밀 설정 (.gitignore 처리됨 — 봇 토큰 포함)
├── data/
│   ├── products.json        # 검수 통과 마스터 상품 DB (현재 69종, 11개 카테고리)
│   ├── candidates_inbox.json# 신규 후보 입력 큐 (오매칭 차단 회귀 테스트용 샘플 1건 포함)
│   ├── discovery_queue.json # 실시간 크롤러가 포착한 미등록 글로벌 모델 후보 대기열 (런타임)
│   └── sent_deals_history.json # 7일 내 중복 알림 도배 방지 이력 (런타임)
├── src/
│   ├── collector.py         # Reddit 6개 서브레딧 JSON + 국내 핫딜 RSS(뽐뿌 국내/해외) 수집 및 신규 모델 추출
│   ├── auto_discover.py     # 신규 모델 후보를 LLM(로컬 Claude CLI 또는 무료 Gemini API)으로 정형화 후 DB 자동 증식
│   ├── verifier.py          # Gatekeeper 검수 엔진 (케이스/단품 키워드 차단, 정가 35% 미만 이상저가 차단, 단점·고지문 검증)
│   ├── affiliate.py         # 쿠팡(AFFSRP lptag) / 아마존(tag) / 알리(aff_fcid) 수익 링크 생성 및 법적 대가성 상수
│   ├── site_builder.py      # 무확장자 URL(/ko/, /en/, /ko/c/<cat>/, /ko/p/<slug>/) 고밀도 패싯 시세표 정적 빌더
│   ├── pin_generator.py     # Pillow 기반 1000x1500 비교 카드 PNG 렌더링 및 pinterest-feed.xml / ko/feed.xml 생성
│   ├── deal_sniper.py       # 프로모션 코드 정규식 추출, 7일 쿨다운 필터링, 발송 우선순위 스코어링
│   ├── social_publisher.py  # 쓰레드(Threads) 공식 무료 Graph API 2단 발행(본문 무링크 + 답글 브릿지 링크) 및 큐 생성
│   └── notifier.py          # 텔레그램 한/영 채널 알림 포맷팅 및 발송
└── .github/workflows/
    └── deploy.yml           # 6시간 주기 무인 실행 및 GitHub Pages 무료 배포 워크플로
```

### 주요 실행 명령어
- 전체 빌드 및 로컬 검증 (발송 없음):
  `python run_pipeline.py`
- 실시간 트렌드 수집 + 신규 모델 3종 자동 발굴·검수 증식 + 텔레그램 실발송:
  `python run_pipeline.py --live-network --auto-grow 3 --send-telegram`

---

## 5. 다음 AI 에이전트가 수익을 키우기 위해 고도화할 핵심 전략 5가지

다른 AI 에이전트가 본 프로젝트를 이어받아 개선할 때는 단순 디자인 수정보다 **실제 클릭률(CTR)과 구매 전환율(CVR)을 높이는 아래 5가지 작업**을 우선 수행하세요.

### 전략 1: 알리 세일 시즌 '프로모션 코드 + 카드할인 체감가' 계산기 탑재 (국내 전환율 1순위)
- 알리익스프레스는 매월 초 `초이스데이(Choice Day)`, 3월 애니버서리, 6월 썸머세일, 11월 광군제/블프마다 **공통 프로모션 코드**(예: `$39 이상 $5 할인`, `$79 이상 $10 할인`)가 풀린다.
- `data/promo_tiers.json`에 시즌별 할인코드 테이블을 넣어두면, 69개+ 전 상품의 **`코드 자동 적용 체감가`**를 계산해 다나와보다 훨씬 싼 실제 결제가와 복사 가능한 쿠폰 코드를 리스트·텔레그램·쓰레드에 즉시 찍어줄 수 있다.

### 전략 2: 아마존 '180일 내 적격 판매 3건' 조기 달성 집중 모드 (계정 유지 최우선 과제)
- 아마존 어소시에이트(`gearcomparehu-20`)는 **가입 후 180일 안에 실제 구매 전환 3건**이 발생해야 계정이 영구 유지되고 공식 PA-API 권한이 열린다.
- 이를 빠르게 넘기 위해 해외 채널(`@gearcompare_en`, 핀터레스트 RSS, 영문 X/Reddit)에서는 500달러짜리 고가 미니PC보다 **충동구매가 쉬운 20~50달러대 미국 아마존 우세/박빙 아이템**(예: `8BitDo Ultimate 2C $29.99`, `INIU 100W GaN`, `Keychron B1 Pro`, `Crucial/SK hynix SSD`) 노출 비중을 높이는 것이 유리하다.

### 전략 3: '문제 해결형 VS 비교 / 상황별 추천 가이드' 정적 페이지 확장 (`/ko/vs/...`, `/en/vs/...`)
- 개별 모델명 검색 외에 구매 직전 전환율이 가장 높은 검색어는 **비교·고민 해결 키워드**다:
  - 국내 예시: `"독거미 F75 vs F99 vs 레이니75 차이"`, `"맥북 에어 M1 M2 M3 듀얼모니터 도킹스테이션 비교"`, `"기내반입 가능한 노트북 보조배터리 100W 비교"`
  - 해외 예시: `"AULA F75 vs Keychron K2 Max"`, `"Beelink SER8 vs GMKtec K8 Plus noise & thermals"`, `"Best DisplayLink dock for base M3 MacBook"`
- 이미 `products.json`에 정형 스펙과 장단점이 다 들어 있으므로, 같은 카테고리 인기 모델 2~3개를 자동 교차 비교하는 `/ko/vs/<slug-a>-vs-<slug-b>/` 생성기를 `site_builder.py`에 추가하면 추가 크롤링 비용 없이 고전환 SEO 페이지를 수백 개로 늘릴 수 있다.

### 전략 4: 가격 변동 이력(`price_history.json`) 누적 및 '진짜 역대가' 판별
- 공식 API(알리 Portals API, 쿠팡 파트너스 API — 매출 15만 원 달성 후 발급) 연동 후 실행 시점마다 가격을 `data/price_history.json`에 기록한다.
- 최근 30일 최저가보다 가격이 떨어졌을 때만 **`[30일 최저가 경신]`** 배지를 붙여 텔레그램과 쓰레드에 즉시 발송하면 채널 구독자 충성도와 클릭률이 극대화된다.

### 전략 5: 쓰레드(Threads) · X(트위터) 무료 API 완전 무인화
- `src/social_publisher.py`에 이미 메타 공식 무료 Threads Graph API 2단 발행 로직(본문 정보 + 첫 답글 브릿지 링크)이 구현되어 있다.
- Meta for Developers에서 무료 앱 생성 후 `THREADS_USER_ID`와 장기 `THREADS_ACCESS_TOKEN`만 GitHub Secrets에 추가하면 유료 마케팅 SaaS 비용 0원으로 하루 4번 쓰레드 핫딜 계정이 자동 운영된다.

---

## 6. 절대 위반 금지 수칙 (Hard Guardrails)

1. **추가 금전 지출 0원 원칙:** 유료 서버, 유료 DB, 유료 도메인, 해외결제 카드 등록이 강제되는 유료 API를 도입하지 않는다. (현재 구독 중인 AI CLI 또는 무료 티어/GitHub Pages/GitHub Actions만 사용)
2. **익명성 철저 유지:** 웹사이트, 텔레그램 채널, 핀터레스트, Git 커밋/문서 어디에도 운영자의 실명이나 개인 닉네임(`sol` 등)을 노출하지 않고 오직 브랜드명(`GearCompare Hub`)만 사용한다.
3. **법적 대가성 문구 강제 검증:** 모든 웹페이지 상단, RSS 설명, 텔레그램 알림, SNS 댓글 링크에는 쿠팡 파트너스 및 아마존 어소시에이트(`As an Amazon Associate...`) 대가성 고지 문구가 코드 레벨(`verifier.py`)로 강제 포함되어야 한다.
4. **오매칭·가품 주의보 유지:** 본품 대신 케이스·케이블·키캡 단품이 매칭되는 것을 막는 `verifier.py` 가격 비율 가드(`min_price_ratio_vs_msrp: 0.35`)와 금지어 필터를 절대 끄지 않으며, 저장장치(SSD)·대기업 마우스 등 가품 위험 품목은 직구 대신 국내 정발/아마존 직영을 우선 추천하는 정직한 판단 로직을 유지한다.
5. **비밀정보 커밋 금지:** `config.local.json`, `.env`, 봇 토큰, API Secret은 절대 Git에 커밋하지 않는다.
