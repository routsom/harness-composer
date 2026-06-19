# Contributing to Harness Composer

Thank you for your interest in contributing.

## Quick start

```bash
git clone https://github.com/your-org/harness-composer
cd harness-composer
pip install -e ".[dev]"
pytest  # should show 70 passed
```

## What we're looking for

### High value
- **New components** — tool wrappers, context strategies, guardrails, and verification checks for real-world use cases (Stripe, Twilio, Salesforce, Bedrock, etc.)
- **New framework adapters** — Bedrock AgentCore and Google ADK are next on the roadmap
- **Classifier improvements** — better signal patterns, edge cases, language coverage
- **Real-world examples** — the more specific and realistic, the better

### Also welcome
- Bug fixes with failing test cases
- Documentation improvements
- Performance improvements with benchmarks

## The one rule for component contributions

**Every component that enters the registry is a commitment.**

It will be used by agents making real decisions — financial transactions, outbound messages, data mutations. The governance model is intentional: the PR review is the safety check, not the runtime.

To add a component:

1. Create it in the appropriate `library/` sub-package, subclassing the right base class.
2. Tag it accurately — tags drive composition selection.
3. Write unit tests that cover the full outcome space (`ALLOW`, `BLOCK`, `ESCALATE`, `REDACT` for guardrails; `VERIFIED`, `FAILED`, `UNCERTAIN` for verification checks).
4. Register it in `default_registry()` in `registry.py`.
5. Add it to the component table in `README.md`.

No component will be merged without tests that can run offline (no live API calls in the test suite).

## Code style

```bash
ruff check .          # linting
mypy harness_composer # type checking
```

## Pull request expectations

- Keep PRs focused — one component or one fix per PR.
- Include a plain-English description of what the component does and when the composition engine will select it.
- If your component is for a paid external service, the stub/test path must work without credentials.

## Reporting issues

Open a GitHub issue. For security-sensitive issues (e.g. a guardrail that can be bypassed), please use GitHub's private vulnerability reporting instead of a public issue.
