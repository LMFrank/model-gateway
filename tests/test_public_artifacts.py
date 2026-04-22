from pathlib import Path


def test_public_artifacts_do_not_leak_private_provider_markers() -> None:
    public_files = [
        Path("README.md"),
        Path("docs/integration.md"),
        Path("docs/runtime-release-sop.md"),
        Path("scripts/verify_runtime.sh"),
        Path("sql/bootstrap_model_gateway.sql"),
    ]
    banned_markers = [
        "qizhi",
        "Kimi-K2.6",
        "openapi-qb-ai.sii.edu.cn",
        "F6yCaUsJj3NMtjbdAxxTmNRwz3zh19DWMImlk8Wkjh4=",
    ]

    for file_path in public_files:
        text = file_path.read_text(encoding="utf-8")
        for marker in banned_markers:
            assert marker not in text, f"{marker!r} leaked in {file_path}"


def test_gitignore_excludes_private_overlay_directories() -> None:
    text = Path(".gitignore").read_text(encoding="utf-8")
    for marker in ("sql/private/", "docs/private/", "scripts/private/"):
        assert marker in text


def test_main_contract_no_longer_exposes_internal_provider_owner() -> None:
    text = Path("app/main.py").read_text(encoding="utf-8")
    assert '"owned_by": PUBLIC_MODEL_OWNER' in text
