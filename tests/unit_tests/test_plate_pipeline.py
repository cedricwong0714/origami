import pytest

from origami.ssdk.plate_pipeline import learn_from_plate

CSV = (
    "well,construct,n_repeats,batch,role,rlu\n"
    "A1,x,3,b1,blank,10\n"
    "B1,x,3,b1,sample,110\nB2,x,3,b1,sample,130\n"
    "C1,x,8,b1,sample,310\nC2,x,8,b1,sample,330\n"
    "D1,x,14,b1,sample,210\nD2,x,14,b1,sample,230\n"
)


def test_plate_to_learn(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text(CSV)
    out = learn_from_plate(f, n_min=3, n_max=20)
    assert out["n_observations"] == 3
    assert out["calibrated"] is False
    assert out["plate_provenance"]["n_rows"] == 3
    assert len(out["plate_provenance"]["input_sha256"]) == 64


def test_observations_option_rejected(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text(CSV)
    with pytest.raises(ValueError, match="plate file"):
        learn_from_plate(f, observations=[])
