# Product Gist: The Harness Composer

**Working title:** *(placeholder — needs a name)*

---

## The One-Line Pitch

A system that takes an incoming task and dynamically composes the right agent harness for it — tool access, context strategy, guardrails, and verification checks — by selecting and assembling pre-vetted, reusable components, the way SonarQube detects a codebase and applies the right quality rules rather than writing new ones each time.

---

## The Origin of the Idea

In a talk at AI Engineer Europe, Tejas Kumar from IBM demonstrated that a model's reliability on agentic tasks comes almost entirely from the harness wrapped around it, not the model itself. He pointed to dynamically assembled, just-in-time harnesses as the open problem the field has not yet solved: today's harnesses are hand-built per agent, in advance, by an engineer who has to anticipate every tool, every context need, every guardrail, and every verification step before the agent ever runs.

The idea here is to solve that specific gap. Not a smarter model. Not a better prompt. A system that looks at the task in front of it and assembles the right harness for that task, automatically, from parts that have already been built and trusted.

---

## Why "Compose, Don't Generate"

The fully generative version of this idea — an agent that writes its own safety logic, its own verification code, its own guardrails from scratch at runtime — is what makes this idea sound risky, and rightly so. Nobody should want an agent inventing its own rules for how to check its own work.

The version worth building is narrower and far more defensible: the system does not write new logic. It selects from a library of components that were built once, reviewed once, tested once, and approved once — and assembles the right combination for the task at hand. The novelty is in the assembly, not the components. This is precisely the SonarQube model: SonarQube does not invent a new static analysis rule when it sees your codebase. It detects what your codebase is and applies the right pre-built rule set from its catalogue.

This framing is what keeps the idea governable rather than speculative.

---

## The Architecture

```
                    ┌─────────────────────┐
   Incoming Task ──▶│   Task Classifier    │
   + Agent Context  │  - Action type       │
                     │  - Reversibility     │
                     │  - Data sensitivity  │
                     │  - External systems  │
                     │    required          │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │  Component Library    │
                     │  ┌──────────────────┐ │
                     │  │ Tool Wrappers     │ │
                     │  ├──────────────────┤ │
                     │  │ Context Strategies│ │
                     │  ├──────────────────┤ │
                     │  │ Guardrail Sets    │ │
                     │  ├──────────────────┤ │
                     │  │ Verification Checks│ │
                     │  └──────────────────┘ │
                     └──────────┬───────────┘
                                │ selects relevant components
                                ▼
                     ┌──────────────────────┐
                     │  Composition Engine   │
                     │  Assembles components │
                     │  into one harness      │
                     │  configuration         │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │  Framework Adapter     │
                     │  ADK plugin /          │
                     │  LangChain hooks /      │
                     │  Bedrock HookProvider / │
                     │  Azure middleware       │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │  Agent runs with the   │
                     │  generated harness     │
                     └──────────────────────┘
```

**Task Classifier.** Given a task description and, optionally, metadata about which agent is running it (a new, unproven agent versus one with a strong track record), determines: is this action reversible or irreversible, does it touch money or personal data, what external systems or tools does it likely need, and what is the appropriate confidence threshold before this task can proceed without human approval. This is the detection layer — analogous to SonarQube detecting language and framework before applying rules.

**Component Library.** The catalogue of pre-built, versioned, independently tested parts.
- *Tool wrappers* — a typed, permissioned wrapper around a specific external capability (a flight booking API, a payment processor, a CRM write operation).
- *Context strategies* — different approaches to managing the context window depending on task length and complexity (minimal context for short lookups, compression and checkpointing for long multi-step tasks).
- *Guardrail sets* — pre-and-post execution checks (a financial threshold guardrail, a PII redaction guardrail, an irreversibility confirmation guardrail).
- *Verification checks* — task-specific methods for confirming an action actually had its intended effect, rather than trusting the model's self-report (checking an external booking system for confirmation, checking a database write actually persisted).

**Composition Engine.** Takes the classifier's output and the available components, and produces a single harness configuration: which tools this task is allowed to call, what context strategy applies, which guardrails are active, and which verification check must pass before the task is marked complete. This is the "generative" step, but it generates a configuration, not code.

**Framework Adapter.** The generated configuration is injected into whichever framework the agent actually runs on, using each framework's native extension point: Google ADK's plugin system, LangChain/LangGraph's pre and post model hooks, AWS Bedrock AgentCore's HookProvider lifecycle events, or Microsoft Agent Framework's middleware pipeline. The agent itself does not need to be rewritten. The harness is injected around it.

---

## What Makes This Different From What Exists

Existing harness tooling — LangChain Deep Agents, Microsoft Agent Framework's Agent Harness, Claude's auto mode classifier, Cursor's three-stage filter — all provide fixed or narrowly dynamic behaviour. A developer builds the harness once, in advance, for a given agent or product. The closest thing to dynamic behaviour that exists today is a single safety classifier deciding allow, deny, or escalate for one action at a time.

Nothing currently takes a task as input and outputs a complete, tailored harness composed from independent, swappable parts. That composition step — task in, full harness configuration out — is the genuine gap.

---

## A Worked Example

Task: "Book me a flight to Edinburgh next Tuesday."

The classifier identifies: this is a financial transaction (payment will be made), it is reversible up to a point (cancellation policies usually apply) but becomes irreversible after a defined window, it requires at least two external systems (a flight search API and a payment processor), and the requesting user has a track record of similar successfully completed tasks.

The composition engine assembles: the flight search tool wrapper and the payment tool wrapper from the tool library, a medium-length context strategy (the task involves a few sequential steps but is not a long-running multi-hour job), the financial-threshold guardrail set at a level appropriate to typical flight costs, and a booking-confirmation verification check that queries the airline's confirmation system directly rather than trusting the agent's report that booking succeeded.

A different task — "Summarise this internal document" — produces a dramatically lighter harness: no payment guardrail, no booking verification, a different context strategy entirely, because the classifier correctly identifies this as a low-stakes, fully reversible, single-system task.

---

## MVP Scope

1. Build the component library first, in one framework, before attempting the classifier or the composition engine. Start with LangChain/LangGraph given its installed base and its accessible pre/post model hooks. A small set of 5 to 10 well-built, well-tested components — a couple of tool wrappers, two context strategies, two or three guardrail sets, two verification check patterns — proves the concept before any classification logic is added.
2. Build the task classifier as a separate, swappable module. Start with a rules-based classifier (explicit logic: does the task description contain payment-related language, does it reference an external irreversible action) before attempting an LLM-based classifier. Rules-based is slower to generalise but far easier to audit and trust early on — and auditability is the entire point of this product.
3. Build the composition engine to map classifier output to component selection. This is largely a lookup and assembly problem at this stage, not a machine learning problem.
4. Add the second framework adapter (likely AWS Bedrock AgentCore, given its already-exposed hook points) once the LangChain version is proven.
5. Validate with one real, narrow use case end to end — ideally something with a genuine financial or compliance dimension, since that is where the value of dynamic guardrail selection is most visible and most defensible.

## What to Defer

- LLM-based task classification — start rules-based, evolve once there is enough real task data to evaluate an LLM classifier against
- Azure and Google ADK adapters — prove the model on two frameworks before generalising to four
- Any notion of agents contributing new components to the library autonomously — every component should be human-reviewed and versioned for the foreseeable future

---

## Open Questions

- How is a new component added to the library, reviewed, and approved? This governance process is as important as the technical architecture, because the entire value proposition rests on every component being trustworthy.
- Does the classifier need to be explainable in a way that satisfies an auditor — i.e., can the system show why a given task was assigned a particular harness configuration, not just what configuration it received?
- What happens when the classifier is wrong — when a task is misclassified as low-stakes but turns out to need stronger guardrails partway through execution? Is there a mechanism for the harness to escalate mid-task, not just at task start?
- Should the agent's own track record (the autonomy calibration concept — fewer overrides over time leading to lighter harnesses for proven task types) be part of the classifier from day one, or added later once there is enough production data to calibrate it safely?

---

*This document is a working gist, not a finished spec. Built from a conversation working through Tejas Kumar's (IBM, AI Engineer Europe) framing of dynamic, on-the-fly harness generation as the next open problem in agent reliability engineering.*
