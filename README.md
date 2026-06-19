<br>

<div align="center">

# Harness Composer

**The missing layer between your agent and disaster.**

*Dynamically compose the right guardrails, tools, context strategy, and verification checks for any task — automatically, from parts that have already been built and trusted.*

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-70%20passing-brightgreen.svg)](#)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

## The Problem Nobody Has Solved Yet

At AI Engineer Europe, Tejas Kumar (IBM) put it plainly: *"A model's reliability on agentic tasks comes almost entirely from the harness wrapped around it, not the model itself."*

Then he named the open problem: **dynamically assembled, just-in-time harnesses.**

Today, every agent harness is **hand-built in advance** by an engineer who has to anticipate every tool, every guardrail, every verification step — before the agent ever sees a real task.

The result: a flight-booking agent and a document-summarisation agent get the same static harness. Or none at all.

```
Today                               With Harness Composer
─────────────────────────────────   ─────────────────────────────────────────────
Engineer writes harness in advance  System looks at the task, assembles the right
for every agent, for every use      harness from pre-approved parts — automatically
case. Works until it doesn't.       every single time.
```

---

## How It Works

Harness Composer looks at the task in front of it and assembles the right harness for that task, from components that have already been built, reviewed, and approved.

**The novelty is in the assembly, not the components.**

This is the [SonarQube](https://www.sonarsource.com/products/sonarqube/) model: SonarQube doesn't invent a new static analysis rule when it sees your codebase. It detects what your codebase is and applies the pre-built rule set that fits. That's what makes it governable.

```
                    ┌──────────────────────┐
  Incoming Task ───▶│   Task Classifier     │
                    │  · action type        │
                    │  · reversibility      │
                    │  · data sensitivity   │
                    │  · external systems   │
                    └──────────┬───────────┘
                               │ TaskProfile
                               ▼
                    ┌──────────────────────┐
                    │   Component Library   │
                    │  ┌────────────────┐  │
                    │  │ Tool Wrappers  │  │  pre-built
                    │  │ Ctx Strategies │  │  versioned
                    │  │ Guardrail Sets │  │  human-reviewed
                    │  │ Verif. Checks  │  │  independently tested
                    │  └────────────────┘  │
                    └──────────┬───────────┘
                               │ selects relevant components
                               ▼
                    ┌──────────────────────┐
                    │  Composition Engine   │──▶ HarnessConfig
                    │  (config, not code)   │    (serialisable, auditable)
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Framework Adapter    │
                    │  LangChain · Bedrock  │
                    │  ADK · Azure          │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Agent runs with the  │
                    │  right harness        │
                    └──────────────────────┘
```

---

## See It In Action

Two tasks. Same system. Dramatically different harnesses.

```python
from harness_composer import HarnessComposer
from harness_composer.registry import default_registry

composer = HarnessComposer(registry=default_registry())
```

**Task 1: High-stakes booking**

```python
harness = composer.compose(
    "Book me a flight to Edinburgh next Tuesday and pay with my corporate card."
)
print(harness.summary())
```

```
HarnessConfig(
  risk=critical, action=transact,
  context=context_compression,
  guardrails=[financial_threshold, irreversibility_confirmation],
  verification=[external_confirmation]
)
```

**Task 2: Read-only summary**

```python
harness = composer.compose(
    "Summarise this internal document for the quarterly review."
)
print(harness.summary())
```

```
HarnessConfig(
  risk=low, action=read,
  context=context_minimal,
  guardrails=[],
  verification=[]
)
```

Same API call. The right harness, automatically. No engineer had to write either of them in advance.

---

## Quickstart

```bash
pip install -e ".[dev]"
```

```bash
# See both examples side by side
python examples/flight_booking.py
python examples/document_summary.py
```

### Wire into a LangChain agent

```python
from harness_composer import HarnessComposer
from harness_composer.registry import default_registry
from harness_composer.adapters.langchain import LangChainAdapter

registry = default_registry()
composer  = HarnessComposer(registry=registry)
adapter   = LangChainAdapter(registry=registry)

task    = "Transfer £800 to the supplier's account."
harness = composer.compose(task)

# Option A — inject into an AgentExecutor
agent = adapter.inject(harness, agent_executor)

# Option B — pass as RunnableConfig (non-mutating)
config = adapter.build_runnable_config(harness)
chain.invoke({"input": task}, config=config)
```

The adapter:
- Runs guardrail checks before every tool call (`on_tool_start`)
- Runs verification checks after every tool call (`on_tool_end`)
- Filters the agent's tool list to only what the harness authorises (least privilege)
- Raises `GuardrailViolation` on `BLOCK` outcomes — the agent sees a hard error, not a silent bypass

---

## The Component Library

Every component is **pre-built, versioned, and human-reviewed** before it enters the registry. Nothing reaches an agent through dynamic discovery.

### Tool Wrappers

| Component | What it does |
|---|---|
| `web_search` | Read-only web search. Inject any real client (Tavily, SerpAPI). |
| `http_request` | Generic HTTP with domain allow-listing and mutation gating. |

### Context Strategies

| Component | When to use |
|---|---|
| `context_minimal` | Short, single-step tasks. Keeps system prompt + last N messages only. |
| `context_compression` | Multi-step tasks. Running summary of old messages + tail verbatim. |

### Guardrail Sets

| Component | What it catches |
|---|---|
| `financial_threshold` | Blocks/escalates transactions above configurable soft and hard limits. |
| `pii_redaction` | Detects and redacts emails, phone numbers, NI/SSN, postcodes, card numbers. |
| `irreversibility_confirmation` | Requires explicit confirmation token before irreversible actions. |

### Verification Checks

| Component | What it confirms |
|---|---|
| `external_confirmation` | Re-queries the external system directly — not the agent's self-report. |
| `database_write` | Re-reads the record after a write to confirm it actually persisted. |

---

## Why "Compose, Don't Generate"

The scary version of this idea is an agent that **writes its own guardrails at runtime**. Nobody should want that.

The safe version — the one worth building — is narrower: the system **selects** from a library of components that were built once, reviewed once, tested once, and approved once. The composition step generates a *configuration*, not *code*.

This is what keeps it governable.

> The composition engine never writes new logic. It assembles existing, trusted parts into the right combination for the task at hand.

Every harness decision is auditable because the classifier records exactly which signals fired and why — stored in `TaskProfile.matched_signals`. You can reconstruct any composition decision from logs alone.

---

## The Classifier Is Explainable By Design

The rules-based classifier records every signal that drove the classification:

```python
profile = composer.classifier.classify(
    "Book me a flight to Edinburgh and pay with my corporate card."
)

print(profile.matched_signals)
# ['payment', 'book_ticket', 'flight_api', 'payment_api']

print(profile.risk_level)      # RiskLevel.CRITICAL
print(profile.action_type)     # ActionType.TRANSACT
print(profile.is_reversible)   # False
print(profile.requires_human_approval)  # True
print(profile.classifier_version)       # 'rules-based-1.0'
```

An auditor can trace exactly why a given task got its harness. No black box.

---

## Governance: Adding a Component

The entire value proposition rests on every component being trustworthy. The governance gate is the PR — not the runtime.

1. **Create** your component in the appropriate `library/` sub-package, subclassing the relevant base:
   ```python
   class PaymentProcessorWrapper(BaseToolWrapper):
       ...
   ```

2. **Tag it** accurately — tags drive composition selection:
   ```python
   tags=frozenset({"financial", "payment", "payment_processor"})
   ```

3. **Write tests** in `tests/test_components.py` — every component must be independently testable.

4. **Register it** in `default_registry()` in `registry.py`:
   ```python
   PaymentProcessorWrapper(api_key=..., allowed_domains={"api.stripe.com"}),
   ```

5. **Open a PR.** The review happens here — not at agent runtime.

> The registry is intentionally append-only at runtime. A component that is registered cannot be replaced or removed without a restart and a code change.

---

## Roadmap

- [x] Rules-based task classifier with explainable signal recording
- [x] Component library: 2 tool wrappers, 2 context strategies, 3 guardrails, 2 verification checks
- [x] Composition engine: tag-based, fully deterministic
- [x] LangChain / LangGraph adapter
- [ ] AWS Bedrock AgentCore adapter (HookProvider lifecycle events)
- [ ] Google ADK adapter (plugin system)
- [ ] LLM-based classifier (once there is enough production signal data to validate it against rules-based)
- [ ] Mid-task escalation — harness can escalate based on what the agent discovers during execution, not just at task start
- [ ] Agent track record integration — lighter harnesses for agents with strong proven histories

---

## What This Is Not

- **Not a prompt framework.** Harness Composer doesn't touch your prompts.
- **Not a model router.** It doesn't choose which model runs the task.
- **Not an agent framework.** It wraps around whichever framework you already use.
- **Not a generative guardrail system.** It never writes new safety logic at runtime.

---

## Running the Tests

```bash
python3.11 -m pytest tests/ -v
```

```
70 passed in 1.19s
```

---

## Origin

This project was built from a product gist that came out of a conversation around Tejas Kumar's (IBM) talk at [AI Engineer Europe](https://www.ai.engineer/europe), where he identified dynamically assembled, just-in-time harnesses as the open problem in agent reliability.

The full product thinking is in [`product_gist_harness_composer.md`](product_gist_harness_composer.md).

---

## Contributing

Pull requests are welcome. For significant changes, please open an issue first to discuss what you'd like to change.

For component contributions specifically: follow the governance steps above. Every component that reaches the registry is a commitment — to users of this library and to their agents' downstream actions.

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

[Apache 2.0](LICENSE)
