Contributing to the Keyhole Developer Kit

Thank you for your interest in contributing to the Keyhole Developer Kit.

This repository provides the public developer surface for the Keyhole ecosystem. Contributions help improve the experience for builders integrating with Keyhole-compatible runtimes.

Before contributing, please read the guidelines below to ensure changes remain aligned with the purpose and architecture of this repository.

Purpose of This Repository

The Keyhole Developer Kit exists to provide:

public SDKs

public runtime contracts

a test runtime for local and third-party deployment

integration examples

deployment templates

documentation for external builders

This repository intentionally does not include private Keyhole platform components, such as governance engines, promotion kernel internals, or production control-plane logic.

**keyhole-developer-kit** is a separate governed participant — not a nested
subcomponent of the platform source tree. Contributors should discover
platform capabilities through the MCP boundary (`GET /mcp/v1/capabilities`),
not through private platform source inspection.

Contributions should respect this boundary.

Types of Contributions Welcome

We welcome contributions that improve the developer experience and strengthen the public integration surface.

Examples include:

Documentation improvements

clarifying developer workflows

improving setup instructions

fixing errors or inconsistencies

adding usage examples

Example integrations

Examples demonstrating interaction with the public runtime surface are encouraged:

bridge implementations

SDK usage examples

deployment scenarios

smoke tests

Examples should remain small, executable, and easy to understand.

SDK improvements

Improvements to SDK ergonomics, type safety, or documentation are welcome.

Changes should remain aligned with the public runtime contract and avoid introducing assumptions about private platform internals.

Test runtime improvements

Enhancements to the public Keyhole Test Runtime may be accepted when they:

improve determinism

improve clarity of behavior

strengthen contract validation

improve developer usability

The runtime should remain small and intentionally bounded.

Contribution Principles

All contributions should follow these principles.

Preserve the public boundary

This repository must remain a clean public interface to the Keyhole ecosystem.

Do not introduce:

internal platform code

private governance logic

production secrets

references to internal infrastructure

undocumented internal APIs

Keep examples simple

Examples should prioritize clarity over complexity.

They should demonstrate:

the runtime contract

expected request/response behavior

deterministic replay patterns

Maintain deterministic behavior

The test runtime is intended to behave predictably and reproducibly.

Avoid introducing behavior that depends on:

external services

unstable state

environment-specific dependencies

Respect versioned contracts

Public contracts, schemas, and APIs should remain stable.

Breaking changes require:

versioning

documentation updates

migration guidance

Development Setup

Clone the repository:

git clone https://github.com/Keyhole-Solution/keyhole-developer-kit.git
cd keyhole-developer-kit

Start the test runtime locally:

docker compose up

Verify the runtime:

curl http://localhost:8080/healthz
curl http://localhost:8080/identity

Run the bridge smoke test:

cd examples/bridge-smoke-test
./smoke-test.sh

Windows users can run:

./smoke-test.ps1
Coding Standards
Python

Follow standard Python practices:

PEP 8 formatting

clear docstrings

type hints where appropriate

simple, readable logic

Avoid unnecessary dependencies.

Documentation

Documentation should be:

concise

technically precise

written for external builders

Prefer executable examples over long explanations.

Commit messages

Write clear commit messages describing the change.

Example:

docs: clarify runtime deployment instructions
examples: add bridge smoke test payload
sdk: improve error handling in client
Submitting a Contribution

Fork the repository

Create a feature branch

git checkout -b feature/my-improvement

Make your changes

Commit with clear messages

Push your branch

Open a Pull Request

Describe:

what changed

why it improves the developer experience

how the change was tested

Pull Request Review

Pull requests will be reviewed for:

correctness

clarity

alignment with repository goals

adherence to public boundary principles

Maintainers may request revisions before merging.

Reporting Issues

If you encounter problems using the Developer Kit, please open an issue and include:

steps to reproduce

expected behavior

actual behavior

runtime logs if relevant

Security Issues

If you discover a potential security issue, please follow the process described in:

SECURITY.md

Do not publicly disclose security vulnerabilities before they are reviewed.

License

By contributing to this repository, you agree that your contributions will be licensed under the terms specified in the repository’s LICENSE.

Thank You

Your contributions help make the Keyhole developer ecosystem easier to adopt and more reliable for builders.