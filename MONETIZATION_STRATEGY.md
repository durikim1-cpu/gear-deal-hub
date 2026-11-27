# GearCompare Hub — 무자본(0원) 글로벌·국내 제휴 수익화 전략 및 3-AI 만장일치 아키텍처 문서

> **For AI Coding & Operations Agents (Claude Code, Gemini, Codex, Antigravity, Cursor):**
> 이 문서는 본 저장소(`gear-deal-hub`)의 비즈니스 수익 구조, 현재 개통 완료된 제휴/채널 자산, 그리고 **2026-11-26 세 AI(Gemini · Claude · Codex)가 3개 핵심 주제에 대해 총 30회 발언 끝에 전원 일치로 확정한 수익화·약관 준수 아키텍처**를 정의합니다. 향후 코드를 수정할 때는 반드시 본 문서의 합의 원칙을 준수하세요.

---

## 1. 세 AI(Gemini · Claude · Codex) 만장일치 핵심 실행 아키텍처

### [합의 1] 예산 0원 콜드스타트 유입 전략 (`맥북 독 호환 판별기` 선개통 + 무인 배포)
1. **첫 개통 의사결정 도구 단일화 (`/ko/tools/macbook-dock-checker/`, `/en/tools/macbook-dock-checker/`):**
   - 69개 전 품목 무차별 확산이나 레드오션 관부가세 계산기 대신, 구매 직전 문제와 특정 하드웨어 추천이 한 화면에서 직결되는 **맥북 모델·칩별 듀얼모니터 독 호환 판별기 1종**을 핵심 유입 도구로 운영한다.
   - Apple 공식 외부 디스플레이 지원 사양과 DisplayLink / Thunderbolt 4 규격이 교차 검증된 조합만 추천하며, 고주사율 DSC·데이지체인·리눅스 등 불명확 조합은 억지 추천 대신 **`판정 유보(확인 필요)`**로 표시한다.
2. **무인 배포 원칙:**
   - 외부 커뮤니티 수동 댓글 노동과 하루 3~4회 고정 틀 자동 도배를 전면 배제한다.
   - 핀터레스트 영문 RSS(`1:1` URL 매핑)와 검색엔진 색인(`sitemap.xml`)을 기본축으로 두고, 쓰레드(`social_publisher.py`)는 실제 할인코드·특가 신호가 포착됐을 때만 **하루 최대 1회 이하 비정기 발행**한다.
3. **0원 이원 계측 및 자가 결제 금지:**
   - 앞단(`방문 → 판별 완료 → 판매처 클릭`)은 경량 이벤트 훅(`app.js`)으로, 주문 전환은 경로별 제휴 추적 식별자 리포트로 분리 계측한다(본인·지인 결제 절대 금지). 개통 후 14일 퍼널 병목 실측 전에는 도구를 무분별하게 늘리지 않는다.

### [합의 2] 아마존 어소시에이트(`gearcomparehu-20`) 180일 내 3건 & 계정 수동 심사 생존 전략
1. **비공인 정적 가격 최우선 제거 & 필수 고지:**
   - 3번째 적격 판매 직후 열리는 아마존 수동 심사(Account Review) 탈락을 원천 차단하기 위해 영문 허브(69종), 가이드, 핀터레스트 PNG·RSS에서 비공인 정적 아마존 가격·할인율을 전면 제거했다(`verifier.py`에서 `prices` 키 유입 시 자동 차단).
   - 영문 허브·가이드·버튼 인접 영역에 `"As an Amazon Associate I earn from qualifying purchases."` 원문 고지를 명시하고, 판매자별 확인 없는 일괄 보장(`100% 정품·무료반품 보장`) 문구를 금지한다.
2. **외부 채널 → 등록된 허브 단일 경유 (`외부 직링 전면 중단`):**
   - 핀터레스트·텔레그램은 아마존 공인 소셜 목록에 없으므로 보수적 운영 원칙으로서 `@gearcompare_en`·`@gearcompare_kr`·핀터레스트·쓰레드에서 제휴 쇼핑몰 직접 링크를 발송하지 않고, 반드시 등록된 웹 허브(`?utm_source=telegram|pinterest|threads`)로만 랜딩시킨다.
3. **비템플릿 의사결정 가이드 12편 구축 (`/en/guides/`):**
   - 아마존 공식 심사 권장선(독창적 콘텐츠 10편+)을 충족하도록 ① 맥북/USB-C 디스플레이·NVMe 발열, ② 미국 규격 데스크 전원·GaN 재분배·TSA 100Wh 기내반입, ③ 홀이펙트/TMR 패드·포터블 SSD 가품 판별·`Budget Setup Picks`(가격 숫자 배제) 구성의 **12편 비템플릿 엔지니어링 가이드**(호환 매트릭스 + 제외 대상 체크리스트 포함)를 수록했다.
4. **핀터레스트 노출 우선순위 전환:**
   - 기존의 '알리 할인율순' 정렬을 폐기하고, 맥북 독 판별기 + 12개 해결 키워드형 가이드 + 미국 내 아마존 구매 명분이 뚜렷한 기어를 `1:1` 고유 URL로 매핑해 발행한다.

### [합의 3] 정적 가격 한계와 약관·표시광고법 리스크 해결 (`Zero-Stale · Fail-Closed`)
1. **API 미해금 구간 가격·우회 배지 전면 금지:**
   - API 미해금 상태(현재 아마존 US, 누적 매출 15만 원 전 쿠팡)에서는 정적 판매가 숫자뿐 아니라 우회 상대 격차 배지(`"30% 저렴"`), 가격대 단정(`"Under $50"`)을 모두 금지하며, 본문 HTML·JSON-LD(`offers.price`)·메타태그·RSS·Git 이력 어디에도 쇼핑몰 가격을 남기지 않는다.
   - 제조사 공식 출고가(MSRP)는 출처·확인일을 붙여 상세페이지 **기술 사양표 내부 참고치**로만 분리 배치한다.
2. **아마존 추적 제외 & 서버·클라이언트 이중 만료(`Fail-Closed`):**
   - 아마존은 API 해금 후에도 별도 서면 허가 전까지 30일 가격 추적·알림 대상에서 계속 제외한다(`allow_amazon_price_tracking: false`).
   - 추후 알리익스프레스 포털 API 등 해금 시, 정적 HTML이 아닌 별도 만료 강제 응답(`LIVE_OFFERS_ENDPOINT`, 서버 응답 시점 `expires_at` 검사 + 클라이언트 열린 탭 60초 주기 재확인)으로만 공급하며 만료·장애 즉시 가격 블록을 숨긴다.
3. **언어와 실제 배송국 기준 분리 (`dest-bar`):**
   - **대한민국 수령(`KR`):** 일괄 150달러 오정보를 폐기하고 **미국발 목록통관 적격 미화 200달러 이하 / 일반통관 및 중국·기타국발 미화 150달러 이하** 규칙을 구분 안내한다.
   - **미국 수령(`US`):** 미국 소액면세(*de minimis*) 중단을 반영해 Amazon `Ships from US` 여부 및 AliExpress 결제창 `Import charges` 포함 여부를 핵심 체크 항목으로 안내한다.
4. **배포 후 공개 URL 실증 & 중복 방지(`deploy.yml` 3단 잡 분리):**
   - `build-and-verify` → `deploy` → `notify-after-deploy` 순서를 강제하여, 실제 배포된 GitHub Pages 공개 URL이 `HTTP 200` 및 필수 콘텐츠를 정상 응답하는지 검증한 뒤에만 고유 `event_id` 멱등성 체크를 거쳐 알림을 발송한다.

---

## 2. 현재 구축 및 개통 완료된 자산 현황 (2026-11-26 기준)

| 구분 | 상태 | 식별자 / URL | 비고 |
| :--- | :--- | :--- | :--- |
| **GitHub 저장소** | ✅ 운영 중 | `https://github.com/durikim1-cpu/gear-deal-hub` | 6시간 주기 GitHub Actions 무료 실행 |
| **국내 비교 허브** | ✅ 배포됨 | `https://durikim1-cpu.github.io/gear-deal-hub/ko/` | 69종 모델 · 수령국 통관 토글 · 단점 검수 |
| **글로벌 비교 허브** | ✅ 배포됨 | `https://durikim1-cpu.github.io/gear-deal-hub/en/` | Amazon US vs Direct · Zero-Stale 설계 |
| **맥북 독 호환 판별기** | ✅ 개통됨 | `/ko/tools/macbook-dock-checker/` · `/en/tools/macbook-dock-checker/` | M1~M4 칩·클램쉘·HDCP 교차 검증 도구 |
| **영문 의사결정 가이드** | ✅ 개통됨 | `https://durikim1-cpu.github.io/gear-deal-hub/en/guides/` | 비템플릿 심층 가이드 12편 (`Budget Setup Picks` 포함) |
| **핀터레스트 RSS** | ✅ 배포됨 | `https://durikim1-cpu.github.io/gear-deal-hub/en/pinterest-feed.xml` | 가격 무표기 `1000×1500` PNG 24종 1:1 매핑 |
| **국내 검수 RSS** | ✅ 배포됨 | `https://durikim1-cpu.github.io/gear-deal-hub/ko/feed.xml` | 가격 무표기 단점·통관 검수 피드 |
| **텔레그램 국내/해외** | ✅ 운영 중 | `@gearcompare_kr` / `@gearcompare_en` | 익명 설정 완료 · 직링 없이 허브 단일 경유 |
| **쿠팡 파트너스** | ✅ 승인됨 | **`AF8784203`** (`AUTO_APPROVED`) | 출처·배송국별 `subid` 자동 분리 적용 |
| **아마존 어소시에이트** | ✅ 발급됨 | **`gearcomparehu-20`** (미국 US) | 180일 내 적격 판매 3건 & 수동 심사 대비 완료 |
| **알리익스프레스 포털** | ⏳ 심사 중 | `portals.aliexpress.com` (`2026-11-25` 제출) | 승인 메일 도착 시 `ALIEXPRESS_TRACKING_ID` 및 API 연동 |
| **핀터레스트 비즈니스** | ✅ 무인 가동 중 | `https://www.pinterest.com/gearcomparehub` | 소유권 인증 및 RSS 자동 발행 연결 완료 |
| **구글 서치콘솔** | ✅ 제출 완료 | `https://durikim1-cpu.github.io/gear-deal-hub/` | `sitemap.xml` (179개 URL) 자동 갱신 |

---

## 3. 코드 아키텍처 맵

```text
gear-deal-hub/
├── run_pipeline.py          # Phase 1 (빌드·검수) 및 Phase 2 (--dispatch-deployed 배포 후 공개 URL 실증 발송)
├── config.example.json      # 공개 설정 템플릿 (채널별 PII-free subId/tracking 매핑 포함)
├── config.local.json        # 로컬 전용 비밀 설정 (.gitignore 처리됨 — 절대 커밋 금지)
├── data/
│   ├── products.json        # 정적 판매가가 제거된 69종 마스터 DB (참고 MSRP + buying_profile 수록)
│   └── candidates_inbox.json# 오매칭·정적 가격 차단 회귀 테스트용 샘플
├── src/
│   ├── affiliate.py         # 채널·배송국별 PII-free 추적 링크 생성 및 법적 고지 상수
│   ├── verifier.py          # Gatekeeper (단품 키워드, 비공인 정적 가격 유입, 일괄 보장 문구, 고지문 강제 검수)
│   ├── tools_and_guides.py  # 맥북 듀얼모니터 독 호환 판별기(한/영) 및 영문 비템플릿 가이드 12편
│   ├── site_builder.py      # 무확장자 정적 빌더 + 배송국 토글 + Fail-Closed 실시간 가격 슬롯 + UTM 매퍼
│   ├── pin_generator.py     # 가격 무표기 해결 키워드형 1000x1500 PNG 및 1:1 URL RSS 생성기
│   ├── deal_sniper.py       # 아마존 추적 제외 · 프로모션 코드 매칭 · 고유 event_id 멱등성 키 생성
│   ├── notifier.py          # 공개 URL HTTP 200 실증 후 허브 단일 랜딩 텔레그램 발송기
│   └── social_publisher.py  # 하루 최대 1회 상한 · 공개 URL 실증 후 쓰레드 2단 발행기
└── .github/workflows/
    └── deploy.yml           # build-and-verify -> deploy -> notify-after-deploy 3단계 무인 워크플로
```

---

## 4. 절대 위반 금지 수칙 (Hard Guardrails)

1. **추가 금전 지출 0원 원칙:** 유료 서버, 유료 DB, 유료 도메인, 해외결제 카드 등록이 강제되는 유료 API를 절대 도입하지 않는다.
2. **익명성 철저 유지:** 웹사이트, 텔레그램, 핀터레스트, Git 커밋/문서 어디에도 운영자 개인 식별 정보나 닉네임을 노출하지 않고 오직 `GearCompare Hub`만 사용한다.
3. **비공인 정적 가격·우회 할인율 금지:** API 권한과 서버·클라이언트 만료(`expires_at`) 검증이 없는 상태에서 쇼핑몰 가격 숫자나 `"30% 저렴"`, `"Under $50"` 같은 우회 가격 주장을 HTML·JSON-LD·메타태그·핀 이미지·알림에 넣지 않는다.
4. **아마존 무단 가격 추적 금지 및 허브 단일 경유:** 별도 서면 허가 전까지 아마존 가격 이력 저장·하락 알림을 구현하지 않으며, 모든 외부 채널은 반드시 등록된 웹 허브로만 링크한다.
5. **텔레그램 포맷 원칙 유지:** 텔레그램 메시지 본문에는 쇼핑몰 직접 링크와 `[대가성 광고 안내]` 문구를 넣지 않고 깔끔한 정보 요약 + 허브 상세페이지 링크만 유지한다(법적 대가성 고지는 랜딩되는 허브 상단 및 구매 버튼 인접 영역에서 명확히 표시).
6. **비밀정보 커밋 금지:** `config.local.json`, `.env`, `.git/deploy_key`, 봇 토큰, API Secret은 절대 Git에 커밋하지 않는다.
