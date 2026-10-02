import importlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "src"))

service, out = sys.argv[1], sys.argv[2]
app = importlib.import_module(f"{service}.app.app").app
Path(out).write_text(json.dumps(app.openapi(), sort_keys=True), encoding="utf-8")
