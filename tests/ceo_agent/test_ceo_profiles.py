import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TPL = ROOT / "ceo-agent" / "profiles" / "templates"
INSTALL = ROOT / "ceo-agent" / "scripts" / "install_ceo_profiles.py"
EXPECTED = {"ceo-agent", "cfo-agent", "coo-agent", "cto-agent", "cmo-agent", "chro-agent",
            "clo-agent", "sales-intake-agent", "onboarding-comms-agent"}


def run(home, *extra):
    return subprocess.run([sys.executable, str(INSTALL), "--home", str(home), "--principal", "Test Principal",
                           "--business", "Test Co", *extra], capture_output=True, text=True, check=True)


def test_templates_complete_and_tenant_blind():
    assert {p.name for p in TPL.iterdir() if p.is_dir()} == EXPECTED
    for p in EXPECTED:
        text = (TPL / p / "SOUL.md").read_text(encoding="utf-8")
        assert "Lane guard" in text and "Off limits" in text
        assert "JECI" not in text and "Adrian" not in text
        json.loads((TPL / p / "meta.json").read_text(encoding="utf-8"))


def test_install_renders_all_placeholders(tmp_path):
    run(tmp_path)
    for p in EXPECTED:
        soul = (tmp_path / "profiles" / p / "SOUL.md").read_text(encoding="utf-8")
        assert not re.search(r"\{\{[A-Z_]+\}\}", soul)
        assert "Test Principal" in soul or p.endswith("intake-agent") or p.startswith("onboarding")
        assert "skin: ceo-agent" in (tmp_path / "profiles" / p / "config.yaml").read_text()
        assert "hermes-bots" in (tmp_path / "profiles" / p / "profile.yaml").read_text()


def test_install_never_clobbers_existing(tmp_path):
    d = tmp_path / "profiles" / "cto-agent"; d.mkdir(parents=True)
    (d / "SOUL.md").write_text("MY CUSTOM SOUL", encoding="utf-8")
    run(tmp_path)
    assert (d / "SOUL.md").read_text(encoding="utf-8") == "MY CUSTOM SOUL"
    assert (d / "SOUL.ceo-agent.md").exists()
    run(tmp_path, "--force")
    assert (d / "SOUL.md.bak").read_text(encoding="utf-8") == "MY CUSTOM SOUL"


def test_skin_loads():
    sys.path.insert(0, str(ROOT))
    from hermes_cli import skin_engine
    skin = skin_engine.load_skin("ceo-agent")
    assert skin.get_branding("agent_name") == "CEO Agent"
    assert skin.colors["ui_accent"] == "#8b5cf6"
