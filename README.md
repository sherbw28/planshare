# 実際の旅程の統計(planshare)

r/JapanTravelのTrip Report 100本から、普通の人が東京を実際にどう回ったか(順番・滞在時間・削った場所)を抽出・集計するプロジェクト。背景と設計は [CLAUDE.md](CLAUDE.md) を参照。

## パイプライン

```
取得 → 選定 → 抽出 → 正規化 → 検証 → 集計 → 公開
```

| 段階 | スクリプト | 出力 |
| --- | --- | --- |
| 取得 | `src/fetch_reports.py` | `data/raw/{id}.json`(1投稿1ファイル) |
| 選定 | `src/select_reports.py` | `data/selected/selected.json`(100本+判定根拠) |
| 抽出 | `src/extract.py` | `data/extracted/{id}.json`、`_costs.json` |
| 正規化 | (2週目) | |
| 検証 | (2週目) | |
| 集計 | (2週目) | |

`data/` はすべてgitignore(原文・投稿ID・引用は公開しない)。

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 下記のキーを記入
```

### Reddit APIの登録(手作業・1回だけ)

1. Redditにログインし https://www.reddit.com/prefs/apps を開く
2. 「create another app...」→ タイプは **script** を選択
3. name: `planshare-trip-stats`、redirect uri: `http://localhost:8080`(script型では未使用だが必須)
4. 発行された **client ID**(アプリ名の下の文字列)と **secret** を `.env` に記入
5. `.env` の `REDDIT_USER_AGENT` の `YOUR_USERNAME` を自分のRedditユーザー名に置き換える

### Anthropic APIキー

`.env` の `ANTHROPIC_API_KEY` に記入(抽出で使用)。

## 実行手順(1週目)

```bash
python src/fetch_reports.py          # Trip Reportを取得(〜数分)
python src/select_reports.py         # 東京中心・2〜7日を100本選定
python src/extract.py --limit 10     # まず10本で抽出を試す → 目視で確認
python src/extract.py                # 問題なければ100本すべて抽出
```

抽出は1本ごとに保存されるので、中断・再実行しても抽出済み分の費用はかからない。

## Reddit API 調査メモ(2026-10-11)

- **レート制限**: OAuth認証ありで100クエリ/分(2023-07-01以降の無料枠)。認証なしは10クエリ/分。旧公式wikiは60/分と記載しており、実際の上限は `X-Ratelimit-*` レスポンスヘッダで確認する(prawは自動で尊重する)。
- **無料枠**: 非商用利用。本プロジェクトは非商用・収益化なしの範囲で利用する。
- **User-Agent**: `<platform>:<app ID>:<version> (by /u/<username>)` 形式が必須。偽装は禁止。
- **検索**: `flair:"Trip Report"` 構文(lucene)で絞り込み可能。1リスティングの上限は約1,000件のため、複数クエリ+ID重複排除で補う。
- **データの扱い**: 原文はローカル解析用の保存のみ。公開するのは集計値だけ。投稿者名は保存しない。

出典: [Reddit Data API更新アナウンス(r/redditdev, 2023-05)](https://reddit.birdcat.cafe/r/redditdev/comments/13wsiks/_/jmmptma/?context=1)、[公式APIルール(reddit-archive wiki)](https://github.com/reddit-archive/reddit/wiki/API)、[検索構文(旧公式wiki)](https://web-archive.nli.org.il/National_Library/mp_/https://www.reddit.com/wiki/search)

## 抽出の設計

- モデル: `claude-opus-5-5`(入力$4/出力$20 per 1Mトークン)
- 構造化出力(`messages.parse` + Pydantic)でスキーマ保証。スキーマは `src/schema.py`
- システムプロンプト(`prompts/extract_system.md`)は固定し、prompt cachingで2本目以降の入力費を約90%削減
- 費用想定: 100本で$5〜7(約800〜1,100円)。成功基準の5,000円以内に収まる見込み
- 分からない項目はnull。推測で埋めない(スキーマとプロンプトの両方で指示)

## 結果の記録

各タスクの終わりに数字をここに書き足す(CLAUDE.md「最初の2週間のタスク」)。

| 項目 | 数字 | 記録日 |
| --- | --- | --- |
| 取得したTrip Report総数 | (未) | |
| 選定条件を通過した本数 | (未) | |
| 10本試行の所感・修正点 | (未) | |
| 100本の抽出費用 | (未) | |
| 場所の再現率 / 適合率(20本検証) | (未) | |
| 滞在時間が書かれているレポートの割合 | (未) | |
| 名寄せ後の未分類率 | (未) | |
