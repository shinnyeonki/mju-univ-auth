"""
명지대학교 서버 동시 로그인 테스트 스크립트
=========================================
여러 스레드를 사용하여 `mju-univ-auth` 라이브러리로 동시 로그인을 시도하고,
서버의 Rate Limiting 동작을 확인합니다.

실행 전:
- `pip install python-dotenv`
- `.env` 파일에 MJU_ID와 MJU_PW 설정

실행:
- `python mju_concur_login.py`
"""

import os
import threading
import time
import logging
from dotenv import load_dotenv

# mju_univ_auth 라이브러리를 현재 프로젝트 경로에서 가져옵니다.
from mju_univ_auth import MjuUnivAuth, MjuUnivAuthResult

# 기본 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(message)s')

def attempt_login(thread_id: int, user_id: str, user_pw: str):
    """
    단일 로그인 작업을 수행하는 함수 (스레드에서 실행됨)
    """
    thread_name = f"Thread-{thread_id}"
    threading.current_thread().name = thread_name
    
    logging.info("로그인 시도 시작...")
    start_time = time.time()
    
    try:
        # 각 스레드는 독립적인 MjuUnivAuth 인스턴스를 생성합니다.
        # verbose=False로 설정하여 라이브러리 내부의 상세 로그는 출력하지 않습니다.
        auth = MjuUnivAuth(user_id=user_id, user_pw=user_pw, verbose=False)
        
        # login()은 체이닝을 위해 자기 자신을 반환합니다.
        # 실제 API 엔드포인트와 동일하게 get_student_card()를 직접 호출합니다.
        result: MjuUnivAuthResult = auth.get_student_card()
        
        duration = time.time() - start_time
        
        if result and result.success:
            logging.info(f"✅ 성공! (소요 시간: {duration:.2f}s)")
        else:
            logging.warning(f"❌ 실패. (소요 시간: {duration:.2f}s)")
            logging.warning(f"  - 에러 코드: {result.error_code}")
            logging.warning(f"  - 에러 메시지: {result.error_message}")
            
    except Exception as e:
        duration = time.time() - start_time
        logging.error(f"💥 예외 발생! (소요 시간: {duration:.2f}s)", exc_info=True)


def main():
    """
    메인 실행 함수
    """
    # .env 파일에서 환경 변수 로드
    load_dotenv()
    user_id = os.getenv('MJU_ID')
    user_pw = os.getenv('MJU_PW')

    if not user_id or not user_pw:
        print("오류: .env 파일에 MJU_ID와 MJU_PW를 설정해주세요.")
        print("예시:")
        print("MJU_ID=60xxxxxx")
        print("MJU_PW=your_password")
        return

    # 동시 테스트할 스레드 수
    num_threads = 5
    
    print("=" * 60)
    print(f"명지대학교 서버 동시 로그인 테스트 ({num_threads}개 스레드)")
    print("=" * 60)

    threads = []
    for i in range(num_threads):
        # 스레드 생성
        thread = threading.Thread(target=attempt_login, args=(i + 1, user_id, user_pw))
        threads.append(thread)
        # 스레드 시작
        thread.start()

    # 모든 스레드가 종료될 때까지 대기
    for thread in threads:
        thread.join()

    print("=" * 60)
    print("모든 테스트가 완료되었습니다.")
    print("결과를 확인하여 일부 요청이 실패하고 'NoneType' 관련 파싱 에러가 발생하는지 확인하세요.")
    print("=" * 60)


if __name__ == "__main__":
    main()
