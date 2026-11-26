# Windows 개발 환경 설정 및 PC 변경 가이드

## 1. 필요한 프로그램

- Visual Studio Code: https://code.visualstudio.com/download
- Python 3.13 (64-bit): https://www.python.org/downloads/windows/
- Git for Windows: https://git-scm.com/download/win
- Chrome 등 브라우저: AWS 콘솔 및 Grafana
- 화면 녹화 프로그램 (예: OBS Studio): 최종 MP4 녹화

VS Code 확장: Microsoft Python 및 Pylance 권장. Docker, CUDA, WSL, Blender 및 로컬 AWS CLI는 현 단계에서 필수가 아니다. CloudShell에 AWS CLI가 포함되어 있다.

## 2. 새 데스크톱에서 최초 실행

PowerShell에서 설치 확인:

```powershell
py -0p
py -3.13 --version
git --version
```

Python 3.13이 없다면 공식 설치 페이지에서 설치한다. Windows의 python 명령이 WindowsApps 별칭을 가리키더라도 py -3.13이 정상 작동하면 그대로 사용 가능하다.

원하는 폴더에서 저장소를 내려받는다. 아래 예시는 바탕화면이며 경로 변경 가능하다.

```powershell
Set-Location ([Environment]::GetFolderPath('Desktop'))
git clone https://github.com/darkkyoung/Ajou_AIoT.git
Set-Location Ajou_AIoT
code .
```

code 명령이 없으면 VS Code의 File → Open Folder에서 Ajou_AIoT 폴더를 선택한다. 기존 clone이 있다면 다시 clone하지 말고 해당 폴더에서 git status와 git pull --ff-only를 실행한다. 기존 파일이 있는 과제 폴더에 강제로 clone하지 않는다.

## 3. 패키지 설정

간단한 방식 (이미 Python을 설치했고 프로젝트 전용 환경이 필요하지 않을 때):

```powershell
py -3.13 -m pip install -r hw2/requirements.txt
py -3.13 -c "import numpy, pandas, sklearn, matplotlib; print('SUCCESS')"
py -3.13 hw2/simulation.py
py -3.13 -m unittest discover -s hw2 -p "test_*.py"
```

권장 격리 방식 (다른 프로젝트와 패키지 충돌 방지):

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r hw2/requirements.txt
.\.venv\Scripts\python.exe -c "import numpy, pandas, sklearn, matplotlib; print('SUCCESS')"
.\.venv\Scripts\python.exe hw2/simulation.py
.\.venv\Scripts\python.exe -m unittest discover -s hw2 -p "test_*.py"
```

VS Code에서 Ctrl+Shift+P → Python: Select Interpreter로 사용할 인터프리터를 지정한다. 새 PC로 옮길 때 .venv 폴더를 복사하지 않고 재생성한다. 정확한 패키지 버전은 실제 학습 검증이 끝난 뒤 별도로 기록한다.

## 4. 작업 이어가기

- 기존 clone에서 git status 확인, 변경사항을 커밋하거나 안전하게 보관한 다음 git pull --ff-only.
- 현재 단계와 미검증 항목은 docs/DEVLOG.md 확인.
- 생성 데이터는 hw2/data/sensor_data.csv에 저장되며 재실행 가능하다.
- 각 단계가 검증되면 관련 소스와 개발 일지를 커밋/푸시한다. 비밀키, 계정 정보, 개인 경로, 학번, 제출 자료, 원본 강의자료를 커밋하지 않는다.
- 제공된 강의실/컴퓨터실 GLB 모델은 로컬 원본 에셋 팩에서 준비한다. 공개 저장소에 포함하지 않았다.

## 5. AWS (로컬 검증 완료 후)

1. 기존 AWS 계정 로그인, 서울 리전(ap-northeast-2) 선택, 크레딧/비용 알림 및 서비스 이용 가능 여부 확인.
2. CloudShell: https://console.aws.amazon.com/cloudshell/home?region=ap-northeast-2
3. CloudShell에서 aws --version과 aws sts get-caller-identity로 인증 확인. 응답은 외부에 공유하지 않는다. 별도 액세스 키 발급 불필요.
4. HW2 전용 aiot-hw2 접두어로 리소스 생성. HW1 자원은 이전에 삭제했으므로 재사용 여부를 확인하고 Identity Center만 필요시 기존 설정 재사용.
5. Windows용 scikit-learn 바이너리를 Lambda에 그대로 배포하지 않는다. 최종 모델의 계수 또는 트리 구조를 JSON으로 내보내 순수 Python 추론을 검증할 계획이다.
6. HW1의 ExecuteQuery 권한 오류와 S3 CORS 문제를 사전에 점검한다. AWS 자원 생성·삭제는 단계별로 확인한다.

현재는 로컬 시뮬레이터 단계이며 AWS 배포 코드/실제 클라우드 검증은 아직 준비되지 않았다. 영상과 보고서 증빙 확보 후에만 AWS 정리 작업을 진행한다.

## 6. STEP 2 시뮬레이터 실행 모드

저장소 루트에서 다음 명령 실행 (가상환경 사용 시 Python 실행 경로만 변경).

```powershell
git pull --ff-only
py -3.13 hw2/simulation.py
py -3.13 -m unittest discover -s hw2 -p "test_*.py" -v
py -3.13 hw2/simulation.py --mode demo --steps 3
py -3.13 hw2/simulation.py --mode live --steps 2
```

batch는 센서 기록과 5분 조건부 정답 CSV 각각 10,800행을 생성한다. demo는 첫 기록 즉시 출력 후 10초 간격, live는 60초 간격이며 두 공간의 JSON을 콘솔로 출력한다. steps는 공간별 기록 수다. 시계 모드는 AI 제어 또는 AWS 연동이 아니라 로컬 센서 시연이다. Ctrl+C로 중단 가능. 생성 CSV는 Git에서 제외하고 다시 생성한다.

## 7. STEP 3 모델 학습

```powershell
git pull --ff-only
py -3.13 hw2/simulation.py
py -3.13 hw2/train.py
```

추가 패키지 설치 불필요. hw2/results/step3/metrics.json에서 분할, 모델 평가, 선택 모델 및 export parity 확인. model_mae.png와 predictions.png는 보고서 증빙. hw2/models/selected_model.json은 다음 STEP 4에서 사용. 새 PC에서는 다시 학습하여 생성한다. scikit-learn 버전 차이로 결과에 차이가 날 수 있으며 기준 검증 환경은 Python 3.13.5/sklearn 1.8.0이다. AWS 실제 추론은 이후 검증한다.

## 8. STEP 4 제어 실험

저장소 루트에서 실행. 새 PC는 먼저 simulation.py 및 train.py 실행하여 모델 생성.

```powershell
git pull --ff-only origin main
py -3.13 hw2/evaluate.py
py -3.13 -m unittest discover -s hw2 -p "test_*.py" -v
py -3.13 hw2/control.py --mode demo --steps 3
```

실험 결과는 hw2/results/step4/에 생성. 로컬 live는 --mode live, 60초 간격. demo는 10초 간격. 시작 기록 즉시 출력, 이후 1분의 가상 시뮬레이션을 진행한다. 실제 센서/클라우드 제어는 아직 없음. git pull 기본 명령에서 multiple branches 오류가 나면 origin main을 명시하고 설정은 강제로 변경하지 않는다.

## 9. STEP 5 AWS 접속 전 준비

[STEP5_PREP.md](STEP5_PREP.md)의 Windows 테스트 및 build_package.py 실행 절차를 따른다. 원본 에셋 ZIP은 각 PC에서 경로를 지정한다. AWS 자격증명이나 계정 ID는 필요 없다. 생성된 dist 폴더는 로컬에 보존한다.
