# Privacy and Data Handling

This project is designed as a local-first MVP. The default server binds to
`127.0.0.1` and the application does not intentionally transmit data to an
external service.

## Data Stored Locally

The application may write:

- Project, configuration, run, recommendation, report, event, and plugin state
  metadata to `data/store.json`.
- Imported datasets to `data/uploads/`.
- Generated reports to `data/reports/`.
- Server and test logs to `logs/`.
- UI panel state and other convenience settings to browser local storage.

The repository ignores `data/*` and `logs/*` except `.gitkeep` placeholders.
Keep that behavior unless you have deliberately reviewed and sanitized the
files being published.

## Data You Should Not Import Into a Public Demo

Avoid importing or committing:

- Personal data, contact information, account identifiers, or operator names.
- Customer, partner, vendor, or institution-confidential data.
- Proprietary waveforms, failure logs, procedures, or equipment settings.
- Credentials, tokens, certificates, private keys, network locations, or access
  control information.
- Export-controlled, classified, or contract-restricted technical data.

## Reports and Exports

Project exports can include dataset contents and event details. HTML reports
can include metrics, labels, timestamps, notes, and experiment context. Review
exports and reports before sharing them outside the local environment.

## Browser Storage

The frontend may store UI preferences in browser local storage. Clear browser
site data for `http://127.0.0.1:8765` if you need to remove local UI state.

## Operators and Deployers

If you deploy this project beyond localhost, you are responsible for adding
appropriate authentication, authorization, transport security, logging policy,
data retention controls, and privacy notices for your users.
