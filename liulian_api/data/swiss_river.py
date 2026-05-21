"""Real swiss-river-1990 data loader for liulian-api.

Reads ``dataset/swiss_river/swiss-1990_{train,test}.csv`` from the
liulian-python checkout (one directory up). Stations are FOEN water-temp
stations; rows are one per day (`epoch_day` = days since 1970-01-01).

stdlib-only, cached after first load. Schema:

    epoch_day,2091_wt,...,2269_wt,2091_at,...,2269_at,has_nan

* ``*_wt`` = water temperature °C (28 stations)
* ``*_at`` = air temperature °C (28 stations)
* ``has_nan`` = bool flag, row-level
"""

from __future__ import annotations

import csv
import math
import os
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Iterable, NamedTuple

EPOCH = date(1970, 1, 1)


class StationSeries(NamedTuple):
    station_id: str       # raw FOEN id, e.g. '2091'
    field: str            # 'wt' or 'at'
    timestamps: list[datetime]
    values: list[float | None]


def _resolve_data_dir() -> Path | None:
    """Find dataset/swiss_river/. Honours LIULIAN_SWISS_RIVER_DIR env var,
    then probes the liulian-python sibling checkout."""
    explicit = os.environ.get('LIULIAN_SWISS_RIVER_DIR')
    if explicit and Path(explicit).is_dir():
        return Path(explicit)
    # liulian-api/ → ../liulian-python/dataset/swiss_river/
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent.parent / 'liulian-python' / 'dataset' / 'swiss_river'
        if cand.is_dir():
            return cand
        cand2 = parent / 'dataset' / 'swiss_river'
        if cand2.is_dir():
            return cand2
    return None


def epoch_day_to_ts(epoch_day: int) -> datetime:
    return datetime.combine(EPOCH + timedelta(days=epoch_day), datetime.min.time(), tzinfo=timezone.utc)


@lru_cache(maxsize=4)
def load_csv(name: str = 'swiss-1990') -> dict[str, list]:
    """Load and merge train+test CSVs for the given variant.

    Returns a dict with keys:
      - 'header'      : list[str]
      - 'epoch_day'   : list[int]
      - 'rows'        : list[list[str]]
      - 'stations'    : list[str] (e.g. ['2091', '2143', ...])
    """
    data_dir = _resolve_data_dir()
    if data_dir is None:
        raise FileNotFoundError('swiss-river dataset directory not found; set LIULIAN_SWISS_RIVER_DIR')

    rows: list[list[str]] = []
    header: list[str] | None = None
    epoch_days: list[int] = []

    for suffix in ('train', 'test'):
        path = data_dir / f'{name}_{suffix}.csv'
        if not path.exists():
            continue
        with path.open() as f:
            reader = csv.reader(f)
            this_header = next(reader)
            if header is None:
                header = this_header
            for row in reader:
                rows.append(row)
                try:
                    epoch_days.append(int(row[0]))
                except (ValueError, IndexError):
                    epoch_days.append(0)

    if header is None:
        raise FileNotFoundError(f'no CSV files matched {name}_{{train,test}}.csv in {data_dir}')

    stations = sorted({col.rsplit('_', 1)[0] for col in header if col.endswith('_wt')})

    # sort everything by epoch_day so train+test concatenate chronologically
    paired = sorted(zip(epoch_days, rows), key=lambda x: x[0])
    epoch_days = [p[0] for p in paired]
    rows = [p[1] for p in paired]

    return {'header': header, 'epoch_day': epoch_days, 'rows': rows, 'stations': stations}


def list_stations(name: str = 'swiss-1990') -> list[str]:
    return load_csv(name)['stations']


def station_series(name: str, station_id: str, field: str = 'wt') -> StationSeries:
    """Return the full historical series for one station / one field."""
    d = load_csv(name)
    header = d['header']
    col_name = f'{station_id}_{field}'
    if col_name not in header:
        raise KeyError(f'unknown column {col_name}; available stations: {d["stations"][:5]}…')
    idx = header.index(col_name)
    timestamps: list[datetime] = []
    values: list[float | None] = []
    for ed, row in zip(d['epoch_day'], d['rows']):
        ts = epoch_day_to_ts(ed)
        cell = row[idx] if idx < len(row) else ''
        if cell == '' or cell.lower() == 'nan':
            values.append(None)
        else:
            try:
                values.append(float(cell))
            except ValueError:
                values.append(None)
        timestamps.append(ts)
    return StationSeries(station_id=station_id, field=field, timestamps=timestamps, values=values)


def synth_forecast(
    observed: list[float | None],
    horizon: int,
    noise_scale: float = 0.7,
) -> dict[str, list[float]]:
    """Cheap deterministic forecast from the tail of an observed series.

    Returns ``{'mean', 'q05', 'q95'}``. Strategy:
      - extrapolate from a linear fit over the last 14 observed values
      - widen Q05/Q95 as ``noise * (1 + i/horizon) * 1.96``
    """
    clean = [v for v in observed if v is not None][-30:]
    if len(clean) < 3:
        last = clean[-1] if clean else 0.0
        mean = [last] * horizon
        width = [noise_scale * (1 + i / max(horizon, 1)) * 1.96 for i in range(horizon)]
        return {'mean': mean, 'q05': [m - w for m, w in zip(mean, width)], 'q95': [m + w for m, w in zip(mean, width)]}

    # least-squares slope on last 14 points
    tail = clean[-14:]
    n = len(tail)
    sx = sum(range(n))
    sy = sum(tail)
    sxx = sum(i * i for i in range(n))
    sxy = sum(i * v for i, v in enumerate(tail))
    denom = n * sxx - sx * sx
    if denom == 0:
        slope = 0.0
        intercept = sum(tail) / n
    else:
        slope = (n * sxy - sx * sy) / denom
        intercept = (sy - slope * sx) / n

    mean = [intercept + slope * (n + i) for i in range(horizon)]
    width = [noise_scale * (1 + i / max(horizon, 1)) * 1.96 for i in range(horizon)]
    return {'mean': mean, 'q05': [m - w for m, w in zip(mean, width)], 'q95': [m + w for m, w in zip(mean, width)]}
