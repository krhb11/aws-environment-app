# 도서 추천 RAG 기본 개발 환경

기획서에 필요한 AWS 실행 환경·저장소·접근 권한만 구성합니다. **도서 수집, 임베딩 데이터 적재, 도서 검색, 추천 챗봇 기능은 구현하지 않았습니다.**

## 추가한 기본 환경

- 비공개 S3 웹 버킷 + CloudFront HTTPS 배포, Origin Access Control
- 비공개 S3 데이터 버킷의 `raw/`, `processed/` 준비 위치 (도서 데이터 없음)
- S3 Vectors 벡터 버킷과 `book-descriptions` 인덱스: float32, 256차원, cosine, 빈 인덱스
- Lambda 실행 역할에 지정 저장소 읽기 및 지정 Bedrock 모델 호출 권한 부여
- Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`) 및 APAC Nova Micro (`apac.amazon.nova-micro-v1:0`)
- 기존 API에 `GET /dev/api/environment` 추가, CloudFront에서는 `/api/environment`로 호출

환경 확인 API는 S3 위치와 벡터 인덱스에 읽기 요청만 수행합니다. 공개 API에서 모델을 호출하거나 데이터를 적재하지 않습니다. 모델 접근 검사는 관리자가 Lambda에 `{"action":"model_access_check"}` 테스트 이벤트를 직접 호출할 때에만 실행됩니다. CloudFront 페이지는 환경 확인용이며 챗봇 화면이 아닙니다.

## CloudShell에서 재현

인증된 CloudShell에 배포 ZIP을 업로드하고 `python3 rag-environment.zip`을 실행합니다. ZIP의 `__main__.py`는 `deploy_environment.py`를 실행합니다. 이 스크립트는 기존 `codex-env-20261125` 스택을 업데이트하고 테스트 웹 페이지 업로드, 저장소 점검 및 관리용 모델 연결 검사 결과를 기록합니다. AWS 자격 증명을 코드에 넣지 않습니다.

`cloudformation.json`이 전체 인프라의 재배포 원본입니다. Lambda 인라인 코드와 `index.py`는 동일합니다. 기본 개발 환경 검증은 `python -m unittest test_handler test_environment -v`로 실행합니다.

## 기존 API와 개발 도구

개발 도구: **Codex**. Python 3.12 Lambda, API Gateway HTTP API, DynamoDB, IAM, CloudWatch를 CloudFormation으로 구성합니다.

## API

- `GET /dev/health`: 실행 상태와 개발 도구 확인
- `GET /dev/storage-check`: 고정된 테스트 항목 1개를 DynamoDB에 저장한 뒤 강력한 일관성 읽기로 검증
- 정의되지 않은 경로나 메서드는 404

실습 전용 공개 API이며 개인정보나 비밀값을 입력받지 않습니다. 저장소 검증은 같은 키를 갱신하므로 항목 수가 늘어나지 않습니다. 스테이지 요청 제한은 초당 1회, 버스트 2회이며 하드 비용 한도는 아닙니다.

## 로컬 검증

```bash
python -m unittest test_handler -v
```

## 배포

AWS 콘솔 CloudFormation에서 `cloudformation.json`을 업로드하고 스택 이름을 `codex-env-20261125`로 지정합니다. IAM 리소스 생성 기능을 확인한 뒤 배포합니다. 또는 AWS CLI가 인증된 환경에서:

```bash
aws cloudformation deploy --template-file cloudformation.json --stack-name codex-env-20261125 --capabilities CAPABILITY_IAM --region ap-northeast-2
aws cloudformation describe-stacks --stack-name codex-env-20261125 --region ap-northeast-2 --query 'Stacks[0].Outputs'
```

스택 출력의 HealthUrl과 StorageCheckUrl을 호출하여 HTTP 200과 `status: ok`, `storage: ok`를 확인합니다. `/aws/lambda/codex-env-20261125` 로그 그룹에서 request_id를 대조합니다.

## 권한 및 비용

실행 역할은 기존 DynamoDB 테스트 테이블의 GetItem/PutItem, 해당 로그 그룹의 CreateLogStream/PutLogEvents와 추가 개발 저장소·모델에 필요한 권한을 허용합니다. S3 데이터 읽기는 raw/ 및 processed/ 접두사로 한정하고 벡터 인덱스 권한은 해당 인덱스 ARN으로 제한합니다. 자격 증명은 저장소에 포함하지 않습니다. Lambda는 256MB, 제한 시간 20초이며 로그 보존 기간은 7일입니다. DynamoDB는 기존 테스트 API를 위해 유지하며 RAG 문서·벡터 저장소로 사용하지 않습니다. AWS 사용량과 저장량에 따른 요금이 발생할 수 있습니다.

실습 종료 후 필요할 때 CloudFormation 스택을 삭제하면 이 스택이 만든 리소스의 삭제가 시도됩니다. 테이블 데이터와 로그는 삭제되므로 보관이 필요하면 먼저 내보내야 합니다. S3 버킷과 벡터 인덱스는 내용이 있으면 삭제 전에 비워야 합니다. 웹 배포 파일과 데이터 버킷의 빈 접두사 객체도 삭제 대상입니다. 업로드용 cf-templates S3 버킷은 스택 외부에 남을 수 있습니다.


## 배포 주소

- Health: https://9iluknvlza.execute-api.ap-northeast-2.amazonaws.com/dev/health
- Storage: https://9iluknvlza.execute-api.ap-northeast-2.amazonaws.com/dev/storage-check
- GitHub: https://github.com/krhb11/aws-environment-app (Private)
