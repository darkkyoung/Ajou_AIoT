# STEP 5 사전 준비 (AWS 미접속)

## 배포 전 검증
STEP 4 사용자 Windows 출력: commit 381dca7, 전체 단위 테스트 10/10 (0.176s), demo 두 공간 3 tick 성공(실제 10초/가상 60초). 모델 SHA256 565da9378788149d6b10d70e61544caaef0ccf0694263de1abe9d68831d80405. 제어 결과 일반/AI 1130/994 room-min, 초과 ppm-min 17134.94/14102.03, 평균 환기 45.11/45.81%, 전환 1440/1732. 기존 결과와 일치.

HW1 원본 Lambda 코드와 메타데이터를 참고. 원본 자격증명, 계정 식별자, 보고서 및 에셋은 공개 저장소에 게시하지 않음. AWS SDK 사용은 handler 내부로 제한하여 로컬 fake-S3 테스트에는 boto3가 필요 없다.

## 로컬 실행 (저장소 루트, PowerShell)

```powershell
git pull --ff-only origin main
py -3.13 -m unittest discover -s hw2 -p "test_*.py" -v
$env:PYTHONPATH = "$PWD\hw2;$PWD\hw2\aws"
py -3.13 -m unittest discover -s hw2/aws -p "test_*.py" -v
Remove-Item Env:PYTHONPATH
```

기존 10개 + AWS 어댑터 6개 테스트를 실행한다. AWS 테스트는 fake S3 및 가짜 선형 모델로 제어 연동/자료형/중복/페이지 처리를 확인하며 실제 AWS 검증이 아니다. 실제 RF는 STEP4에서 검증했고 빌드 시 해당 평가의 모델 해시와 비교한다.

원본 에셋 ZIP을 파일 탐색기로 찾아 경로를 지정한다. 예시: 저장소 상위 폴더에 원본 ZIP을 복사한 경우:

```powershell
py -3.13 hw2/aws/build_package.py --assets "..\ClassroomAssetPack GLTF & FBX.zip"
explorer .\hw2\aws\dist
```

기존 models/selected_model.json 및 results/step4/control_metrics.json 필요. 모델 파일을 다시 학습했으면 evaluate.py를 다시 실행. dist는 로컬 산출물이며 Git 제외. 생성/조회 ZIP, GLB 2개, property-definitions.json, manifest.json 생성. 실제 ZIP 내부에는 AWS 자격증명 없음.

## 설계
- 일반 버킷 S3의 sensor-data/ticks/YYYYMMDDTHHMMSSZ.json에 매 tick 두 공간 관측/제어 및 다음 상태를 한 객체로 저장. 마지막 객체에서 상태 복원. 상태 파일을 따로 쓰지 않는다.
- 단일 생성 Lambda, 예약 동시 실행(reserved concurrency)=1 필수. 다른 writer 금지. 동일/과거 slot 재호출은 skip, IfNoneMatch=*로 덮어쓰기 방지. 실패한 호출은 재시도 가능. 누락된 slot을 소급 생성하지 않고 성공한 호출당 가상 1분만 증가. 전체 키 목록 검색은 과제 규모 한정; 장기 운영에는 인덱스/상태 저장 설계 필요.
- live: Scheduler rate(1 minute), payload {"mode":"live","scheduled_time":"<aws.scheduler.scheduled-time>"}, FlexibleTimeWindow OFF. 데모는 Scheduler 비활성/실행 종료 확인 후 10초 간격 별도 동기 호출을 사용. Scheduler 자체의 10초 rate는 사용하지 않는다. mode 혼합 동시 실행 금지.
- timestamp는 정렬용 UTC slot; recorded_at은 실제 호출 시각, simulated_at은 가상 시간. 이전 환기 출력과 이번 결정 출력 구분.
- Reader DataReaderByEntity: classroom-01/computerlab-01, air_quality, 시간 범위/선택 속성/정렬/커서 페이지네이션. 최대 7일 조회, 250 samples/page. interpolation 및 propertyFilters는 미지원. 기본 범위 30분. Grafana는 30분 조회 및 10초 갱신으로 시작하되 실제 동작 검증 필요.
- TwinMaker dataType: CO2/예측/변화량 DOUBLE, 인원/환기/status_code INTEGER, status STRING. status_code 0/1/2 -> normal/warning/high. 아이콘 규칙은 STEP6. 두 공간 모두 같은 component type 사용.
- Lambda Python 3.12, handler lambda_function.lambda_handler, BUCKET_NAME 설정. 생성은 512 MB/60s, 조회 256~512 MB/60s부터 시작(실제 실행에 맞춰 조정). SDK 런타임에서 PutObject IfNoneMatch 지원 확인. Generator S3 ListBucket/GetObject/PutObject (journal prefix만), Reader ListBucket/GetObject (journal prefix만), 두 역할 CloudWatch logs. TwinMaker 역할 Lambda invoke, 모델 S3 접근; Grafana 읽기 역할 ExecuteQuery, GetPropertyValueHistory 등 및 S3 모델 read. 구체 ARN은 계정 접속 후 생성. 새 리소스명 aiot-hw2, 서울 리전. 기존 HW1 리소스나 기타 과제 변경 금지.
- AWS 공식 참고: https://docs.aws.amazon.com/iot-twinmaker/latest/guide/data-connector-interfaces.html ; https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html ; https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-schedule-context-attributes.html

## 아직 미완료
AWS 사전 코드는 작성됐지만, 이 커밋의 Python 실행 결과는 아직 확보하지 않았다. 사용자 PC에서 테스트/패키징 후 결과 확인. AWS 리소스 생성/배포, Scheduler 및 가속 호출, 실제 TwinMaker/Grafana 조회, IAM/CORS, 비용 확인은 다음 단계에서 진행한다.
