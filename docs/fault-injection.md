# Fault Injection

Agent Fault can perturb both tool execution and, when an agent exposes a ModelCallExecutor, the model-client call boundary. Use these faults to test how an agent and its retry/error-handling policy respond when tools, model responses, or model APIs fail.

Faults are scheduled explicitly. The trigger selects a named tool call or a numbered model invocation; the fault describes what happens at that boundary.

## Tool faults

Tool faults are applied to calls executed through the scenario's ToolRegistry or a supported integration interceptor.

    from agentfault.testing import (
        MalformedResponseFault, Scenario, ScenarioRunner, ToolTimeoutFault
    )
    from agentfault.testing.triggers import AfterTool, BeforeTool

    scenario = Scenario(
        name="dependency response is corrupted",
        agent=my_agent,
        environment=test_world,
        faults=[
            (BeforeTool("lookup_customer"), ToolTimeoutFault()),
            (AfterTool("read_record"), MalformedResponseFault("{invalid-json")),
        ],
    )
    result = ScenarioRunner(tool_registry).run(scenario)

Built-in tool faults:

- ToolTimeoutFault: raises an injected timeout before the real tool runs.
- TransientToolFailureFault(failures=N): fails the next N matching tool calls and then allows execution.
- LatencyFault(seconds, sleeper=...): delays the matched boundary. Inject a fake sleeper in tests to avoid waiting.
- MalformedResponseFault(response): replaces the tool result with a configured response.
- TruncatedResponseFault(max_length): truncates a common response type to the specified length.
- EmptyResponseFault(): replaces a successful tool response with None.

Response-mutating faults run after the underlying tool succeeds, so the trajectory identifies that call as executed successfully but contains the altered observation. Pre-call failures skip the actual registered function and are recorded as tool errors.

The existing BeforeTool and AfterTool triggers remain supported. They match registered tool-call names exactly.

## Model/API faults

The Agent Fault OpenAI adapter and other adapters that use ModelCallExecutor can simulate failures around the actual model-client invocation:

    from agentfault.testing import (
        AfterModelCall, BeforeModelCall, MalformedModelResponseFault,
        ModelRateLimitFault, Scenario, ScenarioRunner
    )

    scenario = Scenario(
        name="model provider rate limits the second call",
        agent=my_model_aware_agent,
        environment=test_world,
        model_faults=[
            (BeforeModelCall(call_number=2), ModelRateLimitFault()),
            (AfterModelCall(call_number=3), MalformedModelResponseFault(None)),
        ],
    )
    result = ScenarioRunner(tool_registry).run(scenario)

Model fault classes currently include:

- ModelTimeoutFault: injects a timeout before the selected model invocation.
- ModelConnectionFault: simulates a connection failure.
- ModelRateLimitFault: simulates a retryable provider-neutral HTTP 429 error.
- ModelServerErrorFault(status_code=503): simulates an HTTP 5xx error.
- ModelLatencyFault(seconds, sleeper=...): delays the model-call boundary.
- MalformedModelResponseFault(response) and EmptyModelResponseFault(): replace the actual SDK response after the call.

Use BeforeModelCall(n) and AfterModelCall(n) to target the 1-based nth model invocation. Omitting the number matches every model call, while the built-in fault actions are one-shot by default; pass times=N to repeat them.

### Adapter contract

For a model API fault to apply, the agent must expose a model_call_executor that is a ModelCallExecutor and route its actual model-client invocation through model_call_executor.execute(callable). The built-in OpenAI adapter does this. A custom adapter can use the same pattern around its SDK client's create or invoke method.

Agent Fault cannot automatically intercept model calls hidden inside arbitrary frameworks or nodes. Framework-native integrations must wrap the actual model-call path with the same executor. A provider fault that escapes the adapter is returned as a scenario execution error rather than being misclassified as an ordinary tool failure. A benchmark case with an execution error is invalid and does not contribute to a numeric aggregate score.

These model faults are simulated at the adapter call boundary; they do not alter real provider status or transport behavior. To test actual SDK/network retry implementations, additionally test a custom transport/mock server with the provider's supported retry settings.

## Custom faults

For domain-specific behavior, subclass ToolFault or ModelCallFault and override the relevant pre-call or post-response hook. Keep faults deterministic and narrow: each fault should change one condition that can be observed in the trajectory or checked by an assertion.

## Safety

Use a synthetic test environment and test credentials. Response payloads may contain sensitive information; avoid writing real customer data or secrets to logs. See the Safety and Test Isolation guide for broader isolation guidance.