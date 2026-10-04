import hashlib

import pytest

from origami.lab.plate_reader import PlateReaderError, load_plate_csv, parse_plate_csv

HEAD = "well,construct,n_repeats,batch,role,rlu\n"


def test_blank_subtraction_and_sem():
    csv_text = HEAD + (
        "A1,c8,8,b1,blank,10\nA2,c8,8,b1,blank,30\n"
        "B1,c8,8,b1,sample,120\nB2,c8,8,b1,sample,140\n"
    )
    out = parse_plate_csv(csv_text, "plate.csv")
    row = out["observations"][0]
    # blank mean 20 -> corrected 100, 120 -> mean 110
    assert row["y"] == pytest.approx(110.0)
    # unbiased SD = sqrt(200) ; SEM = SD / sqrt(2) = 10
    assert row["sigma"] == pytest.approx(10.0)
    assert row["n_wells"] == 2 and row["units"] == "RLU"
    assert out["calibrated"] is False


def test_single_well_has_no_invented_sigma():
    out = parse_plate_csv(
        HEAD + "A1,c3,3,b1,blank,5\nB1,c3,3,b1,sample,55\n", "p.csv"
    )
    assert out["observations"][0]["sigma"] is None


def test_blanks_are_per_batch():
    text = HEAD + (
        "A1,c,8,b1,blank,0\nA2,c,8,b2,blank,100\n"
        "B1,c,8,b1,sample,50\nB2,c,8,b2,sample,150\n"
    )
    ys = {r["batch"]: r["y"] for r in parse_plate_csv(text, "p").get("observations")}
    assert ys == {"b1": 50.0, "b2": 50.0}


@pytest.mark.parametrize(
    "body,msg",
    [
        ("B1,c,8,b1,sample,5\n", "no blank wells"),
        ("A1,c,8,b1,blank,1\nB1,c,8.5,b1,sample,5\n", "positive integer"),
        ("A1,c,8,b1,blank,1\nB1,c,8,b1,sample,-5\n", "negative"),
        ("A1,c,8,b1,blank,1\nB1,c,8,b1,sample,nan\n", "finite"),
        ("A1,c,8,b1,blank,1\nB1,c,8,b1,other,5\n", "role"),
        ("A1,c,8,b1,blank,1\n", "no sample wells"),
    ],
)
def test_bad_input_rejected(body, msg):
    with pytest.raises(PlateReaderError, match=msg):
        parse_plate_csv(HEAD + body, "p")


def test_missing_columns_rejected():
    with pytest.raises(PlateReaderError, match="missing required columns"):
        parse_plate_csv("well,rlu\nA1,1\n", "p")


def test_output_and_fidelity_are_not_averaged_together():
    text = (
        "well,construct,n_repeats,batch,role,rlu,output,fidelity\n"
        "A1,c,8,b1,blank,0,,\n"
        "B1,c,8,b1,sample,110,luminescence,1\n"
        "C1,c,8,b1,sample,50,locking_fraction,1\n"
    )
    rows = {row["output"]: row for row in parse_plate_csv(text, "p.csv")["observations"]}
    assert rows["luminescence"]["y"] == pytest.approx(110.0)
    assert rows["locking_fraction"]["y"] == pytest.approx(50.0)
    assert rows["luminescence"]["fidelity"] == 1


def test_unknown_output_is_rejected():
    text = (
        "well,construct,n_repeats,batch,role,rlu,output\n"
        "A1,c,8,b1,blank,0,\n"
        "B1,c,8,b1,sample,10,titer\n"
    )
    with pytest.raises(PlateReaderError, match="output"):
        parse_plate_csv(text, "p.csv")


def test_file_checksum_recorded_and_file_untouched(tmp_path):
    f = tmp_path / "plate.csv"
    f.write_text(HEAD + "A1,c,8,b1,blank,1\nB1,c,8,b1,sample,11\n")
    before = f.read_bytes()
    out = load_plate_csv(f)
    assert out["input_sha256"] == hashlib.sha256(before).hexdigest()
    assert f.read_bytes() == before
