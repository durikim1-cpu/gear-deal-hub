# ⚡ GearCompare Hub (완전 0원 제휴 수익화 자동화 파이프라인)

글로벌 공통 모델이 존재하는 **소형 IT · 데스크 기어**를 수집·검수하여 다음 두 시장을 동시에 공략하는 무자본(유지비 0원) 정적 웹사이트 + 텔레그램 알림 봇입니다.

- **국내 타겟 (`/ko/`):** 쿠팡 로켓배송 vs 알리익스프레스 직구 가격·단점 비교 + 국내 텔레그램 알림
- **해외 타겟 (`/en/`):** Amazon Prime vs AliExpress Direct 가격·단점 비교 + 영문 텔레그램 알림

## 폴더 구조

- `data/products.json` : 검수 완료된 글로벌 IT 기어 비교 DB (초기 제휴 심사 통과용 12종 기본 수록)
- `data/candidates_inbox.json` : 크롤링 신규 후보 대기열 (본품 오매칭 차단 테스트 샘플 포함)
- `src/collector.py` : Reddit 공개 JSON 트렌드 및 후보 수집기
- `src/verifier.py` : **Gatekeeper 자동 검수기** (케이스 단품/저가 오매칭 차단, 단점 누락 차단, 대가성 문구 검증)
- `src/site_builder.py` : 외부 라이브러리 0개 순수 파이썬 다국어 정적 웹사이트 생성기 (`dist/`)
- `src/notifier.py` : 텔레그램 한/영 채널 핫딜 포맷터 및 발송기
- `.github/workflows/deploy.yml` : 6시간 주기 자동 빌드 및 **GitHub Pages 무료 배포** 설정

## 로컬 실행 방법

```powershell
python run_pipeline.py
```

실행 후 `dist/index.html`, `dist/ko/index.html`, `dist/en/index.html` 및 `dist/telegram_preview_ko.txt`에서 생성된 결과물을 바로 확인할 수 있습니다.

## 내 제휴 아이디 & 텔레그램 토큰 연결 방법

1. `config.example.json`을 복사해 `config.local.json` 파일을 만듭니다 (`config.local.json`은 `.gitignore`에 의해 GitHub에 절대 올라가지 않습니다).
2. GitHub에 올린 뒤 자동 배포할 때는 저장소의 **Settings → Secrets and variables → Actions**에 아래 값을 등록하면 됩니다:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID_KO` / `TELEGRAM_CHAT_ID_EN`
   - `COUPANG_PARTNERS_ID` / `ALIEXPRESS_TRACKING_ID` / `AMAZON_ASSOCIATE_TAG`
