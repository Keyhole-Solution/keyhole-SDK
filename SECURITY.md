Security Policy

This document describes how to report security issues for the Keyhole Developer Kit and how the Keyhole maintainers handle vulnerability reports.

The Keyhole Developer Kit provides the public developer interface to the Keyhole ecosystem, including SDKs, schemas, documentation, and the Keyhole Test Runtime.

Supported Scope

This security policy applies to the contents of this repository, including:

SDK packages

the Keyhole Test Runtime container

public API contracts and schemas

example integrations

deployment templates

documentation

This repository does not include the private Keyhole platform, including governance engines, promotion infrastructure, or internal control-plane systems.

Security reports concerning the public developer kit are welcome and appreciated.

Reporting a Vulnerability

If you discover a security vulnerability, please report it privately.

Do not open a public GitHub issue for security vulnerabilities.

Instead, contact:

security@keyholesolution.com

Include as much detail as possible:

description of the vulnerability

affected file(s) or component(s)

steps required to reproduce the issue

proof-of-concept code or requests (if available)

potential impact of the vulnerability

If applicable, include:

runtime logs

request/response examples

dependency versions

This helps us assess and resolve the issue quickly.

Response Process

When a vulnerability report is received, the Keyhole maintainers will:

Acknowledge receipt of the report.

Investigate the issue and determine severity.

Develop a fix or mitigation.

Publish a patch or update.

Disclose the vulnerability responsibly once remediation is available.

We aim to respond to security reports as quickly as possible.

Responsible Disclosure

We ask that security researchers follow responsible disclosure practices:

Do not publicly disclose vulnerabilities before a fix is available.

Allow maintainers time to investigate and address the issue.

Avoid exploiting vulnerabilities beyond what is necessary to demonstrate the problem.

Responsible disclosure helps protect users of the Keyhole Developer Kit.

Security Considerations for Builders

The Keyhole Test Runtime included in this repository is designed as a development and integration tool, not a hardened production system.

Builders deploying the runtime should consider:

running it behind a reverse proxy (such as Traefik)

restricting network access when appropriate

using TLS for public deployments

avoiding exposure of development instances to untrusted networks

Deployment guidance is available in:

docs/traefik-deploy.md
Dependency Security

Dependencies used by the SDKs and runtime should be kept up to date.

Maintainers periodically review dependency updates and may release updates to address security advisories.

Users are encouraged to:

keep dependencies current

monitor upstream advisories

update SDK versions when new releases are published

Supported Versions

Security fixes will typically be applied to the latest release of the Developer Kit.

Older versions may not receive patches.

Thank You

We appreciate the work of security researchers and developers who help improve the safety and reliability of the Keyhole ecosystem.

If you believe you have found a security issue, please report it privately using the process described above.