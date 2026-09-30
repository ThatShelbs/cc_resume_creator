"""Write the API's OpenAPI schema to webapp/frontend/openapi.json so
`npm run gen:api` can turn the server's Pydantic models into TypeScript types
(src/lib/api-schema.d.ts). Run from anywhere; no server needs to be running."""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from taylor.api import create_app  # noqa: E402
from taylor.jobs import JobManager  # noqa: E402
from taylor.paths import Paths  # noqa: E402


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(Paths(Path(tmp)), "schema-export", jobs=JobManager())
        schema = app.openapi()
    out = ROOT / "webapp" / "frontend" / "openapi.json"
    out.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
