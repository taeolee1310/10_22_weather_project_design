"""체크리스트·활동 선택 저장. 지역·한국 날짜를 키에 넣고, 지난 날짜 항목은 정리한다."""
import json
from pathlib import Path

FILE = Path(__file__).with_name(".state.json")


def _load():
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def get(region, date, name, default=None):
    return _load().get(f"{region}|{date}", {}).get(name, default)


def put(region, date, name, value):
    state = {k: v for k, v in _load().items() if k.endswith(f"|{date}")}
    state.setdefault(f"{region}|{date}", {})[name] = value
    try:
        FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # 저장이 안 돼도 화면은 계속 쓴다
