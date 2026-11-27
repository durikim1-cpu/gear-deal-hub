# ⚡ GearCompare Hub (완전 0원 글로벌·국내 제휴 수익화 & 호환성 판별 허브)

> **AI 에이전트 인수인계 필독 문서:** 비즈니스 수익 모델, 개통된 제휴 ID/채널 현황, 그리고 세 AI(Gemini · Claude · Codex)가 만장일치로 확정한 수익화·약관 준수 아키텍처 전체는 [MONETIZATION_STRATEGY.md](./MONETIZATION_STRATEGY.md)에 정리되어 있습니다.

글로벌 공통 모델이 존재하는 **소형 IT · 데스크 · USB-C 기어(69종, 11개 카테고리)**를 검수하여 다음 두 시장을 동시에 공략하는 무자본(유지비 0원) 정적 웹사이트 + 핀터레스트/텔레그램/쓰레드 무인 자동화 시스템입니다.

- **국내 허브 (`/ko/`):** 쿠팡 국내 배송 vs 알리익스프레스 직구 실사용 단점·수령국 통관 기준(미국발 목록통관 \$200 / 기타국발 \$150) 비교 + **맥북 듀얼모니터 독 호환 판별기 (`/ko/tools/macbook-dock-checker/`)**
- **글로벌 허브 (`/en/`):** Amazon US vs AliExpress Direct 실사용 단점·수입관세 체크리스트 + **MacBook Dual-Monitor Dock Checker (`/en/tools/macbook-dock-checker/`)** + **12편 비템플릿 엔지니어링 구매 가이드 (`/en/guides/`)**

## 핵심 아키텍처

- `data/products.json` : 비공인 정적 판매가를 배제한 69종 마스터 DB (제조사 참고 MSRP 사양표 분리 + 구매 경로 프로필)
- `src/verifier.py` : **Gatekeeper 검수기** (액세서리 단품 차단, 비공인 정적 가격 차단, 일괄 보장 문구 차단, 실사용 단점·고지문 강제)
- `src/tools_and_guides.py` : 맥북 모델·칩별 듀얼모니터 독 호환 판별기(한/영) 및 영문 심층 가이드 12편(`Budget Setup Picks` 포함)
- `src/site_builder.py` : 무확장자 정적 빌더(`dist/`) + 수령국 토글 + Fail-Closed 실시간 API 가격 슬롯 + 채널별 PII-free 추적 매퍼
- `src/pin_generator.py` : 가격 무표기 해결 키워드형 `1000×1500` PNG 인포그래픽 및 `1:1` 고유 URL 핀터레스트 RSS 생성기
- `src/deal_sniper.py` / `src/notifier.py` / `src/social_publisher.py` : 아마존 가격 추적 제외, 배포 후 공개 URL `HTTP 200` 실증 및 `event_id` 중복 방지 발송기
- `.github/workflows/deploy.yml` : 6시간 주기 `build-and-verify` → `deploy` → `notify-after-deploy` 무료 무인 파이프라인

## 로컬 실행 방법

```powershell
python run_pipeline.py
```
