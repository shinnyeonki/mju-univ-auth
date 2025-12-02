import sys
import os

# 패키지를 임포트할 수 있도록 루트 경로를 sys.path에 추가합니다
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
