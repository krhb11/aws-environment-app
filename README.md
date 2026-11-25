# AWS 환경 구성 테스트 API

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

실행 역할은 해당 DynamoDB 테이블의 GetItem/PutItem, 해당 로그 그룹의 CreateLogStream/PutLogEvents만 허용합니다. 자격 증명은 저장소에 포함하지 않습니다. Lambda는 128MB, 제한 시간 10초이며 로그 보존 기간은 7일입니다. DynamoDB는 온디맨드 용량을 사용합니다. AWS 사용량과 저장량에 따른 요금이 발생할 수 있습니다.

실습 종료 후 필요할 때 CloudFormation 스택을 삭제하면 이 스택이 만든 리소스가 함께 삭제됩니다. 테이블 데이터와 로그도 삭제되므로 보관이 필요하면 먼저 내보내야 합니다.


## 배포 주소

- Health: https://9iluknvlza.execute-api.ap-northeast-2.amazonaws.com/dev/health
- Storage: https://9iluknvlza.execute-api.ap-northeast-2.amazonaws.com/dev/storage-check
- GitHub: https://github.com/krhb11/aws-environment-app (Private)
