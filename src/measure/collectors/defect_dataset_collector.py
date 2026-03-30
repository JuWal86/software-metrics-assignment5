from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import requests


@dataclass
class DefectDataset:
    name: str
    df: pd.DataFrame


def load_defect_dataset(url: str, datasets_dir: Path) -> DefectDataset:
    datasets_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1] or "defect_dataset.csv"
    local = datasets_dir / filename

    if not local.exists():
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        local.write_bytes(r.content)

    df = pd.read_csv(local)
    return DefectDataset(name=filename, df=df)
