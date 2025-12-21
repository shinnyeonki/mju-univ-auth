# mju-univ-auth 기여 가이드

`mju-univ-auth` 프로젝트에 기여해주셔서 감사합니다! 이 문서는 새로운 기능을 추가하거나 버그를 수정하고자 하는 사람들을 위한 안내서입니다.

## 1. 시작하기 전에

기여하기 전에, 프로젝트의 전반적인 구조를 이해하는 것이 좋습니다. 상세한 내용은 [아키텍처 문서](architecture.md)에서 확인하실 수 있습니다.

## 2. 핵심 설계 원칙

이 라이브러리는 서비스 개발자와 라이브러리 개발자 모두의 사용성을 고려하여 설계되었습니다.

- **이중 결과 처리 (Result + Exception)**:
    - **Public API (고수준)**: `MjuUnivAuth` Facade 클래스와 같이 사용자에게 직접 노출되는 API는 항상 `MjuUnivAuthResult` 객체를 반환합니다. 실패하더라도 예외를 발생시키지 않습니다.
    - **Internal Layer (저수준)**: 내부 로직(Fetcher, Authenticator의 `_execute` 메서드 등)은 실패 시 구체적인 커스텀 예외(`ParsingError`, `NetworkError` 등)를 발생시켜 문제의 원인을 명확히 합니다.

- **계층 분리**: 코드는 역할에 따라 `facade`, `authenticator`, `fetcher`, `domain`, `infrastructure` 등으로 명확히 분리되어 있습니다.

## 3. 새로운 데이터 조회 기능 추가하기

새로운 학생 정보를 조회하는 기능을 추가하는 과정을 예시로 설명합니다.

### 1단계: Domain 모델 정의

조회할 데이터를 담을 순수 데이터 클래스를 `mju_univ_auth/domain/` 디렉토리에 정의합니다. `pydantic`의 `BaseModel`을 상속받아 작성합니다.

**예시: `mju_univ_auth/domain/new_data.py`**
```python
from pydantic import BaseModel, Field

class NewData(BaseModel):
    field1: str = Field(default="", description="필드1 설명")
    field2: int = Field(default=0, description="필드2 설명")
```

### 2단계: Fetcher 구현

`mju_univ_auth/fetcher/` 디렉토리에 실제 데이터 조회 및 파싱 로직을 담당하는 Fetcher를 구현합니다.

- `BaseFetcher`를 상속받습니다.
- `_execute()` 메서드 내에서 `requests.Session`을 사용하여 페이지에 접근하고, `BeautifulSoup`이나 정규표현식으로 HTML을 파싱합니다.
- 실패 상황(네트워크 오류, 파싱 실패 등)에서는 적절한 예외를 `raise`해야 합니다. `BaseFetcher`가 이 예외를 `MjuUnivAuthResult`로 변환해줍니다.

**예시: `mju_univ_auth/fetcher/new_data_fetcher.py`**
```python
from bs4 import BeautifulSoup
from .base_fetcher import BaseFetcher
from ..domain.new_data import NewData
from ..exceptions import ParsingError, NetworkError
import requests # requests는 .base_fetcher 내에서 session을 통해 사용됩니다.

class NewDataFetcher(BaseFetcher[NewData]):
    def __init__(self, session, verbose=False):
        super().__init__(session)
        self._verbose = verbose
    
    def _execute(self) -> NewData:
        # 1. 대상 페이지 접근
        try:
            # 조회하려는 정보가 있는 페이지 URL
            url = "https://service.mju.ac.kr/path/to/data"
            response = self.session.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            raise NetworkError("데이터 페이지 접근 실패", original_error=e)

        # 2. HTML 파싱 및 데이터 추출
        soup = BeautifulSoup(response.text, 'lxml')
        field1_tag = soup.find('div', id='field1')
        if not field1_tag:
            raise ParsingError("field1에 해당하는 태그를 찾을 수 없습니다.")
        
        # 3. Domain 객체 생성 및 반환
        return NewData(
            field1=field1_tag.text.strip(),
            field2=123 # 예시
        )
```

### 3단계: Facade에 메서드 추가

사용자가 쉽게 접근할 수 있도록 `mju_univ_auth/facade.py`의 `MjuUnivAuth` 클래스에 새 조회 메서드를 추가합니다.

- 메서드는 로그인 상태를 확인하고, 세션이 유효할 때 구현한 Fetcher를 호출합니다.
- Fetcher의 `fetch()` 메서드가 반환하는 `MjuUnivAuthResult`를 그대로 반환합니다.

**예시: `mju_univ_auth/facade.py`**
```python
# ... (import 구문 추가)
from .fetcher.new_data_fetcher import NewDataFetcher
from .domain.new_data import NewData
from .results import MjuUnivAuthResult, ErrorCode


class MjuUnivAuth:
    # ... (기존 코드)

    def get_new_data(self) -> MjuUnivAuthResult[NewData]:
        """새로운 데이터를 조회합니다."""
        if self._login_failed:
            return self._login_error
        if self._session is None:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=False,
                data=None,
                error_code=ErrorCode.SESSION_NOT_EXIST_ERROR,
                error_message="로그인이 필요합니다."
            )
        
        # 특정 서비스('msi' 등)에서만 조회가 가능하다면 아래와 같이 확인 로직을 추가할 수 있습니다.
        # if self._service != 'msi':
        #     return MjuUnivAuthResult(error_code=ErrorCode.INVALID_SERVICE_USAGE_ERROR, ...)

        fetcher = NewDataFetcher(self._session, self._verbose)
        return fetcher.fetch()
```

### 4단계: 모듈 Export

새로 만든 클래스들을 외부에서 `import`할 수 있도록 각 패키지의 `__init__.py` 파일에 있는 `__all__` 리스트에 추가합니다.

- `mju_univ_auth/domain/__init__.py`
- `mju_univ_auth/fetcher/__init__.py`
- `mju_univ_auth/__init__.py`


궁금한 점이 있다면 언제든지 Issue를 열어 질문해주세요.
