"""Write the API's OpenAPI schema to frontend/openapi.json so
`npm run gen:api` can turn the server's Pydantic models into TypeScript types
(src/lib/api/schema.d.ts). Run from anywhere; no server needs to be running."""

import json
import tempfile
from pathlib import Path

from resume_taylor.app.main import create_app
from resume_taylor.app.services.jobs import JobManager
from resume_taylor.app.storage.paths import Paths
from resume_taylor.layout import FRONTEND_DIR, REPO_ROOT


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(Paths(Path(tmp)), "schema-export", jobs=JobManager())
        schema = app.openapi()
    out = FRONTEND_DIR / "openapi.json"
    out.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Wrote {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
