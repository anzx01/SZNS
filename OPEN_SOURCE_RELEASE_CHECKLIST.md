# Open Source Release Checklist

Use this checklist before making the GitHub repository public and before major
public releases.

## License and Copyright

- Confirm that `LICENSE` contains the intended license and copyright holder.
- Confirm that `pyproject.toml` and `README.md` refer to the same license.
- Confirm that third-party files have compatible licenses and attribution.
- Confirm that sample plugins, sample datasets, and images may be published.

## Sensitive Data

- Confirm that `data/` contains only `.gitkeep` in Git.
- Confirm that `logs/` contains only `.gitkeep` in Git.
- Confirm that no `.env`, key, certificate, token, private configuration, or
  local tool settings file is tracked.
- Run a secret scan before pushing.
- Review Git history for earlier commits that may contain secrets or sensitive
  local configuration.

## Safety and Compliance

- Confirm that no real equipment limits, unpublished procedures, customer data,
  incident data, or export-controlled technical data are included.
- Confirm that README and docs clearly state that this is an MVP and not a
  certified safety system.
- Confirm that any company, university, lab, grant, contract, or customer
  release approval has been completed.
- Confirm that public issues and examples do not ask users to bypass safety
  controls or connect unreviewed plugins to real equipment.

## Engineering

- Run `bash scripts/test.sh`.
- Run plugin validation for each package under `plugins/`.
- Check that generated reports, uploads, caches, and virtual environments are
  ignored.
- Check that the app starts locally and binds only to `127.0.0.1` by default.

## GitHub Repository Settings

- Enable private vulnerability reporting if available.
- Enable secret scanning and push protection if available for the repository.
- Add repository topics, description, and license metadata.
- Consider requiring signed-off commits or documented contribution provenance.
