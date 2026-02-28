from __future__ import annotations

from importlib import import_module
import logging
from pkgutil import iter_modules
from typing import Any, TypeVar


logger = logging.getLogger(__name__)

PluginType = TypeVar("PluginType")


def discover_module_plugins(
    *,
    package_name: str,
    plugin_type: type[PluginType],
    single_attr: str = "PLUGIN",
    multi_attr: str = "PLUGINS",
) -> list[PluginType]:
    try:
        package = import_module(package_name)
    except ModuleNotFoundError:
        logger.warning("Plugin package not found: %s", package_name)
        return []

    package_paths = getattr(package, "__path__", None)
    if package_paths is None:
        return []

    discovered: list[PluginType] = []
    for module_info in sorted(iter_modules(package_paths), key=lambda item: item.name):
        module_name = module_info.name
        if module_name.startswith("_"):
            continue
        full_module_name = f"{package_name}.{module_name}"
        try:
            module = import_module(full_module_name)
        except (ImportError, AttributeError, RuntimeError, TypeError, ValueError) as exc:
            logger.exception("Failed to import plugin module '%s': %s", full_module_name, exc)
            continue
        discovered.extend(
            _extract_module_plugins(
                module=module,
                plugin_type=plugin_type,
                single_attr=single_attr,
                multi_attr=multi_attr,
                module_name=full_module_name,
            )
        )
    return discovered


def _extract_module_plugins(
    *,
    module: Any,
    plugin_type: type[PluginType],
    single_attr: str,
    multi_attr: str,
    module_name: str,
) -> list[PluginType]:
    plugins: list[PluginType] = []

    single_plugin = getattr(module, single_attr, None)
    if isinstance(single_plugin, plugin_type):
        plugins.append(single_plugin)

    plugin_collection = getattr(module, multi_attr, None)
    if isinstance(plugin_collection, (list, tuple)):
        for item in plugin_collection:
            if isinstance(item, plugin_type):
                plugins.append(item)
            else:
                logger.warning(
                    "Ignoring invalid plugin entry in module '%s': expected %s, got %s",
                    module_name,
                    plugin_type.__name__,
                    type(item).__name__,
                )
    return plugins
