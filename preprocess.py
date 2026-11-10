"""preprocess.py - 데이터 전처리 모듈 (정규표현식 정제 + pandas DataFrame 가공)

fetcher.py 와 같은 폴더에 두세요.
준비:  pip install pandas requests python-dotenv
테스트: python preprocess.py

main.py 에서 사용:
    from preprocess import load_schedules, df_to_items
    result = load_schedules(start_date="2026-11-01", end_date="2026-11-30")
    if result["ok"]:
        df = result["df"]            # pandas DataFrame
        items = df_to_items(df)      # 이제혁 님에게 넘길 JSON용 list[dict]
"""
import html
import re

import pandas as pd

from fetcher import FetchError, fetch_page, parse_rows


# ---------------------------------------------------------------- 1. 정규식 정제
_SCRIPT_STYLE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.I | re.S)  # 스크립트/스타일 통째로
_TAG = re.compile(r"<[^>]+>")                                               # 나머지 HTML 태그
_INVISIBLE = re.compile(r"[\u200b-\u200d\u2060\ufeff]")                     # 눈에 안 보이는 글자
_SPACES = re.compile(r"\s+")                                                # 모든 공백류(줄바꿈, 탭, nbsp 포함)


def clean_text(text):
    """HTML 태그, 엔티티(&amp; 등), 보이지 않는 문자, 중복 공백을 제거.
    None, NaN, 숫자가 들어와도 안전하게 "" 또는 문자열을 반환.
    """
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    text = html.unescape(str(text))        # &nbsp; &amp; → 실제 문자
    text = _SCRIPT_STYLE.sub(" ", text)    # <script>...</script> 제거
    text = _TAG.sub(" ", text)             # <b>, <br>, <p> 등 제거
    text = _INVISIBLE.sub("", text)        # 제로폭 문자 제거
    text = text.replace("\u00a0", " ")     # nbsp → 일반 공백
    text = _SPACES.sub(" ", text)          # 연속 공백/줄바꿈 → 공백 하나
    return text.strip()


# ---------------------------------------------------------------- 2. DataFrame 가공
# API 필드명 → 팀에서 쓸 컬럼명
RENAME = {
    "SCH_KIND": "kind",
    "SCH_CN": "title",
    "SCH_DT": "date",
    "SCH_TM": "time",
    "CONF_DIV": "meeting_type",
    "CMIT_NM": "committee",
    "CONF_SESS": "conf_sess",
    "CONF_DGR": "conf_dgr",
    "EV_INST_NM": "host",
    "EV_PLC": "place",
}
TEXT_COLS = ["kind", "title", "time", "meeting_type", "committee",
             "conf_sess", "conf_dgr", "host", "place"]


def _build_text(row):
    """AI 요약 프롬프트에 넣을 한 덩어리 텍스트"""
    date = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else ""
    parts = [f"[{row['kind']}] {row['title']}", f"일시: {date} {row['time']}".strip()]
    if row["committee"]:
        parts.append(f"위원회: {row['committee']} {row['meeting_type']}".strip())
    if row["session"]:
        parts.append(f"회기: {row['session']}")
    if row["host"]:
        parts.append(f"주최: {row['host']}")
    if row["place"]:
        parts.append(f"장소: {row['place']}")
    return "\n".join(parts)


def rows_to_dataframe(rows):
    """API의 row 리스트 → 정제된 pandas DataFrame

    처리 순서: DataFrame 생성 → 컬럼명 통일 → 텍스트 정제 → 날짜 변환
              → 결측/중복 제거 → 정렬 → text 컬럼 생성
    """
    # 1) DataFrame 생성. 일부 필드가 없는 응답이어도 컬럼은 항상 같게 맞춤
    df = pd.DataFrame(rows).reindex(columns=list(RENAME))
    df = df.rename(columns=RENAME)

    # 2) 텍스트 컬럼 정제 (None → "", 태그·공백 제거)
    for col in TEXT_COLS:
        df[col] = df[col].map(clean_text)

    # 3) 날짜 변환: 형식이 이상하면 NaT(결측)로 처리
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # 4) 결측·빈 제목 제거, 중복 제거
    df = df.dropna(subset=["date"])
    df = df[df["title"] != ""]
    df = df.drop_duplicates(subset=["kind", "title", "date", "time", "committee"])

    # 5) 회기 합치기 ("제439회국회(정기회)" + "제5차")
    df["session"] = (df["conf_sess"] + " " + df["conf_dgr"]).str.strip()
    df = df.drop(columns=["conf_sess", "conf_dgr"])

    # 6) 최신순 정렬 + 인덱스 정리
    df = df.sort_values("date", ascending=False).reset_index(drop=True)

    # 7) 요약용 텍스트 컬럼
    df["text"] = df.apply(_build_text, axis=1)

    return df[["kind", "title", "date", "time", "committee", "meeting_type",
               "session", "host", "place", "text"]]


def df_to_items(df):
    """DataFrame → list[dict]. 날짜는 'YYYY-MM-DD' 문자열로 (JSON 변환용)"""
    out = df.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    return out.to_dict(orient="records")


# ---------------------------------------------------------------- 3. 수집 + 필터
def fetch_schedule_df(start_date=None, end_date=None, kind=None, committee=None,
                      max_pages=5, size=100):
    """여러 페이지를 가져와 DataFrame으로 만들고 pandas로 필터링.
    응답이 최신순인 점을 이용해 start_date보다 오래된 구간이 나오면 일찍 멈춤.
    """
    all_rows = []
    for page in range(1, max_pages + 1):
        rows = parse_rows(fetch_page(page, size))
        if not rows:
            break
        all_rows.extend(rows)

        dates = [r.get("SCH_DT") for r in rows if r.get("SCH_DT")]
        if start_date and dates and min(dates) < start_date:
            break

    df = rows_to_dataframe(all_rows)

    if start_date:
        df = df[df["date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["date"] <= pd.to_datetime(end_date)]
    if kind:
        df = df[df["kind"] == kind]
    if committee:
        df = df[df["committee"].str.contains(committee, regex=False)]
    return df.reset_index(drop=True)


def load_schedules(start_date=None, end_date=None, kind=None, committee=None,
                   max_pages=5):
    """main.py 에서 부르는 함수. 예외 대신 항상 같은 모양의 dict를 반환.

    반환: {"ok": bool, "df": DataFrame, "error": str | None}
    """
    try:
        df = fetch_schedule_df(start_date, end_date, kind, committee, max_pages)
    except FetchError as e:
        return {"ok": False, "df": pd.DataFrame(), "error": str(e)}
    except Exception as e:
        return {"ok": False, "df": pd.DataFrame(), "error": f"알 수 없는 오류: {e}"}

    if df.empty:
        return {"ok": True, "df": df, "error": "조건에 맞는 일정이 없어요."}
    return {"ok": True, "df": df, "error": None}


# ---------------------------------------------------------------- 단독 테스트
if __name__ == "__main__":
    # (1) API 없이 정규식 정제만 먼저 확인
    sample = "<p>안녕&nbsp;<b>하세요</b><br>   반갑습니다 &amp; 환영해요</p>\n\n"
    print("정제 전:", repr(sample))
    print("정제 후:", repr(clean_text(sample)))
    print("=" * 40)

    # (2) 실제 API → DataFrame
    result = load_schedules(max_pages=1)
    print("ok:", result["ok"], "| error:", result["error"])
    df = result["df"]
    if not df.empty:
        print("크기(행, 열):", df.shape)
        print(df.dtypes)
        print(df[["date", "kind", "title"]].head())
