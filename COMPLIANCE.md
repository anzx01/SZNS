# Compliance and Responsible Use

This document is an engineering checklist and public project notice, not legal
advice. Laws and institutional policies vary by jurisdiction and use case. If
you publish this project from a company, lab, university, or regulated
environment, have the release reviewed by the appropriate legal, compliance,
security, and safety owners.

## Project Status

This repository is a local MVP for adaptive experiment optimization,
simulation-based validation, plugin management, and report generation.

It is not:

- A certified safety controller.
- A certified rail, power electronics, industrial, medical, aviation, defense,
  energy, or critical infrastructure system.
- A substitute for laboratory safety procedures, equipment interlocks,
  standards compliance, calibration, qualified engineering review, or operator
  approval.
- A guarantee that recommended parameters are safe for real equipment.

## Experiment and Equipment Safety

Before connecting the platform to real instruments, simulators, hardware, or
plant data, users should:

- Add an explicit human approval step for every action that can affect physical
  equipment.
- Keep hardware interlocks, emergency stops, current/voltage/temperature limits,
  and independent safety systems outside this software.
- Validate every plugin against known safe datasets before live use.
- Treat generated recommendations and reports as decision support only.
- Document experiment-specific limits, calibration status, operator training,
  and rollback procedures outside the codebase.

## Data and Privacy

The application runs locally and does not intentionally call external services.
Imported datasets, generated reports, and event logs are stored under `data/`
and `logs/`. These directories are ignored by Git by default because they may
contain sensitive experiment data, customer data, personal data, equipment
configuration, or incident information.

Do not publish:

- Raw customer, lab, employee, student, patient, or operator data.
- Personal data or identifiers.
- Proprietary waveforms, test procedures, failure data, or equipment settings.
- Security credentials, network details, API keys, certificates, or private
  keys.
- Export-controlled, classified, confidential, or contract-restricted technical
  data.

Synthetic or anonymized data should be reviewed for re-identification and
commercial sensitivity before release.

## Third-Party Intellectual Property

Do not add code, models, reports, datasets, images, or plugins copied from
third parties unless the repository includes a compatible license notice and
required attribution.

Commercial simulation environments, instrument SDKs, equipment manuals, test
procedures, and vendor models may have license terms that limit public
redistribution. Keep such integrations out of the public repository unless you
have written permission to publish them.

## Export Controls and Sanctions

This project is intended as general-purpose research software. Users are
responsible for complying with export control, sanctions, procurement, and
technology transfer rules that apply to their location, organization, users,
datasets, and end use.

Do not publish or accept contributions containing controlled technical data,
restricted equipment parameters, circumvention methods, or regulated know-how
without an appropriate review and authorization.

## Plugin Risk

External plugins are imported as local Python code and can execute with the
same operating-system permissions as the application process. Review plugin
source before loading it, especially when it can:

- Read or write local files.
- Call subprocesses or network services.
- Connect to instruments, simulators, databases, or message buses.
- Generate reports for external distribution.
- Influence safety limits or optimization recommendations.

Public plugins should be small, auditable, and free of secrets, proprietary
algorithms, real-world safety limits, and unpublished customer or laboratory
data.

## Release Review Checklist

Before making the repository public, complete
`OPEN_SOURCE_RELEASE_CHECKLIST.md`. For company or institutional releases, also
record the approver, date, license choice, data review result, and any excluded
materials in your internal release system.

## Reference Links

- GitHub documentation on licensing a repository:
  https://docs.github.com/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository/
- GitHub documentation on adding a security policy:
  https://docs.github.com/en/code-security/getting-started/adding-a-security-policy-to-your-repository
- SPDX MIT License identifier and canonical text:
  https://spdx.org/licenses/MIT
- GitHub trade controls policy:
  https://docs.github.com/site-policy/other-site-policies/github-and-trade-controls
- U.S. EAR public information reference, 15 CFR 734.7:
  https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-734/section-734.7
