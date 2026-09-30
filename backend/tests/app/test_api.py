"""The HTTP API, driven through FastAPI's test client with a fake pipeline."""

import json
import time

from fastapi.testclient import TestClient

from resume_taylor.sample_data import demo_data
from support import EXAMPLES_DIR, JOB_TEXT


def test_api_requires_token_and_loopback_host(client):
    assert client.get("/api/health").status_code == 200
    bare = TestClient(client.app)
    assert bare.get("/api/projects").status_code == 403
    assert bare.get("/api/projects?t=tok").status_code == 200
    evil = TestClient(client.app, base_url="http://attacker.example")
    assert evil.get("/api/health", headers={"X-Taylor-Token": "tok"}).status_code == 421


def test_api_profile_and_resume_flow(client, workspace):
    body = client.get("/api/profile").json()
    assert body["exists"] and body["profile"]["contact"]["name"] == "Jordan Rivera"
    body["profile"]["sections"].append({"title": "Certifications", "items": ["None yet, and that's fine"]})
    saved = client.put("/api/profile", json=body["profile"]).json()
    assert saved["backup"] and saved["profile"]["sections"][-1]["title"] == "Certifications"

    bad = {**body["profile"], "contact": {**body["profile"]["contact"], "email": "nope"}}
    assert client.put("/api/profile", json=bad).status_code == 400

    with open(EXAMPLES_DIR / "in_resume_example.docx", "rb") as fh:
        up = client.post("/api/resume/upload", files={"file": ("my resume.docx", fh)}).json()
    assert not up["needs_ai"] and up["structure"]["jobs"][0]["company"] == "Northwind Traders"
    confirmed = client.post("/api/resume/confirm", json={"structure": up["structure"], "upload_id": up["upload_id"]}).json()
    assert confirmed["file"] == "in_resume_Jordan-Rivera.docx"
    # The demo fact bank names Fabrikam Health, which this smaller resume doesn't have.
    assert any(i["employer"] == "Fabrikam Health" for i in confirmed["fact_bank_issues"])
    assert client.post("/api/resume/upload", files={"file": ("x.exe", b"MZ")}).status_code == 400


def test_api_project_generate_edit_render(client):
    created = client.post("/api/projects", json={"job_text": JOB_TEXT, "company": "Example Co.", "role": "Director"}).json()
    pid = created["project"]["id"]
    job = client.post(f"/api/projects/{pid}/generate").json()

    events = []
    with client.stream("GET", f"/api/jobs/{job['id']}/events") as resp:
        for line in resp.iter_lines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())
            if events and events[-1] == "end" and line.startswith("data:"):
                final = json.loads(line[5:])
                break
    assert events[0] in ("lines", "status") and events[-1] == "end"
    assert final["status"] == "succeeded"

    detail = client.get(f"/api/projects/{pid}").json()
    assert detail["result"]["summary"] == demo_data.DEMO_RESULT["summary"]
    assert detail["project"]["last_generate"]["ok"] and not detail["project"]["inputs_changed"]
    assert [f["name"] for f in detail["outputs"]][0].startswith("out_resume_")

    result = detail["result"]
    result["summary"] = "Edited by hand."
    assert client.put(f"/api/projects/{pid}/result", json=result).json()["outputs_stale"] is True
    lint = client.post(f"/api/projects/{pid}/lint", json=result).json()
    assert "counts" in lint

    job = client.post(f"/api/projects/{pid}/render", json={"template": "compact"}).json()
    end = time.time() + 20
    while client.get(f"/api/jobs/{job['id']}").json()["status"] not in ("succeeded", "failed") and time.time() < end:
        time.sleep(0.05)
    detail = client.get(f"/api/projects/{pid}").json()
    assert detail["project"]["template"] == "compact" and detail["result"]["summary"] == "Edited by hand."

    name = detail["outputs"][0]["name"]
    assert client.get(f"/api/projects/{pid}/files/{name}").status_code == 200
    assert client.get(f"/api/projects/{pid}/files/..%2Fproject.json").status_code == 404
    assert client.get(f"/api/projects/{pid}/report").text == "# Report"

    trash = client.delete(f"/api/projects/{pid}").json()["trash_id"]
    assert client.get(f"/api/projects/{pid}").status_code == 404
    assert client.post(f"/api/trash/{trash}/restore").status_code == 200


def test_api_import_legacy_postings(client, workspace):
    (workspace.input_dir / "in_job_example.txt").write_text(JOB_TEXT, encoding="utf-8")
    candidates = client.get("/api/import/candidates").json()
    assert candidates == [{"file": "in_job_example.txt", "company": "Example Co.", "role": "Director, Customer Analytics"}]
    assert len(client.post("/api/import", json={"files": ["in_job_example.txt"]}).json()["created"]) == 1
    assert client.get("/api/import/candidates").json() == []
