# Contributing

Thanks for helping improve this project.

## License of Contributions

By submitting a contribution, you agree that it may be distributed under the
repository MIT License.

Each commit should be signed off using the Developer Certificate of Origin
style trailer:

```text
Signed-off-by: Your Name <you@example.com>
```

This confirms that you wrote the contribution yourself, or otherwise have the
right to submit it under this project's license.

## Do Not Submit

Please do not submit:

- Proprietary, confidential, classified, export-controlled, or contract-limited
  material.
- Real customer, operator, employee, student, patient, or partner data.
- Secrets, tokens, credentials, private keys, certificates, or internal network
  details.
- Third-party code, models, datasets, images, reports, or documentation unless
  their license is compatible and attribution is included.
- Device-specific safety limits, unpublished equipment behavior, or operational
  procedures that you are not allowed to publish.

## Pull Request Checklist

Before opening a pull request:

- Run the test suite with `bash scripts/test.sh`.
- For plugin changes, run `uv run python -m lab_mvp.plugins validate plugins/<package>`.
- Update README or plugin documentation when behavior changes.
- Add or update tests for changed behavior.
- Review generated files, sample data, reports, images, and logs for sensitive
  or third-party content.

## Code of Conduct

Participation in this project is governed by `CODE_OF_CONDUCT.md`.
