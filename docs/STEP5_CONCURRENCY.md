# STEP 5 — 동시성 보호 보완 및 재배포

## 실제 확인된 결과 (사용자 CloudShell)
- 1588ea7 로컬: 기존 10/10, AWS fake-S3 6/6, 배포 패키지 생성 성공. 모델 SHA256 565da9378788149d6b10d70e61544caaef0ccf0694263de1abe9d68831d80405.
- S3 서울 리전, 공개 접근 차단 4/4, GLB 2개 해시 일치. 두 Lambda Python 3.12 Active. IAM 역할 및 권한 부여 성공.
- 예약 동시 실행 설정 실패: 계정 총 10, 미예약 10, 최소 미예약 10. Scheduler 미생성.
- 2026-11-27 14:48/14:52 UTC 생성 호출 2회 성공. 두 공간의 상태 연속성 PASS. 조회 Lambda 직접 호출에서 6개 속성 × 2공간 × 2시점 일치. TwinMaker 실제 조회는 아직 미검증.
- 현재 관측값 강의실 672.75→675.80, 컴퓨터실 779.87→784.85 ppm. 두 시점 모두 normal/20%. 성공 호출당 가상 시간 1분. 실제 4분 간격은 수동 테스트이며 누락된 3분은 소급 생성하지 않는다.

## 변경 사항
- 생성 함수가 S3의 sensor-data/locks/generate.lock에 IfNoneMatch=* 조건부 PutObject로 배타 잠금을 확보한 뒤 전체 read/compute/write를 수행한다. 다른 시간 슬롯의 동시 호출도 잠금 실패 시 busy로 반환, 상태 갱신하지 않는다. 기존 journal 형식 및 기록은 유지.
- finally에서 자신이 확보한 ETag로 IfMatch 조건부 DeleteObject. 잠금은 자동 탈취하지 않는다. 런타임 강제 종료/통신 장애 시 잠금이 남을 수 있어 fail-closed(데이터 일관성 우선). Scheduler 및 다른 모든 writer를 중지하고 마지막 호출 종료(60초 timeout 이상 및 비동기 대기 호출 확인) 후 관리자만 해당 잠금 객체를 삭제한다. 실제 센서 기록 삭제 금지. 평상시 busy는 로그에서 감시한다.
- 기존 생성 IAM 정책에 정확히 이 잠금 객체에 한해 s3:PutObject, s3:GetObject, s3:DeleteObject 추가. GetObject는 ETag 기반 조건부 삭제에 필요. 조회 역할 수정 불필요.
- 기존 journal 중복 방지 IfNoneMatch 유지. 예약 동시 실행 1은 더 이상 필수 아님. 단, 모든 생성 호출은 동일한 잠금 코드를 사용해야 함. S3 SDK DeleteObject IfMatch 지원은 실제 Lambda에서 확인.
- AWS 공식: https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html ; https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-deletes.html

## 로컬 검증 및 재배포 전 준비 (PowerShell)
```powershell
git pull --ff-only origin main
$env:PYTHONPATH = "$PWD\hw2;$PWD\hw2\aws"
py -3.13 -m unittest discover -s hw2/aws -p "test_*.py" -v
Remove-Item Env:PYTHONPATH
py -3.13 hw2/aws/build_package.py --assets "..\ClassroomAssetPack GLTF & FBX.zip"
```
기존 6개 + lock 테스트 2개 = 8개 예상. 실제 테스트와 패키징은 사용자 PC에서 확인 필요. 모델 다시 학습하지 않음. generate.zip만 CloudShell에 교체 업로드 후 IAM 잠금 권한 추가, update-function-code, wait function-updated-v2, 수동 호출 및 잠금 해제 확인. 기존 S3/GLB/reader Lambda는 유지. Scheduler 생성은 실제 검증 이후.
