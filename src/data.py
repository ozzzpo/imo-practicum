"""Загрузка исходного CSV Telco Customer Churn. Источник и проверки описаны в data/README.md."""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
RAW_SHA256 = "88be4b93fbe0cc83421af1c503794c97c342eca914c1576db7c276e61d61358a"


def load_raw(path=RAW_PATH, check_hash=True):
    """Читает исходный CSV без обработки, кроме приведения TotalCharges к числу.

    Пробельные TotalCharges становятся NaN. Как их заполнить, решает команда по итогам EDA.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Нет файла {path}. Скачай его по инструкции в data/README.md")
    if check_hash:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != RAW_SHA256:
            raise ValueError(f"SHA-256 {path.name} не совпадает с data/README.md: {digest}")

    df = pd.read_csv(path)
    # Без errors="coerce": любое другое нечисловое значение должно уронить загрузку, а не стать NaN.
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"].replace(r"^\s*$", np.nan, regex=True))
    return df
