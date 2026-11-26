# Ajou AIoT — HW2

AI 기반 실내 공기질 예측 및 자동 환기 디지털 트윈.

- 공간: 일반 강의실과 컴퓨터실
- 입력: 공간별 CO₂ 농도(ppm), 재실 인원(명), 총 4개 센서 입력
- AI: 5분 후 CO₂ 농도를 예측하는 Linear Regression 및 Random Forest 비교
- 제어: 기본 환기(20%), 사전 환기(60%), 강화 환기(100%)
- 시각화: AWS IoT TwinMaker의 별도 Scene 2개와 Grafana 상태 아이콘·색상 및 수치 대시보드
- 마감: 2026-11-30 23:59 KST

## 프로젝트 문서

- [개발 계획서](docs/PLAN.md)
- [개발 일지](docs/DEVLOG.md)
- [Windows 환경 설정 및 다른 PC에서 작업 이어가기](docs/SETUP.md)

## 현재 상태 (2026-11-25)

- 로컬 Python 환경 설치 및 설계 결정 완료 (사용자 확인).
- [센서 시뮬레이터](hw2/simulation.py) 구현 및 Python 3.13.5 테스트 환경 검증 완료 (7/7). 사용자 Windows에서도 7/7 통과 확인.
- AI 학습 및 JSON 내보내기 검증 완료 (Linux). Random Forest 선정. [STEP 3 결과](docs/STEP3_RESULTS.md). 사용자 Windows에서도 RF 선정 및 JSON parity 확인 완료 (sklearn 1.9.1).
- 폐루프 환기 제어 및 비교 실험 Linux 검증 완료. [STEP 4 결과](docs/STEP4_RESULTS.md). Windows 재현 확인 완료 (10/10 tests, demo 3 ticks).
- AWS 사전 어댑터 및 패키징 코드 작성, 로컬 검증 대기. [STEP 5 준비](docs/STEP5_PREP.md). 실제 AWS 배포 및 시각화 미진행.
- LSTM은 필수 구현과 제출물 확보 이후에만 검토.

## 빠른 시작 (Windows PowerShell)

```powershell
git clone https://github.com/darkkyoung/Ajou_AIoT.git
cd Ajou_AIoT
py -3.13 -m pip install -r hw2/requirements.txt
py -3.13 hw2/simulation.py
py -3.13 -m unittest discover -s hw2 -p "test_*.py"
```

다른 Python 프로젝트와 분리하려면 SETUP.md의 가상환경 방식을 사용한다. 생성 CSV는 hw2/data/sensor_data.csv 및 hw2/data/training_data.csv이며 각각 10,800행 검증 완료. 로컬 시계 모드: `py -3.13 hw2/simulation.py --mode demo --steps 3` (10초 간격), `--mode live` (60초 간격). 아직 AI 제어나 AWS 연동은 아니다. Lambda 배포는 Python 3.12와 호환되는 순수 Python 추론을 우선 고려한다.

## 저장소 관리

단계마다 코드, 설정 템플릿, 테스트 결과, 설계 변경사항을 커밋한다. 실제 AWS 인증 정보, 개인 식별 정보, 학번, 로컬 절대 경로, 원본 강의 자료, 제출용 PDF/영상은 공개 저장소에 올리지 않는다. 모의 데이터는 실제 측정값으로 취급하지 않는다.

## STEP 3 실행

```powershell
py -3.13 hw2/train.py
```

hw2/models/selected_model.json 및 hw2/results/step3/metrics.json, test_predictions.csv, model_mae.png, predictions.png 생성. 모델은 학습으로 재생성한다. LSTM 보류.

## STEP 4 실행

```powershell
py -3.13 hw2/evaluate.py
py -3.13 -m unittest discover -s hw2 -p "test_*.py" -v
py -3.13 hw2/control.py --mode demo --steps 3
```

STEP 3의 selected_model.json 필요. 결과는 hw2/results/step4/. control.py의 live/demo는 로컬 폐루프 모드이며 AWS 기능은 아니다.
