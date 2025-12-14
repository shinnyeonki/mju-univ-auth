
import os
import threading
import time
import logging
from dotenv import load_dotenv

# mju_univ_auth 라이브러리에서 필요한 클래스를 가져옵니다.
from mju_univ_auth import MjuUnivAuth, MjuUnivAuthResult
from mju_univ_auth.exceptions import MjuUnivAuthError

# 기본 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(message)s'
)

def attempt_login_and_get_card(user_id: str, user_pw: str):
    """
    지정된 사용자로 로그인하고 학생증 정보를 가져오는 함수 (스레드에서 실행됨)
    """
    thread_name = threading.current_thread().name
    logging.info(f"로그인 및 학생증 조회 시도 시작 (사용자: {user_id})...")
    start_time = time.time()
    
    try:
        # 각 스레드는 독립적인 MjuUnivAuth 인스턴스를 생성합니다.
        auth = MjuUnivAuth(user_id=user_id, user_pw=user_pw)
        
        # get_student_card()는 내부적으로 msi 로그인을 수행합니다.
        result: MjuUnivAuthResult = auth.get_student_card()
        
        duration = time.time() - start_time
        
        if result.success:
            student_info = result.data
            logging.info(
                f"✅ 성공! (사용자: {user_id}, 이름: {student_info.name_korean}, 학과: {student_info.department}) "
                f"(소요 시간: {duration:.2f}s)"
            )
        else:
            logging.warning(
                f"❌ 실패. (사용자: {user_id}) (소요 시간: {duration:.2f}s)\n"
                f"  - 에러 코드: {result.error_code}\n"
                f"  - 에러 메시지: {result.error_message}"
            )
            
    except MjuUnivAuthError as e:
        duration = time.time() - start_time
        logging.error(f"💥 라이브러리 예외 발생! (사용자: {user_id}) (소요 시간: {duration:.2f}s)\n  - {e}")
    except Exception:
        duration = time.time() - start_time
        logging.error(f"💥 예상치 못한 예외 발생! (사용자: {user_id}) (소요 시간: {duration:.2f}s)", exc_info=True)


def main():
    """
    메인 실행 함수
    """
    # .env 파일에서 환경 변수 로드
    load_dotenv()
    user_id_1 = os.getenv('MJU_ID_1')
    user_pw_1 = os.getenv('MJU_PW_1')
    user_id_2 = os.getenv('MJU_ID_2')
    user_pw_2 = os.getenv('MJU_PW_2')

    if not all([user_id_1, user_pw_1, user_id_2, user_pw_2]):
        print("오류: .env 파일에 아래 4개의 환경 변수를 모두 설정해주세요.")
        print("MJU_ID_1=<첫 번째 사용자 ID>")
        print("MJU_PW_1=<첫 번째 사용자 PW>")
        print("MJU_ID_2=<두 번째 사용자 ID>")
        print("MJU_PW_2=<두 번째 사용자 PW>")
        return

    print("=" * 70)
    print("서로 다른 명지대학교 계정 동시 로그인 및 학생증 조회 테스트 (threading)")
    print("=" * 70)

    # 동시에 실행할 스레드 목록 생성
    # 각기 다른 사용자로 여러 번의 요청을 동시에 테스트
    threads_to_run = [
        # 사용자 1에 대한 요청 4개
        threading.Thread(target=attempt_login_and_get_card, args=(user_id_1, user_pw_1), name="Thread-A(User1)"),
        # 사용자 2에 대한 요청 4개
        threading.Thread(target=attempt_login_and_get_card, args=(user_id_2, user_pw_2), name="Thread-E(User2)"),
    ]

    # 모든 스레드 시작
    for thread in threads_to_run:
        thread.start()

    # 모든 스레드가 종료될 때까지 대기
    for thread in threads_to_run:
        thread.join()

    print("=" * 70)
    print("모든 테스트가 완료되었습니다.")
    print("결과를 확인하여 모든 요청이 독립적으로 성공했는지,")
    print("또는 동일 사용자(User1)에 대한 요청 중 일부가 실패하고 다른 사용자(User2) 요청은 성공하는지 확인하세요.")
    print("=" * 70)


if __name__ == "__main__":
    main()
