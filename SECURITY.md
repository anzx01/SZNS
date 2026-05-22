# Security Policy

## Supported Versions

This repository is currently an MVP. Security fixes are considered for the
default branch and the latest tagged release, if releases exist.

## Reporting a Vulnerability

Please do not open public issues for exploitable vulnerabilities or accidental
secret exposure.

Report security issues privately by using GitHub private vulnerability
reporting if it is enabled for the repository. If it is not enabled, contact
the maintainer through the private channel listed on the GitHub repository
profile or organization page.

Include:

- Affected version or commit.
- Steps to reproduce.
- Impact and expected behavior.
- Any proof of concept needed to confirm the issue.
- Whether the issue involves secrets, personal data, export-controlled data, or
  physical equipment safety.

## Security Boundaries

The default server is intended for local use on `127.0.0.1`. The MVP does not
include authentication, authorization, TLS, multi-user isolation, sandboxed
plugin execution, or hardened file upload controls.

Do not expose the server directly to a public network without adding the
security controls required for your environment.

## Plugin Security

External plugins are local Python code. Load only trusted plugins and review
their source before use. A malicious plugin can read files, alter reports,
change recommendations, or interact with connected systems using the
permissions of the application process.

## Secret Handling

Do not commit secrets. The repository ignores common local environment and key
files, but automated checks are not a substitute for review. Rotate any secret
that was committed or pushed, even if it is later removed from Git history.
