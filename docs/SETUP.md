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
