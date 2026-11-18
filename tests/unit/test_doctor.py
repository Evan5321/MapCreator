"""doctor 的探测逻辑：缺失项、版本下限与输出结构。"""

from __future__ import annotations

from mapcreator import doctor


def test_collect_reports_missing_required_tools() -> None:
    checks = doctor.collect_checks(which=lambda _name: None, run=lambda _args: None)
    by_name = {check.name: check for check in checks}
    for name in ("uv", "node", "npm", "git"):
        assert by_name[name].status == "missing"
        assert by_name[name].required is True
        assert by_name[name].remediation
    assert by_name["python"].status == "ok"
    assert {"name", "status", "value", "required", "remediation"} <= set(by_name["uv"].to_dict())


def test_collect_ok_with_fake_tools() -> None:
    versions = {
        "uv": "uv 0.11.32",
        "node": "v24.16.0",
        "npm": "11.13.0",
        "git": "git version 2.47.0",
    }
    checks = doctor.collect_checks(
        which=lambda name: f"C:/fake/{name}.exe",
        run=lambda args: versions.get(args[0], "1.0.0"),
    )
    by_name = {check.name: check for check in checks}
    for name in ("python", "uv", "node", "npm", "git", "sqlite"):
        assert by_name[name].status == "ok", (name, by_name[name].value)


def test_node_below_minimum_is_missing() -> None:
    checks = doctor.collect_checks(
        which=lambda _name: "C:/fake/node.exe",
        run=lambda _args: "v18.20.0",
    )
    node = {check.name: check for check in checks}["node"]
    assert node.status == "missing"
    assert "20" in (node.remediation or "")


def test_sqlite_capabilities_probe() -> None:
    caps = doctor.probe_sqlite()
    assert set(caps) == {"fts5", "rtree", "trigram"}


def test_render_lines_includes_remediation() -> None:
    lines = doctor.render_lines([doctor.Check("demo", "missing", "未找到", True, "安装它")])
    assert lines[0].startswith("✗ demo")
    assert "安装它" in lines[1]
