"""fetcher.py - 열린국회정보 '국회일정(ALLSCHEDULE)' 수집 + 정제 모듈"""
import html
import json
import os
import re
from pathlib import Path
from datetime import datetime

import requests

try:  # python-dotenv가 없어도 환경변수만 있으면 동작
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BASE_URL = "https://open.assembly.go.kr/portal/openapi"
SERVICE = "ALLSCHEDULE"
API_KEY = os.getenv("ASSEMBLY_API_KEY", "")
TIMEOUT = 10  # 초


class FetchError(Exception):
    """수집 중 생긴 오류를 하나로 묶은 예외"""


# ---------------- 1. 호출
def fetch_page(page=1, size=100, **filters):
    if not API_KEY:
        raise FetchError("API 키가 없어요. .env 파일에 ASSEMBLY_API_KEY를 넣어주세요.")

    params = {"KEY": API_KEY, "Type": "json", "pIndex": page, "pSize": size, **filters}
    try:
        res = requests.get(f"{BASE_URL}/{SERVICE}", params=params, timeout=TIMEOUT)
        res.raise_for_status()
        return res.json()
    except requests.Timeout:
        raise FetchError("국회 서버 응답이 늦어지고 있어요. 잠시 후 다시 시도해 주세요.")
    except requests.RequestException as e:
        raise FetchError(f"국회 서버에 연결하지 못했어요: {e}")
    except ValueError:
        raise FetchError("응답이 JSON 형식이 아니에요.")


# ---------------- 2. 파싱
def parse_rows(data):
    if SERVICE not in data:
        result = data.get("RESULT", {})
        if result.get("CODE") == "INFO-200":  # 데이터 없음 → 오류 아님
            return []
        raise FetchError(f"API 오류 {result.get('CODE')}: {result.get('MESSAGE')}")

    for block in data[SERVICE]:
        if "row" in block:
            return block["row"]
    return []


# ---------------- 3. 정제
def clean_text(text):
    if not text:
        return ""
    text = html.unescape(str(text))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[\r\n\t\u00a0]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


# ---------------- 4. 구조화
def normalize(row):
    kind = clean_text(row.get("SCH_KIND"))
    title = clean_text(row.get("SCH_CN"))
    date = clean_text(row.get("SCH_DT"))
    time = clean_text(row.get("SCH_TM"))
    committee = clean_text(row.get("CMIT_NM"))
    host = clean_text(row.get("EV_INST_NM"))
    place = clean_text(row.get("EV_PLC"))
    session = " ".join(
        p for p in (clean_text(row.get("CONF_SESS")), clean_text(row.get("CONF_DGR"))) if p
    )
    meeting_type = clean_text(row.get("CONF_DIV"))

    parts = [f"[{kind}] {title}", f"일시: {date} {time}".strip()]
    if committee:
        parts.append(f"위원회: {committee} {meeting_type}".strip())
    if session:
        parts.append(f"회기: {session}")
    if host:
        parts.append(f"주최: {host}")
    if place:
        parts.append(f"장소: {place}")

    return {
        "kind": kind,
        "title": title,
        "date": date,
        "time": time,
        "committee": committee,
        "meeting_type": meeting_type,
        "session": session,
        "host": host,
        "place": place,
        "text": "\n".join(parts),
    }


# ---------------- 5. 수집 + 필터
def fetch_schedules(start_date=None, end_date=None, kind=None, committee=None,
                    max_pages=5, size=100):
    items = []
    for page in range(1, max_pages + 1):
        rows = parse_rows(fetch_page(page, size))
        if not rows:
            break

        page_items = [normalize(r) for r in rows]
        for it in page_items:
            if start_date and it["date"] < start_date:
                continue
            if end_date and it["date"] > end_date:
                continue
            if kind and it["kind"] != kind:
                continue
            if committee and committee not in it["committee"]:
                continue
            items.append(it)

        dates = [it["date"] for it in page_items if it["date"]]
        if start_date and dates and min(dates) < start_date:  # 최신순이라 일찍 멈춤
            break
    return items


def get_schedules(start_date=None, end_date=None, kind=None, committee=None,
                  max_pages=5):
    """main.py 에서 부르는 함수. 항상 {"ok", "items", "error"} 반환"""
    try:
        items = fetch_schedules(start_date, end_date, kind, committee, max_pages)
    except FetchError as e:
        return {"ok": False, "items": [], "error": str(e)}
    except Exception as e:
        return {"ok": False, "items": [], "error": f"알 수 없는 오류: {e}"}

    if not items:
        return {"ok": True, "items": [], "error": "조건에 맞는 일정이 없어요."}
    return {"ok": True, "items": items, "error": None}


# ---------------- 단독 테스트
# ---------------------------------------------------------------- 6. JSON 저장
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

def make_filename(prefix="schedules", output_dir=OUTPUT_DIR):
    """만든 순서(번호) + 시간(날짜_시각)이 들어간 파일 이름을 만든다.
    예: output/schedules_001_20261111_153045.json
    """
    os.makedirs(output_dir, exist_ok=True)

    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)_")
    numbers = []
    for name in os.listdir(output_dir):
        m = pattern.match(name)
        if m:
            numbers.append(int(m.group(1)))
    next_no = max(numbers, default=0) + 1

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(output_dir, f"{prefix}_{next_no:03d}_{stamp}.json")


def save_json(items, prefix="schedules", output_dir=OUTPUT_DIR):
    """정제된 일정 리스트를 새 JSON 파일로 저장하고, 저장한 경로를 반환."""
    path = make_filename(prefix, output_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    return path


# ---------------------------------------------------------------- 단독 테스트
if __name__ == "__main__":
    result = get_schedules(max_pages=1)
    print("ok:", ...)
    if result["ok"] and result["items"]:
        saved = save_json(result["items"])
        print("저장 완료:", saved)