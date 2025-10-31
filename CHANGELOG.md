# 변경 기록

## feature/llmpart-integration
- LLMpart JSON 어댑터 추가(`backend/services/llm_adapter.py`)
- 최적화(MVP) / XAI(MVP) 추가(`backend/services/optimizer.py`, `backend/services/xai.py`)
- DB 헬퍼 확장(`backend/services/db_handler.py`): assignments/summary 저장, settings 조회, jobs 조회
- `backend/app.py` 흐름 연결: LLMpart JSON → RUN/JOBS 저장 → 최적화 → ASSIGNMENTS/RUN_SUMMARY 저장 → XAI 요약 저장
- `sql/` 문서화: DDL/DML 스크립트 파일 추가 및 정리

참고: 기존 main 브랜치의 한글 깨진 커밋 메시지는 기록 보존을 위해 그대로 두고, 본 CHANGELOG에서 명확한 한국어 설명을 제공합니다. 필요 시 히스토리 재작성(rebase -i)로 교체 가능합니다(권장하지 않음).

