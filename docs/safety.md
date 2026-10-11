# Safety and Test Isolation

Agent Fault is a testing and evaluation toolkit, **not a security sandbox**. It does not automatically make a production agent or its tools safe.

Perturbations affect the environment passed to the scenario or integration. The tool registry and integration interceptor can only observe and perturb calls that are routed through them. Direct network calls, unregistered functions, unwrapped framework nodes, callbacks, and external side effects may bypass that boundary.

## Use a safe test environment

Before running an agent under Agent Fault:

- Use fake services, fixtures, disposable resources, or a dedicated sandbox.
- Point tools at test endpoints and test accounts. Do not provide production credentials to a test run.
- Disable or stub real write operations such as purchases, refunds, account changes, emails, deployments, and data deletion.
- Use least-privilege credentials and network restrictions as an additional control, not as a replacement for mocks and isolation.
- Create a fresh environment per scenario and prevent mutable state from leaking between cases.
- Avoid including secrets, customer records, private documents, or other sensitive data in trajectories or CI logs.

An external LLM provider may still receive the prompt and tool observations sent to it. Review your provider, data-handling, and retention requirements before using private application data.

## Know what is and is not observed

Agent Fault can make guarantees only about the calls routed through the configured executor or integration hook and the assertions you have implemented. For example, a `ProhibitedActionAssertion("issue_refund")` can detect successful calls with that name recorded in the trajectory. It cannot detect a refund made directly over an unrelated HTTP client, and in v0.1.0 the built-in assertion does not fail solely because a matching tool call was attempted but returned an error.

For a framework-owned loop, instrument the real execution path. The current LangGraph integration supports synchronous `invoke` and sequential calls through the configured `ToolNode`; it does not cover async execution, parallel ordering, or tools executed through other paths. See [Integrations](integrations.md).

## Recommended workflow

1. Prove the scenario with a deterministic local fake.
2. Test that the perturbation is applied when expected and that the trajectory captures the relevant calls.
3. Assert the business invariant, including whether unsafe actions must not be attempted or must not succeed.
4. Add adapter-level tests for every execution mode you claim to support.
5. Only connect a more realistic environment once the test boundaries and credentials have been reviewed; keep destructive operations stubbed or explicitly disabled.

Do not use the getting-started or repository example configurations against live purchase, payment, refund, or customer systems. Those examples assume an isolated synthetic world and are not production protections.
