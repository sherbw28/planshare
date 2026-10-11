"""抽出スキーマ(CLAUDE.md「設計方針 > 抽出」に対応)。

分からない項目はnullにする。推測で埋めない。
quoteは検証専用で、公開物には含めない。
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Visit(BaseModel):
    place_name_raw: str = Field(description="場所名(原文の表記のまま)")
    arrival_time: Optional[str] = Field(
        default=None, description="到着時刻 HH:MM(本文に明記されている場合のみ)"
    )
    time_of_day: Optional[Literal["morning", "afternoon", "evening", "night"]] = Field(
        default=None, description="粗い時間帯(文脈から分かる場合)"
    )
    duration_min: Optional[int] = Field(
        default=None, description="滞在時間(分)。本文に明記されている場合のみ"
    )
    transport: Optional[str] = Field(
        default=None, description="この場所への移動手段(train/walk/taxi等、分かれば)"
    )
    sentiment: Optional[Literal["good", "neutral", "bad"]] = Field(
        default=None, description="本人の評価(良かった/普通/失敗)"
    )
    quote: Optional[str] = Field(
        default=None, description="根拠となる原文の短い引用(検証専用・非公開)"
    )
    confidence: float = Field(
        description="この訪問が実際に行われたことへの抽出の自信度 0.0〜1.0"
    )


class Day(BaseModel):
    day_number: int = Field(description="旅程の何日目か(1始まり)")
    visits: list[Visit]


class Skipped(BaseModel):
    place_name_raw: str = Field(description="行く予定だったが行かなかった場所(原文の表記のまま)")
    reason: Optional[str] = Field(default=None, description="行かなかった理由(書かれていれば)")


class Trip(BaseModel):
    total_days: Optional[int] = Field(default=None, description="旅行全体の日数")
    tokyo_days: Optional[int] = Field(default=None, description="うち東京滞在の日数")
    month: Optional[int] = Field(default=None, description="旅行した月(1〜12、分かれば)")
    companions: Optional[
        Literal["solo", "couple", "friends", "family", "other"]
    ] = Field(default=None, description="同行者の種類")
    first_visit: Optional[bool] = Field(default=None, description="初めての訪日か")


class Extraction(BaseModel):
    """1レポート分の抽出結果。"""

    trip: Trip
    days: list[Day]
    skipped: list[Skipped]
    notes: Optional[str] = Field(
        default=None, description="抽出時の注意点(曖昧だった箇所など、あれば)"
    )
