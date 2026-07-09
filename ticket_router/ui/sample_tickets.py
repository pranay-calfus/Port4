import json
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

SAMPLE_TICKETS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "sample-tickets" / "tickets.json"
)


class SampleTicket(TypedDict):
    id: str
    title: str
    categoryLabel: str
    message: str


@lru_cache(maxsize=1)
def load_sample_tickets() -> list[SampleTicket]:
    with SAMPLE_TICKETS_PATH.open(encoding="utf-8") as f:
        return json.load(f)
