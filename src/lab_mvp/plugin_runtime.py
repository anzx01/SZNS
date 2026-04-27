from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PluginSpec:
    id: str
    name: str
    type: str
    experiment_type: str | None = None
    key: str | None = None
    source: str = "builtin"
    version: str = "0.1.0"
    description: str = ""
    default_loaded: bool = True
    available: bool = True
    required: bool = False
    notes: str = ""


class RuntimePluginManager:
    def __init__(self, store, specs: list[PluginSpec]):
        self.store = store
        self.specs = {spec.id: spec for spec in specs}
        self.name_index = {spec.name: spec.id for spec in specs}

    def catalog(self) -> list[dict]:
        return [self._entry(spec) for spec in self.specs.values()]

    def load(self, plugin_id: str) -> dict:
        spec = self._spec(plugin_id)
        if not spec.available:
            raise ValueError(f"{spec.name} 当前不可加载：{spec.notes or '缺少运行时依赖。'}")
        self.store.save_plugin_state(spec.id, True)
        return self._entry(spec)

    def unload(self, plugin_id: str) -> dict:
        spec = self._spec(plugin_id)
        if spec.required:
            raise ValueError(f"{spec.name} 是核心插件，不能卸载。")
        self.store.save_plugin_state(spec.id, False)
        return self._entry(spec)

    def is_loaded(self, plugin_id_or_name: str) -> bool:
        spec = self._spec(plugin_id_or_name)
        return self._loaded(spec)

    def require(self, plugin_id_or_name: str) -> None:
        spec = self._spec(plugin_id_or_name)
        if not spec.available:
            raise ValueError(f"{spec.name} 当前不可用：{spec.notes or '缺少运行时依赖。'}")
        if not self._loaded(spec):
            raise ValueError(f"{spec.name} 已卸载，请先在插件目录中加载。")

    def _entry(self, spec: PluginSpec) -> dict:
        loaded = self._loaded(spec)
        if not spec.available:
            status = "optional"
        elif loaded:
            status = "active"
        else:
            status = "unloaded"
        return {
            "id": spec.id,
            "name": spec.name,
            "type": spec.type,
            "experiment_type": spec.experiment_type,
            "key": spec.key,
            "source": spec.source,
            "version": spec.version,
            "description": spec.description,
            "status": status,
            "loaded": loaded,
            "loadable": spec.available,
            "can_unload": spec.available and not spec.required,
            "required": spec.required,
            "notes": spec.notes,
        }

    def _loaded(self, spec: PluginSpec) -> bool:
        if not spec.available:
            return False
        state = self.store.plugin_states().get(spec.id)
        if state is None:
            return spec.default_loaded
        return bool(state.get("loaded"))

    def _spec(self, plugin_id_or_name: str) -> PluginSpec:
        plugin_id = plugin_id_or_name
        if plugin_id not in self.specs:
            plugin_id = self.name_index.get(plugin_id_or_name, "")
        if plugin_id not in self.specs:
            raise ValueError(f"未知插件：{plugin_id_or_name}")
        return self.specs[plugin_id]
