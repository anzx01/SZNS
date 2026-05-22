# External Plugin Packages

The platform scans one folder per plugin package:

```text
plugins/
  conservative_optimizer/
    plugin.json
    plugin.py
```

`plugin.json` is the package manifest:

```json
{
  "id": "optimizer:ConservativeOptimizerPlugin",
  "name": "ConservativeOptimizerPlugin",
  "type": "optimizer",
  "key": "conservative_external",
  "version": "0.1.0",
  "entrypoint": "plugin:ConservativeOptimizerPlugin",
  "default_loaded": true,
  "description": "A local external optimizer package.",
  "notes": "Loaded from plugins/conservative_optimizer/plugin.py"
}
```

External package scanning supports `optimizer`, `feature`, `model`, `constraint`, `report`, and `data_source` plugins. The entry class must implement the interface required by its `type`. For an optimizer:

```python
def recommend(self, runs: list[dict], config: dict) -> dict:
    return {
        "recommended_parameters": {},
        "expected_improvement": {},
        "optimizer": "MyOptimizerPlugin",
        "reasons": []
    }
```

After adding a package, use the workbench reload action or call `POST /api/plugins/reload`. The plugin appears in the workbench plugin catalog and, when loaded, participates in the corresponding workflow.

## Licensing and safety

Plugin packages in this repository are distributed under the repository MIT License unless a plugin package states otherwise. Do not submit plugins that contain proprietary algorithms, third-party code, controlled technical data, real customer data, secrets, credentials, or device-specific safety limits unless you have documented permission to publish them.

External plugins are imported as local Python code. Review and run only plugins from trusted sources, especially before connecting the platform to real instruments, simulators, or datasets.
