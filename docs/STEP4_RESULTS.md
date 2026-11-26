# STEP 4 — 폐루프 환기 제어 실험

## 방법

- 기준: STEP 3 commit 4537c9f. Linux Python 3.13.5, sklearn 1.8.0에서 동일 시뮬레이터/추론 blob 및 RF 설정, episode 분할을 사용해 모델 재생성.
- 모델 SHA256: 1468d66518267f8c156d322e6e7387075f3332cc6dffec7d0708295a2fae5940.
- 새로운 시드 300000 + episode*10 + room_index, 20회 x 2공간 x 90분, 정책별 3600 room-minutes. 초기 농도/인원/노이즈 동일성 검증.
- 직전 환기 출력을 유지하는 5분 조건부 예측 -> 현재 >=1000이면 100%, 아니면 예측 >=1000이면 60%, 나머지는 20%. 예측 입력의 직전 출력과 결정된 출력은 별도 필드로 보존.
- 일반 제어는 예측 없이 현재 농도에 따라 20%/100%. 초기 출력 20%. 결정된 출력은 다음 1분 농도에 반영.
- 평가는 매 분 시작 시점의 관측 농도, 해당 분의 제어 출력을 사용. 초과 ppm-min은 max(C-1000,0)의 합. 환기 출력 %-min은 가동량 대리지표이며 전력량(kWh)이 아니다. 제어 변경 횟수는 초기 20% 대비 변경도 포함.

## 실제 실행 결과

| 지표 | 일반 제어 | AI 제어 |
|---|---:|---:|
| 평균 CO2 ppm | 914.0154 | 910.3133 |
| 최대 CO2 ppm | 1046.08 | 1042.19 |
| 1000 ppm 이상 room-min | 1130 | 994 |
| 초과 ppm-min | 17134.94 | 14102.03 |
| 누적 환기 %-min | 162400 | 164920 |
| 평균 환기 % | 45.1111 | 45.8111 |
| 사전 환기 min | 0 | 335 |
| 강화 환기 min | 1130 | 994 |
| 출력 변경 | 1440 | 1732 |

| 공간 | 일반 기준 이상 분 | AI 기준 이상 분 | 일반 초과 ppm-min | AI 초과 ppm-min |
|---|---:|---:|---:|---:|
| classroom-01 | 439 | 387 | 7223.78 | 5804.50 |
| computerlab-01 | 691 | 607 | 9911.16 | 8297.53 |

기준 이상 시간 12.0%, 누적 초과 농도 17.7% 감소. 평균 농도 약 3.7 ppm 감소, 환기 출력 평균 0.70%p 증가. 출력 변경 횟수 20.3% 증가. AI가 사전 환기 후 다음 분에 기본 환기로 복귀하는 등의 반복이 가능하며, 기존 합의 규칙을 변경하지 않았다. 향후 히스테리시스/최소 유지시간 검토. 모의 환경 결과이며 실제 환기 효과 또는 에너지 절감의 증거가 아니다.

## 검증

- python -m unittest test_control -v: 신규 테스트 3/3 PASS. 경계값, 직전 출력 입력, 다음 분 피드백, 동일 외생조건 확인.
- python evaluate.py: 정상 완료, 정책별 3600행, 두 정책의 초기/외생조건 일치 assertion 통과.
- python control.py --mode demo --steps 1: 두 공간 JSON 출력 성공. 실제 10/60초 대기 및 AWS 연동은 아직 검증하지 않음.
- Windows STEP 3 사용자 실행: sklearn 1.9.1, RF test MAE 7.25767064, RMSE 13.24438087, R2 .99790764, TN/FP/FN/TP 1028/10/7/575. Validation MAE 6.01684649, JSON parity 1.1368683772161603e-12 ppm. 모델 6275715 bytes. Windows STEP 4 결과는 별도 확인 필요.
- 코드 blob: control.py 3b9e317edc8d749d1c8a28385f08ecc242b37383, evaluate.py a5462fec4adeefe323f1b25037b3428ad7052e35, test_control.py 9f6015b273a699132643002979a3f4ead19f86d4.
- 생성 결과: hw2/results/step4/control_metrics.json, control_timeseries.csv, classroom-01.png, computerlab-01.png. 재현 가능한 로컬 파일은 gitignore 유지.

## 사용자 Windows 최종 검증

381dca7에서 evaluate.py와 전체 unittest 10/10 PASS(0.176s), demo 3 tick(두 공간, 10초 실제 간격) 성공. 모델 SHA256 565da9378788149d6b10d70e61544caaef0ccf0694263de1abe9d68831d80405. 제어 결과는 위 전체/공간별 수치와 동일. demo 3 tick은 모두 normal; 사전/강화 환기는 전체 비교 실험에서 관찰됨. AWS 미검증.
