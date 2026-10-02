import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", "src.ui.cli", *args],
        cwd=ROOT, capture_output=True, text=True,
    )


def test_import_plate_cli(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text(
        "well,construct,n_repeats,batch,role,rlu\n"
        "A1,c,8,b1,blank,10\nB1,c,8,b1,sample,110\nB2,c,8,b1,sample,130\n"
    )
    r = _run("import-plate", str(f))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["observations"][0]["y"] == 110.0


def test_import_plate_cli_rejects_bad_file(tmp_path):
    f = tmp_path / "p.csv"
    f.write_text("well,rlu\nA1,1\n")
    r = _run("import-plate", str(f))
    assert r.returncode == 2 and "missing required columns" in r.stderr


def test_ablation_cli(tmp_path):
    n = 12
    d = {
        "X": [[i / n] for i in range(n)],
        "y_mech": [1.0 + i / n for i in range(n)],
        "y_obs": [1.5 + i / n for i in range(n)],
        "groups": [f"g{i % 3}" for i in range(n)],
    }
    f = tmp_path / "d.json"
    f.write_text(json.dumps(d))
    r = _run("ablation", str(f))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["calibrated"] is False
