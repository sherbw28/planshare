"""data/raw/から「東京中心・2〜5日程度」のレポートを100本選定する。

選定条件はすべてこのファイルのコードで再現できる。結果は
data/selected/selected.json に、各レポートの判定根拠つきで保存する。

使い方:
    python src/select_reports.py
    python src/select_reports.py --n 100
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CRITERIA_VERSION = "v1"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
OUT_PATH = DATA_DIR / "selected" / "selected.json"

MIN_BODY_CHARS = 1000  # 旅程の線が書かれている最低限の長さ

# 都市判定キーワード(小文字で照合)。東京は区・主要スポット名も含める
TOKYO_KEYWORDS = [
    "tokyo", "shinjuku", "shibuya", "asakusa", "akihabara", "ginza", "ueno",
    "harajuku", "ikebukuro", "roppongi", "odaiba", "nakameguro", "kichijoji",
    "shimokitazawa", "tsukiji", "toyosu", "skytree", "meiji jingu", "senso-ji",
    "sensoji", "teamlab",
]
OTHER_KEYWORDS = [
    "kyoto", "osaka", "nara", "hiroshima", "kanazawa", "sapporo", "hokkaido",
    "fukuoka", "okinawa", "hakone", "nikko", "kamakura", "takayama", "nagoya",
]

DAY_HEADER_RE = re.compile(r"\bday\s*(\d{1,2})\b", re.IGNORECASE)
N_DAYS_RE = re.compile(r"\b(\d{1,2})\s*(?:days?|nights?)\b", re.IGNORECASE)


def count_keywords(text: str, keywords: list[str]) -> int:
    return sum(text.count(k) for k in keywords)


def estimate_days(text: str, title: str) -> int | None:
    """滞在日数の推定。'Day N'見出しの最大値を優先し、なければ'N days'表現。"""
    day_numbers = [int(m) for m in DAY_HEADER_RE.findall(text) if 0 < int(m) <= 30]
    if day_numbers:
        return max(day_numbers)
    n_days = [int(m) for m in N_DAYS_RE.findall(title + " " + text[:500]) if 0 < int(m) <= 30]
    if n_days:
        return max(n_days)
    return None


def judge(record: dict) -> dict:
    """1レポートの判定。選定可否と根拠を返す。"""
    text = (record["title"] + "\n" + record["selftext"]).lower()
    tokyo = count_keywords(text, TOKYO_KEYWORDS)
    other = count_keywords(text, OTHER_KEYWORDS)
    days = estimate_days(record["selftext"].lower(), record["title"].lower())
    body_len = len(record["selftext"])

    reasons = []
    if body_len < MIN_BODY_CHARS:
        reasons.append(f"本文が短い({body_len}字)")
    if tokyo == 0 or tokyo <= other:
        reasons.append(f"東京中心でない(tokyo={tokyo}, other={other})")
    # 東京中心の判定済みなので、日数は旅行全体の長さで2〜7日を許容
    # (東京のみ2〜5日+近郊日帰りを含むケースを想定。検証後に調整する)
    if days is None:
        reasons.append("日数を推定できない")
    elif not (2 <= days <= 7):
        reasons.append(f"日数が範囲外({days}日)")

    return {
        "id": record["id"],
        "created_utc": record["created_utc"],
        "selected": not reasons,
        "excluded_reasons": reasons,
        "stats": {"tokyo": tokyo, "other": other, "days": days, "body_chars": body_len},
    }


def main(n: int) -> None:
    records = [
        json.loads(p.read_text(encoding="utf-8")) for p in sorted(RAW_DIR.glob("*.json"))
    ]
    if not records:
        raise SystemExit("data/raw/ が空です。先に fetch_reports.py を実行してください。")

    judged = [judge(r) for r in records]
    passed = [j for j in judged if j["selected"]]
    # 新しい順に上位n本(決定的な順序)
    passed.sort(key=lambda j: j["created_utc"], reverse=True)
    chosen = passed[:n]
    chosen_ids = {j["id"] for j in chosen}

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(
            {
                "criteria_version": CRITERIA_VERSION,
                "total_raw": len(records),
                "total_passed": len(passed),
                "selected_ids": sorted(chosen_ids),
                "judgements": judged,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"raw {len(records)}件 → 条件通過 {len(passed)}件 → 選定 {len(chosen)}件")
    print(f"保存: {OUT_PATH}")

    # 除外理由の内訳(抽出条件の調整に使う)
    from collections import Counter

    counter = Counter(
        reason.split("(")[0] for j in judged if not j["selected"] for reason in j["excluded_reasons"]
    )
    for reason, count in counter.most_common():
        print(f"  除外: {reason} … {count}件")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=100, help="選定する本数(既定100)")
    args = parser.parse_args()
    main(args.n)
