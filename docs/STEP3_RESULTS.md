# STEP 3 — AI 학습 및 평가 결과

- 실행 환경: Linux Python 3.13.5, scikit-learn 1.8.0.
- 기준 시뮬레이터: d732028, simulation.py blob 34c8e880b1907dd4aef98da4ec821c57fa1f7bfe.
- 실행: python hw2/simulation.py && python hw2/train.py
- 분할 시드 2026, episode 단위 42/9/9 (7560/1620/1620행), 동일 episode의 두 공간은 같은 분할에 포함.
- Train으로만 학습, Validation MAE로 모델 선택, Test는 최종 평가에만 사용.
- LinearRegression 기본 설정. RF: n_estimators=64, max_depth=12, min_samples_leaf=2, random_state=2026, n_jobs=1.
- 입력 5개: co2_ppm, occupancy, ventilation_pct, volume_m3, delta_co2_ppm. 목표: 현재 인원과 환기 유지, 무작위 노이즈 없는 5분 후 CO2.

## 실제 실행 결과

| 모델 | Val MAE | Val RMSE | Val R² | Test MAE | Test RMSE | Test R² | Test Precision | Test Recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Persistence | 61.16587 | 78.03938 | .898596 | 65.14691 | 83.56229 | .916710 | .903811 | .855670 |
| Linear Regression | 18.39103 | 25.07759 | .989529 | 21.85392 | 29.22689 | .989811 | .963087 | .986254 |
| Random Forest | 6.02114 | 9.50463 | .998496 | 7.23272 | 13.10546 | .997951 | .981261 | .989691 |

단위: MAE/RMSE ppm. Precision/Recall은 5분 조건부 목표 1000ppm 이상을 양성으로 정의한다.

| 모델 | TN | FP | FN | TP (test) |
|---|---:|---:|---:|---:|
| Persistence | 985 | 53 | 84 | 498 |
| Linear Regression | 1016 | 22 | 8 | 574 |
| Random Forest | 1027 | 11 | 6 | 576 |

선택: Random Forest (validation MAE 최소). Test episode: 6, 7, 14, 20, 32, 38, 39, 41, 57. Validation: 15, 26, 28, 31, 35, 36, 37, 46, 50. 나머지 train.

## 순수 Python 추론

두 모델의 JSON export 및 재로드 후 test 전 행에서 sklearn 예측과 비교. 최대 절대 차이 LR 4.55e-13 ppm, RF 1.14e-12 ppm (허용오차 1e-6 ppm). RF 선택 모델 크기 6,275,951 bytes. AWS Python 3.12 실제 배포는 아직 검증하지 않음.

## 해석 및 한계

모의 환경 정답은 알려진 수식으로 생성되므로 그 수식을 직접 계산하는 oracle은 MAE 0이다. 이는 실측 환경에 대한 예측 정확도 증거가 아니다. 학습 모델은 과제용 모의 환경의 비선형 매핑을 근사하는 역할이다. 실제 제어 뒤 농도는 조건부 예측과 달라질 수 있다. RF가 학습 분포 외에서 더 정확하다는 보장은 없으며 STEP 4의 폐루프 실험이 필요하다.

생성 CSV, 그래프, 모델 JSON은 재현 가능하며 gitignore 대상. Windows에서 재실행 후 버전 차이와 결과를 확인한다. 코드 blob: train.py 14f38226b4e3e3a2761a793f05586e385b9ea631, inference.py 0cb259b4e0dfd56193b75b0890ecd2039fac9505.
