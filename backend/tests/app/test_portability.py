"""Portability: the API key, the data root, and the sample data."""

from resume_taylor.app.storage import credentials as credentials_mod
from resume_taylor.app.storage.paths import Paths, default_data_root
from support import make_client

FAKE_KEY = "sk-ant-api03-" + "A1b2C3d4E5" * 3


def test_api_key_is_never_returned_or_settings_leaked(workspace):
    c = make_client(workspace)
    assert c.put("/api/settings/api-key", json={"key": "not a key"}).status_code == 400
    r = c.put("/api/settings/api-key", json={"key": FAKE_KEY})
    assert r.json() == {"set": True, "source": "app", "last4": FAKE_KEY[-4:]}
    for url in ("/api/settings", "/api/system", "/api/settings/api-key"):
        assert FAKE_KEY not in c.get(url).text
    assert credentials_mod.load_key(workspace.secrets_path) == FAKE_KEY
    assert c.delete("/api/settings/api-key").json()["set"] is False
    assert not workspace.secrets_path.exists()


def test_api_key_reaches_jobs_and_logs_are_redacted(workspace):
    assert credentials_mod.redact(f"boom {FAKE_KEY} end") == "boom sk-ant-*** end"


def test_default_data_root_is_outside_the_repo(monkeypatch, tmp_path):
    monkeypatch.delenv("RESUME_TAYLOR_DATA", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert default_data_root() == tmp_path / "ResumeTaylor"
    monkeypatch.setenv("RESUME_TAYLOR_DATA", str(tmp_path / "mine"))
    assert default_data_root() == (tmp_path / "mine").resolve()


def test_sample_data_loads_only_into_an_empty_folder_and_clears(tmp_path):
    paths = Paths(tmp_path)
    paths.ensure()
    c = make_client(paths)
    assert c.get("/api/system").json()["onboarding_needed"] is True
    assert c.post("/api/demo/load").status_code == 200
    system = c.get("/api/system").json()
    assert system["sample_loaded"] and not system["onboarding_needed"]
    assert c.post("/api/demo/load").status_code == 409
    assert c.post("/api/demo/clear").json()["backup"] is None
    system = c.get("/api/system").json()
    assert not system["sample_loaded"] and system["onboarding_needed"]
    assert not [p for p in paths.projects_dir.iterdir() if p.is_dir() and not p.name.startswith("_")]


def test_sample_data_refuses_to_mix_with_a_real_profile(workspace):
    assert make_client(workspace).post("/api/demo/load").status_code == 409
