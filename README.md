# BitBot

BitBot은 사용자가 직접 매수/매도 조건을 설정하고, 과거 데이터로 모의 테스트한 뒤, 필요하면 Upbit 실거래까지 실행할 수 있도록 만든 자동매매 도구입니다.

기본 실행은 모의투자(paper mode)입니다. 실제 주문은 `.env`에 Upbit API 키를 설정하고, 앱에서 `Live Trading`을 켠 뒤 확인 창을 통과해야만 실행됩니다.

## 실행 방법

```bash
pip install -r requirements.txt
python main.py
```

## GitHub Pages

[https://vedal629.github.io/BitBot/](https://vedal629.github.io/BitBot/)에서 웹 화면을 바로 열 수 있습니다.

GitHub Pages 설정이 `docs` 폴더 기준이든 저장소 루트 기준이든 화면이 보이도록 `docs/index.html`과 루트 `index.html`을 함께 제공합니다.

## HTML 실시간 차트와 모의 테스트

브라우저에서 `docs/index.html`을 열면 Upbit 공개 API 기반 실시간 차트와 과거 캔들 기반 모의 테스트를 할 수 있습니다.

실시간 화면에서 지원하는 항목은 다음과 같습니다.

- KRW-BTC, KRW-ETH, KRW-XRP 실시간 캔들
- 1분, 5분, 15분, 1시간, 일봉 차트
- 10초 간격 자동 갱신
- Upbit API 실패 시 BTC/USDT 샘플 CSV 자동 전환

모의 테스트에서 설정할 수 있는 항목은 다음과 같습니다.

- 테스트 기간: 시작일, 종료일
- 초기 자산
- 주문 비중
- SMA 기간
- RSI 기간
- 매수 조건: 장기 SMA보다 낮은 비율, RSI 기준
- 매도 조건: 장기 SMA보다 높은 비율, RSI 기준
- 익절, 손절, 수수료

모의 테스트 결과로 전략 수익률, 기간 수익률, 최종 자산, 총 손익, 최대 낙폭, 승률, 체결 내역을 확인할 수 있습니다.

## 실거래 설정

Upbit 실거래를 사용하려면 `.env` 파일에 API 키를 설정합니다.

```bash
UPBIT_ACCESS_KEY=your-access-key
UPBIT_SECRET_KEY=your-secret-key
```

## 현재 지원하는 자동매매 조건

- 현재가가 장기 SMA보다 지정 비율 이상 낮으면 매수
- RSI가 지정 값 이하이면 매수
- 현재가가 장기 SMA보다 지정 비율 이상 높으면 매도
- RSI가 지정 값 이상이면 매도
- 익절 또는 손절 비율에 도달하면 매도

## 주의사항

이 프로젝트는 투자 판단을 대신하지 않습니다. 실거래 전에는 반드시 `docs/index.html` 모의 테스트와 paper mode로 조건이 의도대로 동작하는지 먼저 확인하세요.
