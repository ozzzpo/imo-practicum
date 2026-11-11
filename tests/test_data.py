import errno
import hashlib
from pathlib import Path

import pytest

import src.data as data
from src.data import RAW_PATH, load_raw

CSV = "customerID,tenure,TotalCharges,Churn\nA,0, ,No\nB,2,40.5,Yes\n"


@pytest.fixture
def csv_hash(monkeypatch):
    monkeypatch.setattr(data, "RAW_SHA256", hashlib.sha256(CSV.encode()).hexdigest())


@pytest.fixture
def kagglehub(monkeypatch):
    import kagglehub as module

    def unexpected_download(*args, **kwargs):
        pytest.fail("Тест не должен обращаться к сети")

    monkeypatch.setattr(module, "dataset_download", unexpected_download)
    return module


def test_blank_total_charges_become_nan(tmp_path):
    path = tmp_path / "telco.csv"
    path.write_bytes(CSV.encode())
    df = load_raw(path, check_hash=False)
    assert df["TotalCharges"].isna().tolist() == [True, False]
    assert df.loc[1, "TotalCharges"] == 40.5


def test_other_garbage_is_not_silenced(tmp_path):
    path = tmp_path / "telco.csv"
    path.write_bytes(CSV.replace("40.5", "abc").encode())
    with pytest.raises(ValueError):
        load_raw(path, check_hash=False)


def test_wrong_hash_rejected(tmp_path):
    path = tmp_path / "telco.csv"
    path.write_bytes(CSV.encode())
    with pytest.raises(ValueError, match="SHA-256"):
        load_raw(path)


def test_missing_file(tmp_path, kagglehub):
    with pytest.raises(FileNotFoundError, match="data/README.md"):
        load_raw(tmp_path / "nope.csv")
    assert list(tmp_path.iterdir()) == []


def test_opt_in_download_is_pinned_and_reused_offline(
    tmp_path, monkeypatch, csv_hash, kagglehub
):
    target = tmp_path / "raw" / "custom-name.csv"
    calls = []

    def fake_download(handle, *, path, output_dir):
        temporary = Path(output_dir)
        assert temporary.parent == target.parent
        assert temporary.is_dir() and not list(temporary.iterdir())
        assert not target.exists()
        calls.append((handle, path))
        downloaded = temporary / path
        downloaded.write_bytes(CSV.encode())
        return str(downloaded)

    monkeypatch.setattr(kagglehub, "dataset_download", fake_download)

    df = load_raw(target, download=True)

    assert calls == [("blastchar/telco-customer-churn/versions/1", RAW_PATH.name)]
    assert target.read_text() == CSV
    assert df["TotalCharges"].isna().tolist() == [True, False]
    assert df.loc[1, "TotalCharges"] == 40.5
    assert data.download_raw(target) == target
    assert load_raw(target, download=True).equals(df)
    assert len(calls) == 1
    assert list(target.parent.iterdir()) == [target]


def test_existing_files_are_verified_without_downloading(
    tmp_path, csv_hash, kagglehub
):
    target = tmp_path / "telco.csv"
    target.write_bytes(CSV.encode())
    original_inode = target.stat().st_ino

    assert data.download_raw(target) == target
    assert load_raw(target, download=True).loc[1, "TotalCharges"] == 40.5
    assert target.stat().st_ino == original_inode

    custom_csv = CSV.replace("40.5", "41.5")
    target.write_bytes(custom_csv.encode())
    with pytest.raises(ValueError, match="SHA-256"):
        data.download_raw(target)
    with pytest.raises(ValueError, match="SHA-256"):
        load_raw(target, download=True)

    custom = load_raw(target, check_hash=False, download=True)
    assert custom.loc[1, "TotalCharges"] == 41.5
    assert target.read_text() == custom_csv
    assert target.stat().st_ino == original_inode


def test_download_can_return_a_file_on_another_filesystem(
    tmp_path, monkeypatch, csv_hash, kagglehub
):
    cached = tmp_path / "kaggle-cache" / RAW_PATH.name
    cached.parent.mkdir()
    cached.write_bytes(CSV.encode())
    target = tmp_path / "raw" / "telco.csv"

    # В Kaggle/Colab клиент может вернуть файл из монтирования,
    # проигнорировав output_dir. Имитируем границу томов без привязки к ОС.
    monkeypatch.setattr(kagglehub, "dataset_download", lambda *args, **kwargs: str(cached))
    original_link = data.os.link

    def cross_device_link(source, destination):
        if Path(source) == cached:
            raise OSError(errno.EXDEV, "Invalid cross-device link")
        return original_link(source, destination)

    monkeypatch.setattr(data.os, "link", cross_device_link)

    df = load_raw(target, download=True)

    assert df.shape == (2, 4)
    assert df["TotalCharges"].isna().tolist() == [True, False]
    assert target.read_bytes() == cached.read_bytes() == CSV.encode()
    assert list(target.parent.iterdir()) == [target]
    assert list(cached.parent.iterdir()) == [cached]


def test_bad_download_is_not_published_even_if_load_hash_check_is_disabled(
    tmp_path, monkeypatch, csv_hash, kagglehub
):
    target = tmp_path / "raw" / "telco.csv"

    def fake_download(handle, *, path, output_dir):
        downloaded = Path(output_dir) / path
        downloaded.write_bytes(CSV.replace("40.5", "41.5").encode())
        return str(downloaded)

    monkeypatch.setattr(kagglehub, "dataset_download", fake_download)

    with pytest.raises(ValueError, match="SHA-256"):
        load_raw(target, check_hash=False, download=True)

    assert not target.exists()
    assert list(target.parent.iterdir()) == []


def test_download_failure_keeps_cause_and_cleans_temporary_files(
    tmp_path, monkeypatch, csv_hash, kagglehub
):
    target = tmp_path / "raw" / "telco.csv"
    failure = OSError("download interrupted")

    def failing_download(handle, *, path, output_dir):
        (Path(output_dir) / path).write_text("partial download")
        raise failure

    monkeypatch.setattr(kagglehub, "dataset_download", failing_download)

    with pytest.raises(RuntimeError, match="data/README.md") as caught:
        load_raw(target, download=True)

    assert caught.value.__cause__ is failure
    assert not target.exists()
    assert list(target.parent.iterdir()) == []


@pytest.mark.parametrize(
    "concurrent_csv",
    [CSV, CSV.replace("40.5", "41.5")],
    ids=["valid", "corrupt"],
)
def test_concurrent_target_is_verified_and_never_overwritten(
    tmp_path, monkeypatch, csv_hash, kagglehub, concurrent_csv
):
    target = tmp_path / "raw" / "telco.csv"
    concurrent_inodes = []

    def fake_download(handle, *, path, output_dir):
        downloaded = Path(output_dir) / path
        downloaded.write_bytes(CSV.encode())
        target.write_bytes(concurrent_csv.encode())
        concurrent_inodes.append(target.stat().st_ino)
        return str(downloaded)

    monkeypatch.setattr(kagglehub, "dataset_download", fake_download)

    if concurrent_csv == CSV:
        assert data.download_raw(target) == target
    else:
        with pytest.raises(ValueError, match="SHA-256"):
            data.download_raw(target)

    assert target.read_text() == concurrent_csv
    assert target.stat().st_ino == concurrent_inodes[0]
    assert list(target.parent.iterdir()) == [target]


@pytest.mark.skipif(not RAW_PATH.exists(), reason="исходный CSV не скачан")
def test_real_file_matches_readme():
    df = load_raw()
    assert df.shape == (7043, 21)
    assert df["customerID"].is_unique
    assert df["TotalCharges"].isna().sum() == 11
    assert (df.loc[df["TotalCharges"].isna(), "tenure"] == 0).all()
    assert (df["Churn"] == "Yes").sum() == 1869
