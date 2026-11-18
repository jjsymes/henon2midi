import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "henon2midi"
FORBIDDEN_FOR_DOMAIN = {"mido", "click"}
FORBIDDEN_PREFIXES = ("henon2midi.output", "henon2midi.cli", "henon2midi.run")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_output_adapters_do_not_import_the_application():
    output_files = list((ROOT / "output").glob("*.py"))
    assert output_files
    for path in output_files:
        modules = _imported_modules(path)
        assert all(
            not module.startswith(("henon2midi.cli", "henon2midi.run", "click"))
            for module in modules
        ), path.name
        assert "click" not in {module.split(".")[0] for module in modules}


def test_mapping_does_not_depend_on_controller_names():
    modules = _imported_modules(ROOT / "domain" / "mapping.py")
    assert "henon2midi.domain.controls" not in modules


def test_domain_does_not_import_adapters_or_frameworks():
    domain_files = list((ROOT / "domain").glob("*.py"))
    assert domain_files
    for path in domain_files:
        modules = _imported_modules(path)
        top_levels = {module.split(".")[0] for module in modules}
        assert top_levels.isdisjoint(FORBIDDEN_FOR_DOMAIN)
        assert all(
            not module.startswith(FORBIDDEN_PREFIXES) for module in modules
        ), path.name
