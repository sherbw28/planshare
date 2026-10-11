"""選定済みレポートをLLMで構造化抽出し、1本1ファイルでdata/extracted/に保存する。

- モデル: claude-opus-5-5(構造化出力 messages.parse を使用)
- システムプロンプトは固定でprompt cachingを効かせる(2本目以降は入力の大半が90%引き)
- 抽出済みファイルはスキップするので、再実行しても費用は増えない
- 費用はusageから集計して data/extracted/_costs.json に記録する

使い方:
    python src/extract.py --limit 10   # まず10本で試す(タスク3)
    python src/extract.py              # 選定済み全件(タスク4)
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from schema import Extraction

MODEL = "claude-opus-5-5"
# USD / 1M tokens(モデルを変えたらここも更新する)
PRICE_INPUT = 4.00
PRICE_OUTPUT = 20.00
PRICE_CACHE_WRITE = 5.00   # 入力の1.25倍
PRICE_CACHE_READ = 0.20    # 入力の0.05倍

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
SELECTED_PATH = ROOT / "data" / "selected" / "selected.json"
OUT_DIR = ROOT / "data" / "extracted"
COSTS_PATH = OUT_DIR / "_costs.json"
SYSTEM_PROMPT = (ROOT / "prompts" / "extract_system.md").read_text(encoding="utf-8")


def cost_usd(usage) -> float:
    return (
        usage.input_tokens * PRICE_INPUT
        + usage.output_tokens * PRICE_OUTPUT
        + (usage.cache_creation_input_tokens or 0) * PRICE_CACHE_WRITE
        + (usage.cache_read_input_tokens or 0) * PRICE_CACHE_READ
    ) / 1_000_000


def extract_one(client: anthropic.Anthropic, record: dict) -> tuple[Extraction, float]:
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    f"# Title\n{record['title']}\n\n# Trip report\n{record['selftext']}"
                ),
            }
        ],
        output_format=Extraction,
    )
    return response.parsed_output, cost_usd(response.usage)


def main(limit: int | None) -> None:
    load_dotenv()
    if not SELECTED_PATH.exists():
        raise SystemExit("selected.json がありません。先に select_reports.py を実行してください。")

    selected_ids = json.loads(SELECTED_PATH.read_text(encoding="utf-8"))["selected_ids"]
    if limit:
        selected_ids = selected_ids[:limit]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    costs = json.loads(COSTS_PATH.read_text(encoding="utf-8")) if COSTS_PATH.exists() else {}
    client = anthropic.Anthropic()

    done = skipped = 0
    for post_id in selected_ids:
        out_path = OUT_DIR / f"{post_id}.json"
        if out_path.exists():
            skipped += 1
            continue
        record = json.loads((RAW_DIR / f"{post_id}.json").read_text(encoding="utf-8"))
        try:
            extraction, usd = extract_one(client, record)
        except anthropic.APIError as e:
            print(f"  {post_id}: APIエラー: {e}")
            continue
        out_path.write_text(
            extraction.model_dump_json(indent=2),
            encoding="utf-8",
        )
        costs[post_id] = {
            "usd": round(usd, 5),
            "model": MODEL,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        COSTS_PATH.write_text(json.dumps(costs, indent=2), encoding="utf-8")
        done += 1
        total = sum(c["usd"] for c in costs.values())
        print(f"  {post_id}: ${usd:.4f}(累計 ${total:.2f})")

    total = sum(c["usd"] for c in costs.values())
    print(f"完了: 新規{done}本 / スキップ{skipped}本 / 累計費用 ${total:.2f}(約{total * 150:.0f}円)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="先頭N本だけ抽出(試行用)")
    args = parser.parse_args()
    main(args.limit)
