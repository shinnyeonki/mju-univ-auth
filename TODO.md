- 사용자의 아이디 비밀번호 틀릴때 에러처리로 하지 말고 t/f 로 반환해서 사용자가 올바르게 분기 처리가 쉽도록 하는 것이 어떨까?

예시 반환 형태 어떤 방식을 사용하는 것이 좋을까??
```
AuthResponse
AuthResponse(
  is_auth=True,
  code='success',
  body={
    'name': '최현민', 
    'department': '컴퓨터과학전공', 
    'email': 'choihm9903@naver.com'
  }
)
is_auth: 인증 성공 여부
Type: bool
Value
True: 인증 성공
False: 인증 실패
code: Authenticator 반환 코드
Type: str
Value
'success': 인증에 성공할 경우
'auth_failed': 인증에 실패할 경우
'unknown_issue': 기타 라이브러리 오류
body: 메타데이터
Type: dict
Key
name: 이름
department: 학과
email: 이메일
```


```
AuthResponse
인증의 결과는 Nametuple의 형태로 반환됩니다.

AuthResponse(
	success=True, 
	is_auth=True, 
	status_code=200, 
	code='success', 
	body={
		'name': '신희재', 
		'major': '컴퓨터공학과'
	}, 
	authenticator='DosejongSession'
)
success: 인증 서버 정상 동작 여부

해당 인증 절차에 대하여 서버는 정상적인 결과를 반환하였습니다.
Value: True / False
is_auth: 인증 성공 여부

id/pw가 정확하더라도 서버의 상태 이상 및 인증 포맷이 갱신되어 라이브러리의 방식과 상이할 경우 인증 성공을 반드시 보장할 수 없습니다.
인증 결과를 알 수 없을 경우, None이 반환됩니다.
Value: True / False / None
status_code: 인증 서버의 HTTP status code

Value: int
code: Authenticator 반환 코드

인증이 성공할 경우, 'success'로 통일합니다.
인증이 실패 및 알 수 없을 경우, 각각의 분기에 맞는 코드 값을 반환합니다.
Value: string
body: 메타데이터

인증 결과에 관련된 메타데이터를 포함합니다.
인증 실패시의 보다 정확한 실패 사유
이름/학번/학년/재학 상태 등의 추가 정보
Value: dict
authenticator: 해당 인증에 사용된 Authenticator 클래스
```