"""Build local Lambda ZIPs and extract only the two GLB assets. No AWS calls."""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

from common import FIELDS

BASE = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(assets, output):
    model = BASE / "models" / "selected_model.json"
    metrics = BASE / "results" / "step4" / "control_metrics.json"
    if not model.is_file() or not metrics.is_file():
        raise SystemExit("Run simulation.py, train.py and evaluate.py first")
    sha = digest(model)
    evaluation = json.loads(metrics.read_text(encoding="utf-8"))
    if sha != evaluation["model_sha256"] or evaluation["model"] != "random_forest":
        raise SystemExit("Model differs from evaluated RF; run evaluate.py again")
    sys.path.insert(0, str(BASE))
    from inference import load_model
    if load_model(model)["kind"] != "random_forest":
        raise SystemExit("Expected selected Random Forest")
    output.mkdir(parents=True, exist_ok=True)
    files = {"generate.zip": [(HERE / "generate.py", "lambda_function.py"),
                              (HERE / "common.py", "common.py"), (model, "selected_model.json")]
                              + [(BASE / f, f) for f in ("simulation.py", "inference.py", "control.py")],
             "read.zip": [(HERE / "reader.py", "lambda_function.py"), (HERE / "common.py", "common.py")]}
    for name, items in files.items():
        with zipfile.ZipFile(output / name, "w", zipfile.ZIP_DEFLATED) as z:
            for source, target in items:
                z.write(source, target)
        with zipfile.ZipFile(output / name) as z:
            if z.testzip() is not None:
                raise RuntimeError("ZIP integrity failure")
    wanted = {"classroom_demoscene.glb": "classroom/GLTF/classroom_demoscene.glb",
              "COMPUTERdemoscene.glb": "computer/GLTF/COMPUTERdemoscene.glb"}
    with zipfile.ZipFile(assets) as z:
        for name, suffix in wanted.items():
            matches = [p for p in z.namelist() if p.endswith("/" + suffix) and not p.startswith("__MACOSX/")]
            if len(matches) != 1:
                raise ValueError(f"Expected one asset: {suffix}")
            content = z.read(matches[0])
            if content[:4] != b"glTF" or int.from_bytes(content[4:8], "little") != 2 or int.from_bytes(content[8:12], "little") != len(content):
                raise ValueError(f"Invalid GLB: {name}")
            (output / name).write_bytes(content)
    schema = {name: {"dataType": {"type": kind}, "isTimeSeries": True, "isStoredExternally": True}
              for name, (kind, _, _) in FIELDS.items()}
    (output / "property-definitions.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
    manifest = {"model_sha256": sha, "files": {p.name: {"bytes": p.stat().st_size, "sha256": digest(p)}
                 for p in sorted(output.iterdir()) if p.name in set(files) | set(wanted) | {"property-definitions.json"}}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    print("Package ready:", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=BASE / "aws" / "dist")
    args = parser.parse_args()
    main(args.assets, args.output)
