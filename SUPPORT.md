Support

This document describes how to get help with the Keyhole Developer Kit.

The Developer Kit provides the public integration surface for Keyhole, including SDKs, the test runtime, contracts, and example integrations.

Getting Help

If you need help using the Keyhole Developer Kit, the following resources are available.

Documentation

Start with the documentation included in this repository:

README.md — overview and quickstart

docs/quickstart.md — developer onboarding

docs/test-runtime.md — test runtime behavior and API surface

docs/bridge-contract.md — public integration model

docs/architecture.md — repository architecture

docs/traefik-deploy.md — deployment behind Traefik

These documents cover the most common setup and integration workflows.

Examples

Example integrations are available in the examples/ directory.

Current examples include:

examples/
└── bridge-smoke-test/

The bridge smoke test demonstrates how to interact with the Keyhole Test Runtime using simple HTTP requests and scripts.

Examples are intended to be small, executable reference implementations.

Opening an Issue

If you encounter a bug, documentation error, or unexpected behavior, please open a GitHub issue.

Include:

a description of the problem

steps required to reproduce the issue

expected behavior

actual behavior

relevant logs or error messages

This helps maintainers diagnose and resolve issues more quickly.

Questions and Discussion

Questions about usage, integration patterns, or developer workflows can also be asked through GitHub issues.

When possible, include:

the component you are working with (SDK, runtime, examples, etc.)

your environment (OS, Python version, Docker version, etc.)

the commands or code you attempted

Security Issues

If you believe you have discovered a security vulnerability, please do not open a public issue.

Instead, follow the instructions in:

SECURITY.md

Security reports should be submitted privately.

Scope of Support

Support provided through this repository applies to:

SDK usage

the Keyhole Test Runtime

public schemas and contracts

example integrations

documentation in this repository

The Keyhole Developer Kit does not include the private Keyhole platform or its internal control-plane components.

Community Contributions

Many improvements to documentation, examples, and tooling come from community contributions.

If you would like to contribute, please see:

CONTRIBUTING.md
Response Expectations

Issues are reviewed as time permits. Maintainers will do their best to respond and assist when possible.

For best results:

provide clear reproduction steps

include relevant configuration details

keep questions focused on the public developer kit.

Thank you for helping improve the Keyhole developer ecosystem.