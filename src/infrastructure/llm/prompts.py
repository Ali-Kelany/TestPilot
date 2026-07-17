ACTOR_SYSTEM = """You are an expert web automation agent. Your task is to perform specific UI actions on a web application.

RULES:
1. FOCUS: Only perform the action described in "Current Action". Do not do extra steps.
2. CHAINING: You may execute multiple tools in one turn if they are logically connected.
3. ORDERING: Respect dependencies (e.g., fill inputs BEFORE clicking submit).
4. COMPLETION: Once the current action is fully achieved, call finish_task() as the VERY LAST tool call. Do not call anything after it. If you have no browser actions to take, call finish_task() immediately.
5. Reference Global Memory for data from prior steps.
6. If an element is missing, use scroll() or wait().

ELEMENT STATE INDICATORS:
- [DISABLED]: Cannot interact — skip or enable first
- [CHECKED: true/false]: Checkbox/radio state
- [EXPANDED: true/false]: Dropdown/accordion state"""


ASSERTOR_SYSTEM = """You are a visual verification specialist with cross-step reasoning ability.

You will receive:
- A screenshot of the current page
- The action just performed
- The assertion to verify
- (Optional) A summary of prior steps in this test session

Your job is to determine whether the assertion is satisfied, taking into account not only what you
see right now but also how it relates to what happened in earlier steps.

Specifically, watch for:
- Temporal dependencies: did something that was true in an earlier step correctly persist or change?
- Causal dependencies: did the current action produce the expected effect relative to the prior state?
- Data dependencies: are values (counts, totals, labels) consistent with data established in prior steps?

Output ONLY a JSON object with two fields:
- "passed": (boolean) true if the assertion is clearly satisfied, false otherwise
- "reason": (string) concise explanation citing the visual evidence, and any cross-step reasoning used

Do not include markdown formatting, preamble, or conversational text outside the JSON."""


RECOVERY_SYSTEM = """You are a failure analysis expert.

Analyze the failure and decide if the test step is recoverable.
Output your decision as a JSON object with:
- "should_retry": (boolean) true for loading delays, popups, timing issues, or temporary glitches. false for wrong page, logic errors, or missing features.
- "reason": (string) Explanation of why a retry is or is not recommended.

Be conservative - retry only if there's a reasonable chance of success. Do not include markdown or preamble."""


def format_observation(
    action: str, assertion: str, memory: dict, elements: str
) -> str:
    """Format the observation prompt for the actor LLM."""
    mem_str = (
        "\n".join(f"  • {k}: {v}" for k, v in memory.items())
        if memory
        else "  (empty)"
    )

    return f"""Current Action: {action}
Expected outcome: {assertion}

Global Memory:
{mem_str}

Visible Elements:
{elements}"""


def format_assertion_prompt(
    assertion: str,
    action: str,
    memory: dict,
    step_history: list[dict] | None = None,
) -> str:
    """Format the prompt for assertion verification."""
    mem_str = (
        "\n".join(f"  • {k}: {v}" for k, v in memory.items())
        if memory
        else "  (empty)"
    )

    history_section = ""
    if step_history:
        lines = []
        for entry in step_history:
            lines.append(
                f"  Step {entry['step']} [{entry.get('title', '')} | {entry.get('url', '')}]\n"
                f"    Action:    {entry['action']}\n"
                f"    Assertion: {entry['assertion']}\n"
                f"    Outcome:   {entry['outcome']}"
            )
        history_section = "\nPrior Steps Context:\n" + "\n".join(lines) + "\n"

    return f"""Context — the agent just performed this action:
"{action}"

Expected Result: {assertion}

Global Memory:
{mem_str}
{history_section}
Analyze the screenshot above and verify if this assertion is satisfied.
Use the prior steps context (if any) to reason about temporal, causal, or data dependencies."""


def format_recovery_prompt(
    action: str, assertion: str, log_entries: list[str]
) -> str:
    """Format the prompt for recovery analysis."""
    log_str = (
        "\n".join(log_entries[-5:]) if log_entries else "(no log entries)"
    )

    return f"""Failed Step Analysis:

Action: {action}
Expected: {assertion}

Recent Log:
{log_str}

Should we retry this step?"""