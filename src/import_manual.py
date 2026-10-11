"""手動保存したレポート(data/manual/*.txt)をdata/raw/のJSON形式に変換する。

Reddit API承認待ちの間、ブラウザで閲覧・コピーしたレポートでタスク3
(抽出の試行)を進めるための補助スクリプト。

形式: 1行目=タイトル、空行、以降=本文。ファイル名=投稿ID.txt
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANUAL_DIR = ROOT / "data" / "manual"
RAW_DIR = ROOT / "data" / "raw"
SELECTED_PATH = ROOT / "data" / "selected" / "selected.json"


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ids = []
    for txt in sorted(MANUAL_DIR.glob("*.txt")):
        lines = txt.read_text(encoding="utf-8").split("\n")
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        record = {
            "id": txt.stem,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "created_utc": 0,
            "title": title,
            "selftext": body,
            "link_flair_text": "Trip Report",
            "num_comments": None,
            "score": None,
            "upvote_ratio": None,
            "source": "manual",
        }
        (RAW_DIR / f"{txt.stem}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        ids.append(txt.stem)
        print(f"変換: {txt.stem} ({title[:50]})")

    # タスク3用: 手動分をそのまま抽出対象にする
    SELECTED_PATH.parent.mkdir(parents=True, exist_ok=True)
    SELECTED_PATH.write_text(
        json.dumps(
            {"criteria_version": "manual-task3", "selected_ids": sorted(ids)},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"selected.json を手動{len(ids)}本で更新(API承認後はselect_reports.pyで上書き)")


if __name__ == "__main__":
    main()
