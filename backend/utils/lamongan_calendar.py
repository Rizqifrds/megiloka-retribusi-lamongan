"""Transcription of the published Lamongan Tourism calendar poster."""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ai.dates import MONTHS

POSTER_PAGE = 'https://lamongantourism.com/kalender-event-2026/'
POSTER_YEAR = 2026
POSTER_API = 'https://lamongantourism.com/wp-json/wp/v2/pages/3022?_fields=modified'
POSTER_TRANSCRIBED_VERSION = '2026-01-27T09:07:50'
_PATH = Path(__file__).resolve().parents[1] / 'database' / 'kalender_lamongan_2026.json'


@dataclass(frozen=True)
class PosterEvent:
    name: str
    date_label: str
    start: date | None
    end: date | None
    anchor: str


def poster_months(today):
    months = json.loads(_PATH.read_text(encoding='utf-8'))
    return [
        {
            'number': month,
            'name': name,
            'entries': entries,
            'open': today.year == POSTER_YEAR and month in (today.month, today.month + 1),
        }
        for month, (name, entries) in enumerate(zip(MONTHS, months, strict=True), start=1)
    ]


def poster_events(today):
    for month, group in enumerate(poster_months(today), start=1):
        for entry, (days, name) in enumerate(group['entries'], start=1):
            month_label = f"{group['name']} {POSTER_YEAR}"
            anchor = f'poster-event-{month}-{entry}'
            if not days:
                yield PosterEvent(name, month_label, None, None, anchor)
                continue
            first, _, last = days.partition('–')
            start = date(POSTER_YEAR, month, int(first))
            end = date(POSTER_YEAR, month, int(last or first))
            yield PosterEvent(name, f'{days} {month_label}', start, end, anchor)


def upcoming_poster_events(today):
    upcoming = [event for event in poster_events(today) if event.end and event.end >= today]
    return sorted(upcoming, key=lambda event: event.start)[:3]
