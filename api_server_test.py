import requests
import time
import concurrent.futures
import random

# 서버 주소
URL = "http://localhost:8001/api/v1/student-basicinfo"

# 테스트 설정
CONCURRENT_USERS = 400  # 동시에 요청할 사용자 수
USER_PREFIX = "TEST_"

def send_request(idx):
    user_id = f"{USER_PREFIX}{idx}"
    payload = {
        "user_id": user_id,
        "user_pw": "password" # Mock 모드라 패스워드는 상관없음
    }
    
    start = time.time()
    try:
        # 요청 전송
        response = requests.post(URL, json=payload, timeout=10)
        elapsed = time.time() - start
        
        status = response.status_code
        # 성공 여부 확인
        if status == 200:
            print(f"[OK] {user_id}: {elapsed:.2f}s elapsed")
            return elapsed
        else:
            print(f"[FAIL] {user_id}: Status {status}")
            return None
    except Exception as e:
        print(f"[ERR] {user_id}: {e}")
        return None

def main():
    print(f"--- Starting Concurrency Test (Users: {CONCURRENT_USERS}) ---")
    print(f"Expecting approx 1.0s ~ 2.0s delay per request (simulated).")
    
    start_total = time.time()
    
    # ThreadPoolExecutor로 동시에 요청 발사
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        futures = [executor.submit(send_request, i) for i in range(CONCURRENT_USERS)]
        
        results = []
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res is not None:
                results.append(res)

    end_total = time.time()
    total_time = end_total - start_total
    
    print("\n--- Test Results ---")
    print(f"Total Requests: {CONCURRENT_USERS}")
    print(f"Successful:     {len(results)}")
    print(f"Total Time:     {total_time:.2f}s")
    
    if results:
        avg_req_time = sum(results) / len(results)
        print(f"Avg Req Time:   {avg_req_time:.2f}s")
        
    # 동시성 검증 로직
    # 만약 순차 처리되었다면 Total Time은 (1.5초 * 10명) = 약 15초가 걸림
    # 병렬 처리되었다면 Total Time은 (가장 늦게 끝난 요청 시간) = 약 2~3초 내외여야 함
    if total_time < (1.0 * CONCURRENT_USERS):
        print("\n✅ Concurrency Check PASSED: Requests were processed in parallel.")
    else:
        print("\n❌ Concurrency Check FAILED: Requests seem to be processed sequentially.")
        print("Tip: Check if your FastAPI endpoints are defined as 'def' instead of 'async def' when using blocking code.")

if __name__ == "__main__":
    main()