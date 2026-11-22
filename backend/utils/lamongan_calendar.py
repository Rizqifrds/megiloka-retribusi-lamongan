"""Transcription of the published Lamongan Tourism calendar poster."""

import json
from pathlib import Path

from ai.dates import MONTHS

POSTER_PAGE = 'https://lamongantourism.com/kalender-event-2026/'
POSTER_YEAR = 2026
POSTER_API = 'https://lamongantourism.com/wp-json/wp/v2/pages/3022?_fields=modified'
POSTER_TRANSCRIBED_VERSION = '2026-01-27T09:07:50'
_PATH = Path(__file__).resolve().parents[1] / 'database' / 'kalender_lamongan_2026.json'


def poster_months(today):
    months = json.loads(_PATH.read_text(encoding='utf-8'))
    return [
        {
            'name': name,
            'entries': entries,
            'open': today.year == POSTER_YEAR and month in (today.month, today.month + 1),
        }
        for month, (name, entries) in enumerate(zip(MONTHS, months, strict=True), start=1)
    ]
