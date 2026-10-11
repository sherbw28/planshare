"""r/JapanTravelからTrip Reportを取得し、1投稿1ファイルでdata/raw/に保存する。

公式API(OAuth)をprawで利用する。prawはレート制限ヘッダ
(X-Ratelimit-*)を自動で尊重するため、追加のスリープは不要。
原文は解析用のローカル保存のみで、公開・再配布はしない。

使い方:
    python src/fetch_reports.py            # 全クエリを取得
    python src/fetch_reports.py --query 'flair:"Trip Report" tokyo'
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import praw
from dotenv import load_dotenv

SUBREDDIT = "JapanTravel"

# リスティングは1クエリ約1,000件で頭打ちになるため、
# 複数クエリを投げてIDで重複排除する。
DEFAULT_QUERIES = [
    'flair:"Trip Report"',
    'flair:"Trip Report" tokyo',
]

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def make_reddit() -> praw.Reddit:
    load_dotenv()
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT")
    if not all([client_id, client_secret, user_agent]):
        raise SystemExit(
            ".envにREDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USER_AGENTを設定してください。"
            "(登録: https://www.reddit.com/prefs/apps → script型アプリ)"
        )
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )
    reddit.read_only = True
    return reddit


def submission_record(s: praw.models.Submission) -> dict:
    """保存するフィールド。投稿者名は保存しない(プライバシー方針)。"""
    return {
        "id": s.id,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "created_utc": s.created_utc,
        "title": s.title,
        "selftext": s.selftext,
        "link_flair_text": s.link_flair_text,
        "num_comments": s.num_comments,
        "score": s.score,
        "upvote_ratio": s.upvote_ratio,
    }


def fetch(queries: list[str]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    reddit = make_reddit()
    sub = reddit.subreddit(SUBREDDIT)

    seen = {p.stem for p in RAW_DIR.glob("*.json")}
    new_count = 0

    for query in queries:
        print(f"検索: {query!r}")
        for s in sub.search(query, sort="new", syntax="lucene", time_filter="all", limit=None):
            if s.id in seen:
                continue
            seen.add(s.id)
            # フレアの厳密な確認は選定段階でも行うが、無関係な投稿の保存は避ける
            if (s.link_flair_text or "").strip().lower() != "trip report":
                continue
            if not s.selftext or s.selftext in ("[removed]", "[deleted]"):
                continue
            path = RAW_DIR / f"{s.id}.json"
            path.write_text(
                json.dumps(submission_record(s), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            new_count += 1
        print(f"  累計保存数: {len(list(RAW_DIR.glob('*.json')))}")

    print(f"完了: 新規{new_count}件、合計{len(list(RAW_DIR.glob('*.json')))}件")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", action="append", help="検索クエリ(複数指定可)。省略時は既定の2クエリ")
    args = parser.parse_args()
    fetch(args.query or DEFAULT_QUERIES)
