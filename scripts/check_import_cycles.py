from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ModuleNode:
    name: str
    path: Path
    package: str


@dataclass(frozen=True)
class BoundaryViolation:
    importer: str
    imported: str
    importer_layer: str
    imported_layer: str


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect import cycles for local Python modules.",
    )
    parser.add_argument(
        "--package",
        action="append",
        default=None,
        help="Package directory to scan (relative to repo root). Can be provided multiple times. Default: main_app",
    )
    parser.add_argument(
        "--check-boundaries",
        action="store_true",
        help="Check top-level architecture import boundaries in addition to cycle detection.",
    )
    parser.add_argument(
        "--enforce-boundaries",
        action="store_true",
        help="Return non-zero when boundary violations are found (requires --check-boundaries).",
    )
    return parser.parse_args()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _package_paths(root: Path, package_args: list[str] | None) -> list[Path]:
    package_names = package_args or ["main_app"]
    paths: list[Path] = []
    for package_name in package_names:
        candidate = (root / str(package_name).strip()).resolve()
        if not candidate.exists() or not candidate.is_dir():
            raise FileNotFoundError(f"Package path not found: {package_name}")
        paths.append(candidate)
    return paths


def _module_name_from_path(package_path: Path, py_file: Path) -> tuple[str, str]:
    relative = py_file.relative_to(package_path.parent)
    if py_file.name == "__init__.py":
        module_parts = relative.parts[:-1]
    else:
        module_parts = relative.with_suffix("").parts

    module_name = ".".join(module_parts)
    if py_file.name == "__init__.py":
        package_name = module_name
    else:
        package_name = ".".join(module_parts[:-1])
    return module_name, package_name


def _discover_modules(package_paths: Iterable[Path]) -> dict[str, ModuleNode]:
    modules: dict[str, ModuleNode] = {}
    for package_path in package_paths:
        for py_file in package_path.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            module_name, package_name = _module_name_from_path(package_path, py_file)
            if module_name:
                modules[module_name] = ModuleNode(
                    name=module_name,
                    path=py_file,
                    package=package_name,
                )
    return modules


def _known_module(module_set: set[str], candidate: str) -> str | None:
    normalized = str(candidate).strip()
    while normalized:
        if normalized in module_set:
            return normalized
        if "." not in normalized:
            return None
        normalized = normalized.rsplit(".", 1)[0]
    return None


def _resolve_from_base(current_package: str, module: str | None, level: int) -> str:
    if level <= 0:
        return (module or "").strip()

    package_parts = [part for part in current_package.split(".") if part]
    remove_count = max(level - 1, 0)
    if remove_count > len(package_parts):
        package_parts = []
    else:
        package_parts = package_parts[: len(package_parts) - remove_count]

    if module:
        package_parts.extend(part for part in module.split(".") if part)
    return ".".join(package_parts)


def _extract_top_level_import_targets(
    *,
    source: str,
    module_name: str,
    current_package: str,
    module_set: set[str],
) -> set[str]:
    targets: set[str] = set()
    tree = ast.parse(source, filename=module_name)

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                found = _known_module(module_set, alias.name)
                if found:
                    targets.add(found)
            continue

        if not isinstance(node, ast.ImportFrom):
            continue

        base = _resolve_from_base(
            current_package=current_package,
            module=node.module,
            level=node.level,
        )
        base_target = _known_module(module_set, base)
        if any(alias.name == "*" for alias in node.names):
            if base_target:
                targets.add(base_target)
            continue

        for alias in node.names:
            nested_candidate = f"{base}.{alias.name}" if base else alias.name
            nested_target = _known_module(module_set, nested_candidate)
            if nested_target:
                targets.add(nested_target)
                continue
            if base_target:
                targets.add(base_target)

    if module_name in targets:
        targets.remove(module_name)
    return targets


def _build_graph(modules: dict[str, ModuleNode]) -> dict[str, set[str]]:
    module_set = set(modules.keys())
    graph: dict[str, set[str]] = defaultdict(set)
    for module_name, module in modules.items():
        source = module.path.read_text(encoding="utf-8-sig")
        imports = _extract_top_level_import_targets(
            source=source,
            module_name=module_name,
            current_package=module.package,
            module_set=module_set,
        )
        graph[module_name].update(imports)
    for module_name in modules:
        graph.setdefault(module_name, set())
    return graph


def _strongly_connected_components(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indexes: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indexes[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for neighbour in graph.get(node, set()):
            if neighbour not in indexes:
                visit(neighbour)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbour])
            elif neighbour in on_stack:
                lowlinks[node] = min(lowlinks[node], indexes[neighbour])

        if lowlinks[node] != indexes[node]:
            return

        component: list[str] = []
        while stack:
            popped = stack.pop()
            on_stack.remove(popped)
            component.append(popped)
            if popped == node:
                break
        components.append(component)

    for candidate in sorted(graph.keys()):
        if candidate not in indexes:
            visit(candidate)

    return components


def _cycle_components(graph: dict[str, set[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    for component in _strongly_connected_components(graph):
        if len(component) > 1:
            cycles.append(sorted(component))
            continue
        module_name = component[0]
        if module_name in graph.get(module_name, set()):
            cycles.append(component)
    return sorted(cycles, key=lambda item: ",".join(item))


def _infer_layer(module_name: str) -> str:
    if not module_name.startswith("main_app."):
        return "external"
    parts = module_name.split(".")
    if len(parts) < 2:
        return "root"
    return parts[1]


def _allowed_dependencies() -> dict[str, set[str]]:
    return {
        "app": {"platform", "orchestration", "domains", "ui", "shared", "plugins", "infrastructure", "services"},
        "ui": {"platform", "orchestration", "domains", "shared", "services"},
        "orchestration": {"platform", "shared", "plugins", "services"},
        "domains": {"platform", "shared", "services"},
        "platform": {"shared", "services"},
        "plugins": {"platform", "orchestration", "shared", "services"},
        "shared": {"platform", "services"},
        "infrastructure": {"platform", "shared", "services"},
        "services": {"platform", "shared", "plugins", "infrastructure", "orchestration", "domains"},
        "parsers": {"platform", "shared", "services"},
        "mindmap": {"platform", "shared", "services"},
        "schemas": {"platform", "shared", "services"},
    }


def _boundary_violations(graph: dict[str, set[str]]) -> list[BoundaryViolation]:
    allow_map = _allowed_dependencies()
    always_allowed = {"constants", "contracts", "models"}
    violations: list[BoundaryViolation] = []
    for importer, imports in graph.items():
        importer_layer = _infer_layer(importer)
        if importer_layer in always_allowed:
            continue
        allowed = allow_map.get(importer_layer, set())
        for imported in imports:
            imported_layer = _infer_layer(imported)
            if imported_layer == "external" or imported_layer == importer_layer:
                continue
            if imported_layer in always_allowed:
                continue
            if imported_layer in allowed:
                continue
            violations.append(
                BoundaryViolation(
                    importer=importer,
                    imported=imported,
                    importer_layer=importer_layer,
                    imported_layer=imported_layer,
                )
            )
    return sorted(violations, key=lambda item: (item.importer_layer, item.importer, item.imported))


def main() -> int:
    args = _parse_args()
    root = _repo_root()
    try:
        package_paths = _package_paths(root, args.package)
    except FileNotFoundError as exc:
        print(str(exc))
        return 2

    modules = _discover_modules(package_paths)
    if not modules:
        print("No Python modules found for cycle check.")
        return 0

    graph = _build_graph(modules)
    cycles = _cycle_components(graph)
    if cycles:
        print("Import cycles detected:")
        for component in cycles:
            chain = " -> ".join(component + [component[0]])
            print(f"- {chain}")
        return 1

    print(f"No import cycles found across {len(modules)} module(s).")
    if not args.check_boundaries:
        return 0

    violations = _boundary_violations(graph)
    if not violations:
        print("No architecture boundary violations found.")
        return 0

    print("Architecture boundary violations detected:")
    for violation in violations:
        print(
            f"- {violation.importer} ({violation.importer_layer}) imports "
            f"{violation.imported} ({violation.imported_layer})"
        )
    if args.enforce_boundaries:
        return 1
    print("Boundary violations are in warning mode. Re-run with --enforce-boundaries to fail on violations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
