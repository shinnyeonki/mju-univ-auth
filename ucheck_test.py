from mju_univ_auth import MjuUnivAuth
import json
from bs4 import BeautifulSoup



auth = MjuUnivAuth(user_id="60222100", user_pw="Jaja8794@", verbose=True).login("ucheck")

result = auth.get_session()

if not result.success:
    print(f"세션 획득 실패: {result.error_message}")
    exit(1)

session = auth.session

# 로그인 후 메인 페이지에 접근하여 세션 유지
main_page_response = session.get("https://ucheck.mju.ac.kr/")
if main_page_response.status_code != 200:
    print(f"메인 페이지 접근 실패: {main_page_response.status_code}")
    exit(1)

print("메인 페이지 접근 성공")

# 메인 페이지에서 현재 yearterm 파싱
soup = BeautifulSoup(main_page_response.text, 'html.parser')
select = soup.find('select', id='select-yearterm')
current_yearterm = '2025:1'  # default
if select:
    options = select.find_all('option')
    for option in options:
        if 'selected' in option.attrs:
            current_yearterm = option['value']
            break
    else:
        if options:
            current_yearterm = options[0]['value']

year = "2025"
term = "1"

print(f"현재 yearterm: {current_yearterm}")

# [requests.session 객체 사용] ajax로 출석확인 페이지 데이터 요청
headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Origin': 'https://ucheck.mju.ac.kr',
    'Pragma': 'no-cache',
    'Referer': 'https://ucheck.mju.ac.kr/',
    'Sec-Ch-Ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"macOS"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}
response = session.post("https://ucheck.mju.ac.kr/lecture/lecture/student/getStudentLectureList.do", headers=headers, params={"lecture_year": "2025", "lecture_term": "1"})

if response.status_code == 200:
    print("AJAX 요청 성공")
    try:
        data = response.json()
        print("응답 데이터:")
        print(json.dumps(data, indent=4, ensure_ascii=False))
    except json.JSONDecodeError:
        print("응답이 JSON이 아닙니다. 텍스트 응답:")
        print(response.text)
else:
    print(f"AJAX 요청 실패: {response.status_code}")
    print(response.text)

