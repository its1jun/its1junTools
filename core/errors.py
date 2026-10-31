class CancelledError(Exception):
    """작업이 사용자에 의해 취소됨. 도구는 잡지 않고 통과시켜도 된다."""
