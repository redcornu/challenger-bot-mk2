import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Optional

def get_kst_now() -> datetime:
    """한국 시간 반환 (timezone-aware)"""
    return datetime.now(ZoneInfo("Asia/Seoul"))

def safe_json_loads(json_str: str, default: Optional[Dict] = None) -> Dict:
    """안전한 JSON 파싱 - 실패 시 기본값 반환"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}

def safe_json_dumps(data: Dict) -> str:
    """안전한 JSON 직렬화"""
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        return '{}'

def validate_image_exists(image_path: str) -> bool:
    """이미지 파일 존재 확인"""
    import os
    return os.path.exists(image_path)
