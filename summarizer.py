
"""
summarizer.py
전처리된 국회 일정 JSON을 OpenAI API로 요약하고
summarized 폴더에 저장하는 모듈
"""

import json
import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI


# --------------------------------------------------
# 1. 기본 설정
# --------------------------------------------------

# summarizer.py가 위치한 폴더
BASE_DIR = Path(__file__).resolve().parent

# 전처리 JSON을 읽어올 폴더
INPUT_DIR = BASE_DIR / "output"

# 요약 결과를 저장할 폴더
OUTPUT_DIR = BASE_DIR / "summarized"

# .env 파일 불러오기
load_dotenv(BASE_DIR / ".env")

# 사용할 OpenAI 모델
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# OpenAI 클라이언트 생성
client = OpenAI()



# --------------------------------------------------
# 2. JSON 파일 읽기
# --------------------------------------------------

def load_json(file_path):
    """전처리 JSON 파일 읽기"""

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # JSON 구조에 따라 일정 목록 추출
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if isinstance(data.get("items"), list):
            return data["items"]

        if isinstance(data.get("data"), list):
            return data["data"]

    raise ValueError("지원하지 않는 JSON 구조입니다.")


# --------------------------------------------------
# 3. OpenAI API 요약
# --------------------------------------------------

def summarize_schedules(items):
    """여러 국회 일정을 OpenAI에 전달하여 요약"""

    if not items:
        return {
            "overall_summary": "일정이 없습니다.",
            "summaries": []
        }

    # AI에게 전달할 데이터 구성
    schedules = []

    for index, item in enumerate(items):
        schedules.append({
            "index": index,
            "kind": item.get("kind", ""),
            "title": item.get("title", ""),
            "date": item.get("date", ""),
            "time": item.get("time", ""),
            "committee": item.get("committee", ""),
            "meeting_type": item.get("meeting_type", ""),
            "host": item.get("host", ""),
            "place": item.get("place", "")
        })

    prompt = f"""
너는 국회 일정을 일반 시민들이 쉽게 이해할 수 있도록 설명하는 도우미야.

다음 국회 일정 데이터를 읽고 각 일정을 요약해 줘.

[요약 규칙]
1. 각 일정의 요약은 반드시 정확히 2줄로 작성해.
2. 중학생도 이해할 수 있는 쉬운 한국어를 사용해.
3. 어려운 정치·행정 용어는 가급적 쉬운 말로 바꿔 줘.
4. 일정 제목을 단순히 반복하지 말고 어떤 일정인지 설명해 줘.
5. 원본 데이터에 없는 사실이나 구체적인 논의 내용을 지어내지 마.
6. 정보가 부족하면 확인할 수 있는 내용만 설명해.
7. 날짜, 시간, 장소 등의 정보는 원본과 다르게 바꾸지 마.

[일정 종류별 설명 방법]
- 국회행사: 행사 제목을 바탕으로 어떤 주제의 행사인지 설명해.
- 위원회: 어느 위원회에서 어떤 종류의 회의가 열리는지 설명해.
- 의장단: 면담, 방문, 행사 참석 등 확인 가능한 활동을 설명해.

전체 일정에 대한 종합 요약도 2~3문장으로 작성해.

[일정 데이터]
{json.dumps(schedules, ensure_ascii=False, indent=2)}
"""

    response = client.responses.create(
        model=MODEL,
        instructions="반드시 요청된 JSON 구조에 맞춰 답변하세요.",
        input=prompt,

        # JSON 형식으로 응답하도록 설정
        text={
            "format": {
                "type": "json_schema",
                "name": "schedule_summary",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "overall_summary": {
                            "type": "string"
                        },
                        "summaries": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "index": {
                                        "type": "integer"
                                    },
                                    "summary": {
                                        "type": "string"
                                    }
                                },
                                "required": ["index", "summary"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": [
                        "overall_summary",
                        "summaries"
                    ],
                    "additionalProperties": False
                }
            }
        }
    )

    result = json.loads(response.output_text)

    return result


# --------------------------------------------------
# 4. 요약 결과 저장
# --------------------------------------------------

def save_summary(input_path, items, ai_result):
    """원본 일정 정보와 AI 요약을 새로운 JSON으로 저장"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 원본 일정과 요약 결과 연결
    summary_map = {
        item["index"]: item["summary"]
        for item in ai_result["summaries"]
    }

    result_items = []

    for index, item in enumerate(items):
        new_item = item.copy()

        new_item["ai_summary"] = summary_map.get(
            index, "요약 결과 없음"
        )

        result_items.append(new_item)

    output_data = {
        "source_file": input_path.name,
        "created_at": datetime.now().isoformat(
            timespec="seconds"
        ),
        "overall_summary": ai_result["overall_summary"],
        "total_count": len(result_items),
        "schedules": result_items
    }

    # 원본과 동일한 파일 이름 사용
    output_path = OUTPUT_DIR / input_path.name

    # 임시 파일에 먼저 저장한 후 최종 파일로 교체
    temp_path = output_path.with_suffix(".tmp")

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(
            output_data,
            f,
            ensure_ascii=False,
            indent=2
        )

    temp_path.replace(output_path)

    return output_path


# --------------------------------------------------
# 5. 아직 처리하지 않은 파일 검색
# --------------------------------------------------


def process_pending_files():
    """output 폴더에서 가장 최근 JSON 파일 하나만 요약"""

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # JSON 파일 검색
    json_files = list(INPUT_DIR.glob("*.json"))

    if not json_files:
        print("전처리된 JSON 파일이 없습니다.")
        return

    # 가장 최근에 수정된 파일 하나 선택
    latest_file = max(
        json_files,
        key=lambda file: file.stat().st_mtime
    )

    print(f"\n[선택된 파일] {latest_file.name}")

    output_path = OUTPUT_DIR / latest_file.name

    # 이미 요약된 파일인지 확인
    if output_path.exists():
        print("[건너뜀] 이미 요약된 파일입니다.")
        return

    try:
        # 1. JSON 읽기
        items = load_json(latest_file)

        if not items:
            print("일정 데이터가 비어 있습니다.")
            return

        # 2. OpenAI API 요약
        print("[요약 시작]")
        ai_result = summarize_schedules(items)

        # 3. 결과 저장
        saved_path = save_summary(
            latest_file,
            items,
            ai_result
        )

        print(f"[저장 완료] {saved_path}")

    except Exception as e:
        print(f"[오류] {e}")



# --------------------------------------------------
# 6. 단독 실행
# --------------------------------------------------

if __name__ == "__main__":
    process_pending_files()
