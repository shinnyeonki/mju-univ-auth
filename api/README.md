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
  "password": "비밀번호"
}
```

**✅ 성공 응답 (200 OK)**
```json
{
  "success": true,
  "data": {
    "name": "홍길동",
    "student_id": "60xxxxxx",
    "department": "컴퓨터공학과",
    "grade": "3",
    "status": "재학"
  }
}
```

**❌ 실패 응답**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "아이디 또는 비밀번호가 틀렸습니다."
  }
}
```

---

### 2. 학적변동내역 조회

**POST** `https://mju-univ-auth.shinnk.kro.kr/api/v1/student-changelog`

**요청:**
```json
{
  "user_id": "학번",
  "password": "비밀번호"
}
```

**✅ 성공 응답 (200 OK)**
```json
{
  "success": true,
  "data": {
    "changes": [
      {
        "date": "2023-03-02",
        "type": "입학",
        "details": "신입학"
      }
    ]
  }
}
```

**❌ 실패 응답**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "에러 메시지"
  }
}
```

---

## 에러 코드

| HTTP 상태 | 에러 코드 | 발생 상황 |
|-----------|----------|-----------|
| 401 | `INVALID_CREDENTIALS` | 학번이나 비밀번호가 잘못됨 |
| 408 | `NETWORK_TIMEOUT`  | 학교 서버가 응답하지 않음 |
| 502 | `NETWORK_ERROR`  | 학교 서버와 네트워크 연결 문제 |
| 500 | `PAGE_PARSING_ERROR`  | 학교 웹페이지 구조 변경 |
| 503 | `SESSION_EXPIRED`  | 학교 서버 세션 만료 (재시도 필요) |
| 500 | `INTERNAL_SERVER_ERROR` | 서버 내부 오류, 라이브러리 오류 |

---

## 사용 예시

### cURL
```bash
curl -X POST "https://mju-univ-auth.shinnk.kro.kr/api/v1/student-card" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "60xxxxxx", "password": "your_password"}'
```

### Python
```python
import requests

response = requests.post(
    "https://mju-univ-auth.shinnk.kro.kr/api/v1/student-card",
    json={"user_id": "60xxxxxx", "password": "your_password"}
)

result = response.json()
if result["success"]:
    print("학생 정보:", result["data"])
else:
    print("에러:", result["error"]["message"])
```

### JavaScript
```javascript
fetch('https://mju-univ-auth.shinnk.kro.kr/api/v1/student-card', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ user_id: '60xxxxxx', password: 'your_password' })
})
  .then(res => res.json())
  .then(result => {
    if (result.success) {
      console.log('학생 정보:', result.data);
    } else {
      console.error('에러:', result.error.message);
    }
  });
```

---

⚠️ **주의:** 이 API는 학생의 민감한 정보를 다룹니다. 안전하게 사용해 주세요.
