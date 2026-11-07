import pytest

from src.data import RAW_PATH, load_raw

CSV = "customerID,tenure,TotalCharges,Churn\nA,0, ,No\nB,2,40.5,Yes\n"


def test_blank_total_charges_become_nan(tmp_path):
    path = tmp_path / "telco.csv"
    path.write_text(CSV)
    df = load_raw(path, check_hash=False)
    assert df["TotalCharges"].isna().tolist() == [True, False]
    assert df.loc[1, "TotalCharges"] == 40.5


def test_other_garbage_is_not_silenced(tmp_path):
    path = tmp_path / "telco.csv"
    path.write_text(CSV.replace("40.5", "abc"))
    with pytest.raises(ValueError):
        load_raw(path, check_hash=False)


def test_wrong_hash_rejected(tmp_path):
    path = tmp_path / "telco.csv"
    path.write_text(CSV)
    with pytest.raises(ValueError, match="SHA-256"):
        load_raw(path)


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="data/README.md"):
        load_raw(tmp_path / "nope.csv")


@pytest.mark.skipif(not RAW_PATH.exists(), reason="исходный CSV не скачан")
def test_real_file_matches_readme():
    df = load_raw()
    assert df.shape == (7043, 21)
    assert df["customerID"].is_unique
    assert df["TotalCharges"].isna().sum() == 11
    assert (df.loc[df["TotalCharges"].isna(), "tenure"] == 0).all()
    assert (df["Churn"] == "Yes").sum() == 1869
