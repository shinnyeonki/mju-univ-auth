# MJU Univ Auth API

명지대학교 학생 인증 및 정보 조회 API입니다.

**베이스 URL:** `https://mju-univ-auth.shinnk.kro.kr`

---

## API 엔드포인트

### 1. 학생 기본 정보 조회

**POST** `https://mju-univ-auth.shinnk.kro.kr/api/v1/student-basicinfo`

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
    "department": "컴퓨터정보통신공학부 컴퓨터공학전공",
    "category": "대학",
    "grade": "4",
    "last_access_time": "2025-xx-xx xx:xx:xx",
    "last_access_ip": "xxx.xxx.xxx.xxx",
    "raw_html_data": "<div class=\"card-item main-user-info\">...</div>"
  },
  "error_code": null,
  "error_message": "",
  "success": true
}
```

필드 설명:

- `department` (string): 소속 학부/학과
- `category` (string): 구분 (예: 대학)
- `grade` (string): 학년
- `last_access_time` (string): 최근 접속 시간
- `last_access_ip` (string): 최근 접속 IP
- `raw_html_data` (string): 원본 HTML 데이터

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

### 2. 학생카드 정보 조회

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
    "student_profile": {
      "student_id": "60xxxxxx",
      "name_korean": "xxx",
      "grade": "4",
      "enrollment_status": "재학",
      "college_department": "(반도체·ICT대학) 컴퓨터정보통신공학부 컴퓨터공학전공",
      "academic_advisor": "xxx (컴퓨터정보통신공학부 컴퓨터공학전공)",
      "student_designed_major_advisor": "",
      "photo_base64": "/9j/... (base64 생략)"
    },
    "personal_contact": {
      "english_surname": "XXX",
      "english_givenname": "XXX XXX",
      "phone_number": "xxx-xxxx-xxxx",
      "mobile_number": "xxxxxxxxxxx",
      "email": "xxx@mju.ac.kr",
      "current_residence_address": {
        "postal_code": "xxx-xxx",
        "address": "xx도 xx시 xx구 xx로 xx xx동 xx호"
      },
      "resident_registration_address": {
        "postal_code": "xxx-xxx",
        "address": "xx도 xx시 xx구 xx로 xx xx동 xx호"
      }
    },
    "raw_html_data": "<div class=\"card-item basic\">...</div>"
  },
  "error_code": null,
  "error_message": "",
  "success": true
}
```

아래 필드들은 일부 응답에서 생략될 수 있으며, `null` 또는 빈 문자열로 반환될 수 있습니다.

**student_profile 필드 설명:**

- `student_id` (string): 학번
- `name_korean` (string): 한글 이름
- `grade` (string): 학년
- `enrollment_status` (string): 학적 상태 (예: `재학`, `휴학`)
- `college_department` (string): 소속 학부/학과
- `academic_advisor` (string): 상담교수
- `student_designed_major_advisor` (string): 학생설계전공 지도교수
- `photo_base64` (string): 프로필 사진 (Base64 인코딩 문자열) — 큰 사이즈 가능, 필요하면 클라이언트에서 처리/다운로드 권장

**personal_contact 필드 설명:**

- `english_surname` (string): 영문 성
- `english_givenname` (string): 영문 이름
- `phone_number` (string): 전화번호
- `mobile_number` (string): 휴대전화
- `email` (string): 학교 이메일
- `current_residence_address` (object): 현거주지 주소 (postal_code, address)
- `resident_registration_address` (object): 주민등록 주소 (postal_code, address)

- `raw_html_data` (string): 원본 HTML 데이터

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

### 3. 학적변동내역 조회

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
    "academic_status": {
      "student_id": "60xxxxxx",
      "name": "xxx",
      "status": "재학",
      "grade": "4",
      "completed_semesters": "7",
      "department": "컴퓨터정보통신공학부 컴퓨터공학전공"
    },
    "cumulative_leave_semesters": "총 0학기",
    "change_log_list": [],
    "raw_html_data": "<div class=\"card-item basic\">...</div>"
  },
  "error_code": null,
  "error_message": "",
  "success": true
}
```

**academic_status 필드 설명:**

- `student_id` (string): 학번
- `name` (string): 이름
- `status` (string): 학적 상태
- `grade` (string): 학년
- `completed_semesters` (string): 이수 학기 수
- `department` (string): 학부/학과

- `cumulative_leave_semesters` (string): 누적 휴학 학기
- `change_log_list` (array): 변동 내역 목록 (각 항목: 년도, 학기, 변동유형, 변동일자, 만료일자, 사유)
- `raw_html_data` (string): 원본 HTML 데이터

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

#### 학생 기본 정보 조회
```bash
curl -X POST "https://mju-univ-auth.shinnk.kro.kr/api/v1/student-basicinfo" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "60xxxxxx", "user_pw": "your_password"}'
```

#### 학생카드 정보 조회
```bash
curl -X POST "https://mju-univ-auth.shinnk.kro.kr/api/v1/student-card" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "60xxxxxx", "user_pw": "your_password"}'
```

#### 학적변동내역 조회
```bash
curl -X POST "https://mju-univ-auth.shinnk.kro.kr/api/v1/student-changelog" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "60xxxxxx", "user_pw": "your_password"}'
```

### Python
```python
import requests

# 학생 기본 정보 조회
response = requests.post(
  "https://mju-univ-auth.shinnk.kro.kr/api/v1/student-basicinfo",
  json={"user_id": "60xxxxxx", "user_pw": "your_password"}
)

# 학생카드 정보 조회
response = requests.post(
  "https://mju-univ-auth.shinnk.kro.kr/api/v1/student-card",
  json={"user_id": "60xxxxxx", "user_pw": "your_password"}
)

# 학적변동내역 조회
response = requests.post(
  "https://mju-univ-auth.shinnk.kro.kr/api/v1/student-changelog",
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
// 학생 기본 정보 조회
fetch('https://mju-univ-auth.shinnk.kro.kr/api/v1/student-basicinfo', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ user_id: '60xxxxxx', user_pw: 'your_password' })
})
  .then(res => res.json())
  .then(result => {
    if (result.success) {
      console.log('학생 기본 정보:', result.data);
    } else {
      console.error('에러:', result.error_message);
    }
  });

// 학생카드 정보 조회
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

// 학적변동내역 조회
fetch('https://mju-univ-auth.shinnk.kro.kr/api/v1/student-changelog', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ user_id: '60xxxxxx', user_pw: 'your_password' })
})
  .then(res => res.json())
  .then(result => {
    if (result.success) {
      console.log('학적변동내역:', result.data);
    } else {
      console.error('에러:', result.error_message);
    }
  });
```

---

⚠️ **주의:** 이 API는 학생의 민감한 정보를 다룹니다. 안전하게 사용해 주세요.
