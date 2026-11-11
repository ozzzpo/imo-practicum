"""Загрузка исходного CSV Telco Customer Churn. Источник и проверки описаны в data/README.md."""

import hashlib
import os
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
RAW_SHA256 = "88be4b93fbe0cc83421af1c503794c97c342eca914c1576db7c276e61d61358a"
DATASET_HANDLE = "blastchar/telco-customer-churn/versions/1"


def _check_raw_hash(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != RAW_SHA256:
        raise ValueError(f"SHA-256 {path.name} не совпадает с data/README.md: {digest}")


def download_raw(path=RAW_PATH):
    """Скачивает CSV версии 1, только если файла нет, и возвращает его путь.

    Хеш проверяется всегда. Существующий файл не перезаписывается, даже
    если его содержимое неверно. При ошибке скачивания или проверки
    новый CSV не появляется на целевом пути.
    """
    path = Path(path)
    if path.exists():
        _check_raw_hash(path)
        return path

    # Чтение локального CSV не должно зависеть от импорта сетевого клиента.
    from kagglehub import dataset_download

    path.parent.mkdir(parents=True, exist_ok=True)
    # Та же файловая система позволяет сохранить уже проверенный файл
    # целиком и не заменить CSV, если его параллельно создал другой процесс.
    with TemporaryDirectory(prefix=".telco-", dir=path.parent) as temporary_dir:
        try:
            downloaded = Path(
                dataset_download(
                    DATASET_HANDLE,
                    path=RAW_PATH.name,
                    output_dir=temporary_dir,
                )
            )
        except Exception as exc:
            raise RuntimeError(
                "Не удалось скачать Telco Customer Churn версии 1 с Kaggle. "
                "Проверьте подключение и доступ к Kaggle или скачайте CSV "
                "вручную по инструкции в data/README.md."
            ) from exc

        # В Kaggle/Colab клиент может проигнорировать output_dir и вернуть
        # файл из другого монтирования. Публикуем только собственную копию
        # на той же файловой системе, где расположен целевой CSV.
        staged = Path(temporary_dir) / "verified.csv"
        copyfile(downloaded, staged)
        _check_raw_hash(staged)
        try:
            os.link(staged, path)
        except FileExistsError:
            _check_raw_hash(path)

    return path


def load_raw(path=RAW_PATH, check_hash=True, *, download=False):
    """Читает исходный CSV без обработки, кроме приведения TotalCharges к числу.

    Пробельные TotalCharges становятся NaN. Как их заполнить, решает команда по итогам EDA.
    download=True разрешает скачать отсутствующий CSV версии 1 с Kaggle.
    Существующий файл используется без сети. Скачанный файл проверяется
    по SHA-256 даже при check_hash=False.
    """
    path = Path(path)
    if not path.exists():
        if download:
            download_raw(path)
        else:
            raise FileNotFoundError(
                f"Нет файла {path}. Вызовите load_raw(download=True) или "
                "скачайте CSV по инструкции в data/README.md"
            )
    if check_hash:
        _check_raw_hash(path)

    df = pd.read_csv(path)
    # Без errors="coerce": любое другое нечисловое значение должно уронить загрузку, а не стать NaN.
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"].replace(r"^\s*$", np.nan, regex=True))
    return df
