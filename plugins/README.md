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

For this MVP, external package scanning supports `optimizer` plugins. The entry class must implement:

```python
def recommend(self, runs: list[dict], config: dict) -> dict:
    return {
        "recommended_parameters": {},
        "expected_improvement": {},
        "optimizer": "MyOptimizerPlugin",
        "reasons": []
    }
```

After adding a package, restart `python .\app.py`. The plugin appears in the workbench plugin catalog and, when loaded, in the optimizer selector.
