"""유틸리티 모듈"""


def mask_sensitive(text: str, visible_chars: int = 4) -> str:
    """민감한 정보 마스킹"""
    if not text or len(text) <= visible_chars:
        return '****'
    return f"{text[:visible_chars]}****"


__all__ = [
    'mask_sensitive',
]
