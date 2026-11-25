# HW2 개발 일지

## 2026-11-25 — STEP 0 / STEP 1

### 완료

- HW2 과제 요구사항 검토: 서로 다른 공간 2개 이상, 센서 입력 총 3개 이상 및 공간마다 최소 1개, AWS 데이터 저장/조회, 자동 갱신과 재접속 검증, 보고서 PDF 및 작동 MP4 제출. AI 적용은 선택 평가 항목이며 이번 프로젝트에서는 적용하기로 함.
- Windows VS Code 작업 폴더 준비. Python 설치 및 numpy, pandas, scikit-learn, matplotlib import 확인(SUCCESS 화면 확인).
- Windows의 python 명령은 앱 실행 별칭을 가리키므로 설치된 Python 3.13을 py -3.13으로 호출하기로 결정.
- 사용자 설계 확정: 일반 강의실과 컴퓨터실, 공간별 CO₂ 및 재실 인원, Linear Regression/Random Forest, 5분 예측, 기본/사전/강화 환기, 상태 아이콘·색상 및 수치 대시보드, 시나리오 반복/확률 변동/환기 효과. LSTM은 필수 구현 이후 여유 시 검토.
- 공개 GitHub 저장소 초기화 및 개발 계획 문서 등록.

### 설계상 주의

- HW1에서 사용한 AWS 리소스는 정리되었으므로 새로 구축한다. 이전 설정과 코드 백업은 참고 가능.
- Python 시뮬레이터 초안은 대화에서 제시됐지만 아직 로컬 실행 또는 저장소 코드로 검증하지 않았다.
- 학습 타깃은 현재 환기/인원 조건 유지 가정으로 정의하고, 데이터 분할은 episode 단위로 한다. 제어 실험은 같은 외생 조건에서 비교한다.
- 아직 모델 성능 수치, AWS 작동 결과, 영상 등은 확보하지 않았다. 검증 결과를 임의로 기록하지 않는다.

### 다음 작업

STEP 2: simulation.py 작성 및 센서 기록 생성, 범위/단위/재현성/환기 효과 확인. 이후 STEP 3 모델 학습 및 검증.

### 일지 기록 원칙

각 단계의 실제 변경 파일, 실행 명령, 실험 결과, 오류와 해결, 미완료 항목을 날짜별로 추가한다. AWS 계정 ID, 인증 정보, 학번 및 개인 경로는 공개 저장소에 게시하지 않는다.

## 2026-11-25 — STEP 2 소스 초안 등록

- 센서 시뮬레이터, 단위 테스트 5개, Python 패키지 목록, Windows 재설정 가이드 추가.
- STEP 2의 실행 및 10,800개 CSV 기록 확인은 아직 미완료. 테스트도 미실행. STEP 3~8은 미진행.
- 계획서 단계별 합계 약 10~16시간; 오류와 재검증 포함 개인 작업 예산은 14~18시간(2~3일 집중 작업). 11/27까지 핵심 구현, 11/28~29 검증·영상·보고서, 11/30 23:59 KST 이전 제출 목표.
- 다음 명령: `py -3.13 hw2/simulation.py`, `py -3.13 -m unittest discover -s hw2 -p "test_*.py"`.
- 5분 조건부 예측 타깃 생성, episode 분할, 모델 학습은 다음 단계에서 구현한다.

## 2026-11-25 — STEP 2 구현 및 테스트

- 사용자 결정 Q1 B: 공간별 이용 패턴 분리. Q2 C: 실제 시간과 가속 모드. Q3 A: 현재 인원 및 환기 유지 가정.
- simulation.py: 공간별 profile, 상태 연속성, 현재-직전 CO₂ 차이, 5분 조건부 정답, batch/live/demo CLI 구현. 로컬 clock은 live 60초/demo 10초 주기, 기록 시각과 가상 시각 분리.
- Python 3.13.5 Linux 테스트 환경에서 실행. sensor_data.csv 및 training_data.csv 각각 10,800행 생성, 고유 episode/room/minute 조합 10,800개. unittest 7/7 통과(0.257초). 시간 모드 테스트는 모의 clock 사용, 실제 대기 시간 및 Windows/AWS 동작은 아직 미확인.
- 실제 생성값: 강의실 5,400행, 431.69~1708.35 ppm, 1000ppm 이상 1329행, 현재 1000 미만/조건부 5분 후 1000 이상 290행. 컴퓨터실 5,400행, 451.04~1732.87 ppm, 1000ppm 이상 1761행, 조건부 초과 예정 351행.
- 모델 성능이나 제어 효과로 해석하지 않는다. 타깃은 동일 시뮬레이터에서 노이즈 없이 생성한 조건부 정답이며 현실 측정값이 아니다. 학습 시 episode ID, room ID, minute, scenario, target을 입력에서 제외하고 명시된 수치 feature만 사용한다.
- 코드 blob 검증 기준: simulation.py 34c8e880b1907dd4aef98da4ec821c57fa1f7bfe, test_simulation.py 477cd09c25f63d14e6949b4ed67cdcd36e80a861.
- 다음: 사용자 Windows에서 pull 및 batch/test 확인. STEP 3에서 episode 기준 분리, LR/RF/persistence 학습 및 비교. 현재 환기 출력은 학습 탐색용 무작위 값이며 AI 제어 및 AWS는 미구현.

## STEP 2 Windows 검증 / STEP 3 모델 학습

- 사용자 데스크톱에서 d732028 확인, CSV 두 종류 생성, unittest 7/7 통과 (0.171s). Python 패키지 import SUCCESS.
- 사용자 결정: LSTM 보류, Linear Regression과 Random Forest만 학습; persistence 기준 포함.
- Linux Python 3.13.5/sklearn 1.8.0에서 시뮬레이터 blob 동일 확인, train.py 실제 실행 완료. Validation MAE LR 18.3910, RF 6.0211; test MAE persistence 65.1469, LR 21.8539, RF 7.2327 ppm. RF 선정. JSON 추론 parity 양 모델 통과 (1e-6ppm 허용). RF 6,275,951 bytes. 상세 지표, 분할 및 한계는 STEP3_RESULTS.md.
- Windows STEP 3 실행 및 AWS는 미검증. 모델과 CSV, 그래프는 로컬에서 생성하며 공개 저장소에 커밋하지 않는다. 다음 STEP 4: 동일 외생 시나리오 폐루프 제어 비교 및 최종 대응 로직 검증.
