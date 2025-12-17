# MJU Univ Auth API

명지대학교 학생 인증 및 정보 조회 API입니다.

**베이스 URL:** `https://mju-univ-auth.shinnk.kro.kr`

---

## API 엔드포인트

### 1. 학생카드 정보 조회

**POST** `https://mju-univ-auth.shinnk.kro.kr/api/v1/student-card`

**요청:**
```json
{
  "user_id": "학번",
  "user_pw": "비밀번호"
}
```

**✅ 성공 응답 (200 OK)**
```json
{
  "request_succeeded": true,
  "credentials_valid": true,
  "data": {
    "student_id": "60xxxxxx",
    "name_korean": "xxx",
    "name_english": "XXX XXX",
    "grade": "x",
    "status": "재학",
    "department": "(반도체·ICT대학) 컴퓨터정보통신공학부 컴퓨터공학전공",
    "advisor": "xxx (컴퓨터정보통신공학부 컴퓨터공학전공)",
    "design_advisor": "()",
    "phone": "",
    "mobile": "xxx-xxxx-xxxx",
    "email": "xxx@mju.ac.kr",
    "current_address": "(xxx-xxx) xx도 xx시 xx구 xx로 xx xx동 xx호",
    "registered_address": "(xxx-xxx) xx도 xx시 xx구 xx로 xx xx동 xx호",
    "photo_base64": "/9j/... (base64 생략)",
    "focus_newsletter": false,
    "completed_semesters": "7"
  },
  "error_code": null,
  "error_message": "",
  "success": true
}
```

아래 필드들은 일부 응답에서 생략될 수 있으며, `null` 또는 빈 문자열로 반환될 수 있습니다.

필드 설명:

- `student_id` (string): 학번
- `name_korean` (string): 한글 이름
- `name_english` (string): 영문 이름 (합쳐진 형태)
- `grade` (string): 학년
- `status` (string): 학적 상태 (예: `재학`, `휴학`)
- `department` (string): 소속 학부/학과
- `advisor` (string): 상담교수
- `design_advisor` (string): 학생설계전공 지도교수
- `phone` (string): 전화번호 (지국)
- `mobile` (string): 휴대전화
- `email` (string): 학교 이메일
- `current_address` (string): 현거주지 전체 주소 (우편번호 포함)
- `registered_address` (string): 주민등록 주소 (우편번호 포함)
- `photo_base64` (string): 프로필 사진 (Base64 인코딩 문자열) — 큰 사이즈 가능, 필요하면 클라이언트에서 처리/다운로드 권장
- `focus_newsletter` (boolean): 명지포커스 수신 여부
- `completed_semesters` (string, optional): 이수 학기 수 (일부 응답에 포함될 수 있습니다)

**❌ 실패 응답**
```json
{
  "request_succeeded": true,
  "credentials_valid": false,
  "data": null,
  "error_code": "INVALID_CREDENTIALS",
  "error_message": "아이디 또는 비밀번호가 틀렸습니다.",
  "success": false
}
```

---

### 2. 학적변동내역 조회

**POST** `https://mju-univ-auth.shinnk.kro.kr/api/v1/student-changelog`

**요청:**
```json
{
  "user_id": "학번",
  "user_pw": "비밀번호"
}
```

**✅ 성공 응답 (200 OK)**
```json
{
  "request_succeeded": true,
  "credentials_valid": true,
  "data": {
    "student_id": "60xxxxxx",
    "name": "xxx",
    "status": "재학",
    "grade": "x",
    "completed_semesters": "x",
    "department": "컴퓨터정보통신공학부 컴퓨터공학전공"
  },
  "error_code": null,
  "error_message": "",
  "success": true
}
```

**❌ 실패 응답**
```json
{
  "request_succeeded": true,
  "credentials_valid": false,
  "data": null,
  "error_code": "ERROR_CODE",
  "error_message": "에러 메시지",
  "success": false
}
```

---

## 에러 코드

| HTTP 상태 | 에러 코드 | 발생 상황 |
|-----------|----------|-----------|
| 401 | `INVALID_CREDENTIALS` | 학번이나 비밀번호가 잘못됨 |
| 401 | `SESSION_NOT_EXIST_ERROR` | 로그인을 하지 않아 세션이 없는 상태 |
| 401 | `SESSION_EXPIRED_ERROR` | 세션이 만료됨 (재로그인 필요) |
| 403 | `INVALID_SERVICE_USAGE_ERROR` | 현재 로그인된 서비스로 해당 기능을 사용할 수 없음 |
| 409 | `ALREADY_LOGGED_IN_ERROR` | 이미 로그인된 상태에서 다시 로그인을 시도함 |
| 422 | `SERVICE_NOT_FOUND_ERROR` | 지원하지 않는 서비스 이름을 사용함 |
| 502 | `NETWORK_ERROR` | 명지대 서버와 통신 실패 (타임아웃 포함) |
| 500 | `PARSING_ERROR` | 명지대 웹페이지 구조 변경으로 파싱 실패 |
| 500 | `UNKNOWN_ERROR` | 서버 내부 오류, 라이브러리 내부의 일반적인 오류 |

---

## 사용 예시

### cURL
```bash
curl -X POST "https://mju-univ-auth.shinnk.kro.kr/api/v1/student-card" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "60xxxxxx", "user_pw": "your_password"}'
```

### Python
```python
import requests

response = requests.post(
  "https://mju-univ-auth.shinnk.kro.kr/api/v1/student-card",
  json={"user_id": "60xxxxxx", "user_pw": "your_password"}
)

result = response.json()
if result["success"]:
    print("학생 정보:", result["data"])
else:
    print("에러:", result["error_message"])
```

### JavaScript
```javascript
fetch('https://mju-univ-auth.shinnk.kro.kr/api/v1/student-card', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ user_id: '60xxxxxx', user_pw: 'your_password' })
})
  .then(res => res.json())
  .then(result => {
    if (result.success) {
      console.log('학생 정보:', result.data);
    } else {
      console.error('에러:', result.error_message);
    }
  });
```

---

⚠️ **주의:** 이 API는 학생의 민감한 정보를 다룹니다. 안전하게 사용해 주세요.
