# ⚡ GearCompare Hub (완전 0원 글로벌·국내 제휴 수익화 & 호환성 판별 허브)

> **AI 에이전트 인수인계 필독 문서:** 비즈니스 수익 모델, 개통된 제휴 ID/채널 현황, 그리고 세 AI(Gemini · Claude · Codex)가 만장일치로 확정한 수익화·약관 준수 아키텍처 전체는 [MONETIZATION_STRATEGY.md](./MONETIZATION_STRATEGY.md)에 정리되어 있습니다.

글로벌 공통 모델이 존재하는 **소형 IT · 데스크 · USB-C 기어(69종, 11개 카테고리)**를 검수하여 다음 두 시장을 동시에 공략하는 무자본(유지비 0원) 정적 웹사이트 + 핀터레스트/텔레그램/쓰레드 무인 자동화 시스템입니다.

- **국내 허브 (`/ko/`):** 쿠팡 국내 배송 vs 알리익스프레스 직구 실사용 단점·수령국 통관 기준(미국발 목록통관 \$200 / 기타국발 \$150) 비교
- **글로벌 허브 (`/en/`):** Amazon US vs AliExpress Direct 실사용 단점·수입관세 체크리스트
- 두 허브 모두 **실시간 현황판**(세일 신호등 + 프로모 코드 구간 + 오구매 컷 필터)으로 시작하며, 아래 도구·콘텐츠가 한/영 `hreflang` 쌍으로 제공됩니다.

| 구분 | 경로 | 내용 |
|---|---|---|
| 도구 | `/{ko,en}/tools/macbook-dock-checker/` | 맥북 칩별 듀얼모니터 독 호환 판별기 |
| 도구 | `/{ko,en}/tools/ali-promo-calculator/` | 알리 프로모 코드 체감가·통관 계산기 (쿠폰 → 코인 → 코드 구간, \$150/\$200 면세선 판정) |
| 가이드 | `/{ko,en}/guides/` + 각 12편 | 한국어판은 KC 인증·220V 플러그·통관·쿠팡 vs 알리 기준으로 현지화 |
| 1:1 대결 | `/{ko,en}/vs/` + 각 15편 | 조건별 승자 2개를 H1 바로 아래에서 즉답, 스펙·참고가 비교표, 단점 맞대결 |

정적 페이지는 총 226개(제품 69종 기준)이며 `dist/sitemap.xml`에 전부 수록됩니다.

## 핵심 아키텍처

- `data/products.json` : 비공인 정적 판매가를 배제한 69종 마스터 DB (제조사 참고 MSRP + 구매 경로 프로필 + 브랜드·모델/SKU 정확 일치 검색어)
- `data/ali_promo_tiers.json` : 프로모 코드 참고 구간과 기간 한정 이벤트 코드(시작·종료일, 출처, 확인일 포함). 종료일이 지나면 참고 구간으로 자동 복귀
- `data/live_offers_cache.json` (런타임 생성, Git 미추적) : 실시간 오퍼 캐시
  - **Tier 1 `community_benchmark`** : Reddit·뽐뿌 게시글 제목에서 포착한 가격. `MSRP × 0.35` 미만은 차단하고 관측 후 48시간에 만료. 화면에는 반드시 "최근 커뮤니티 포착 핫딜 기준가 (관측일 · 종료 가능)"로만 표기
  - **Tier 2 `ali_official_api`** : `ALIEXPRESS_APP_KEY` / `ALIEXPRESS_APP_SECRET`이 설정된 경우에만 동작하는 알리 공식 API 훅(`src/ali_api.py`). `s.click` 프로모션 링크로 자동 교체하고 "실시간 알리 API 특가"로 표기
- `src/verifier.py` : **Gatekeeper 검수기** (액세서리 단품 차단, 비공인 정적 가격 차단, 일괄 보장 문구 차단, 실사용 단점·고지문 강제)
- `src/collector.py` / `src/deal_sniper.py` : 라이브 신호 전량 전달(`trend_signals`), 가격 파서, 모델 정밀 매칭, 커뮤니티 기준가 수집, 아마존 가격 추적 제외
- `src/tools_and_guides.py` / `src/guides_ko.py` : 독 판별기, 프로모·통관 계산기, 세일 신호등 규칙, 한/영 가이드
- `src/vs_battles.py` / `src/vs_pairs.py` : 1:1 대결 15쌍 데이터와 렌더러
- `src/site_builder.py` : 무확장자 정적 빌더(`dist/`) + 현황판 + 오구매 컷 필터 + 기준가 스트립 + 수령국 토글 + 채널별 PII-free 추적 매퍼
- `src/pin_generator.py` : 가격 무표기 `1000×1500` PNG 52장(도구 2 · 가이드 12 · 대결 15 · 제품 23)과 `1:1` 고유 URL 핀터레스트 RSS, 네이버 서치어드바이저 형식 한국어 RSS
- `src/notifier.py` / `src/social_publisher.py` : 배포 후 공개 URL `HTTP 200` 실증 및 `event_id` 중복 방지 발송기 (텔레그램 링크 미리보기 사용, 본문에 고지 문구 미삽입)
- `.github/workflows/deploy.yml` : 6시간 주기 `build-and-verify` → `deploy` → `notify-after-deploy` 무료 무인 파이프라인 (배포 후 IndexNow로 사이트맵 전체 URL 제출)

## 로컬 실행 방법

```powershell
python run_pipeline.py                    # 오프라인 빌드
python run_pipeline.py --live-network     # Reddit·뽐뿌 라이브 신호 포함 빌드
python run_pipeline.py --dispatch-deployed  # 배포 후: IndexNow 전체 URL 제출 + (플래그 지정 시) 알림 발송
```

## 검증

```powershell
python -m pytest                          # 단위·빌드 테스트
pip install playwright                    # 최초 1회 (설치된 Chrome/Edge 사용)
python scripts/verify_layout.py           # 320·375·768·1440px 가로 넘침·카드 삐져나옴·필터·복사·계산기 검증
```
