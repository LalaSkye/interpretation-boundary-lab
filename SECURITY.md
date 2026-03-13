# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public issue.
2. Email the maintainer with a description of the vulnerability.
3. Include steps to reproduce if possible.

We will acknowledge receipt within 48 hours and provide a timeline for a fix.

## Scope

This project is a deterministic admissibility layer with no network access,
no file system writes (beyond CLI output), and no external dependencies in core.
The attack surface is limited to malformed input handling.

## Design Guarantees

- **Fail-closed**: All unspecified states are impermissible by default.
- **No hidden state**: All decisions are traceable to named rules.
- **No execution authority**: The interpretation layer (INTERPRET_X) cannot create authority.
- **Deterministic**: Same inputs always produce the same outputs.
