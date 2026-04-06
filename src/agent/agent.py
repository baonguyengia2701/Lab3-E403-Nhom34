import re
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class ReActAgent:
    """
    A ReAct-style Agent that follows the Thought-Action-Observation loop.
    The agent repeatedly:
      1. Generates a Thought and an Action using the LLM.
      2. Parses the Action and executes the corresponding tool.
      3. Appends the Observation to the conversation and repeats.
    The loop terminates when the LLM produces a 'Final Answer' or max_steps is reached.
    """

    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def get_system_prompt(self) -> str:
        """
        Build the system prompt that instructs the agent to follow the ReAct format.
        Includes tool descriptions and few-shot examples to reduce parse errors.
        """
        tool_descriptions = "\n".join(
            [f"- {t['name']}: {t['description']}" for t in self.tools]
        )

        few_shot_examples = """
Example 1 — calculation:
User: What is 18% VAT on 1,500,000 VND?
Thought: I need to calculate 18% of 1,500,000.
Action: calculator(18/100 * 1500000)
Observation: 270000
Thought: The VAT amount is 270,000 VND.
Final Answer: The 18% VAT on 1,500,000 VND is 270,000 VND.

Example 2 — date query:
User: How many days until 2027?
Thought: I need to find out how many days are left until January 1, 2027.
Action: datetime(days_until:2027-01-01)
Observation: There are 270 days remaining until 2027-01-01.
Thought: I now have the answer.
Final Answer: There are 270 days remaining until January 1, 2027.

Example 3 — multi-step:
User: What is today's date and how many days until 2030?
Thought: I should first get today's date.
Action: datetime(today)
Observation: Today's date is Monday, April 06, 2026.
Thought: Now I need the countdown to 2030.
Action: datetime(days_until:2030-01-01)
Observation: There are 1366 days remaining until 2030-01-01.
Final Answer: Today is April 6, 2026, and there are 1,366 days until January 1, 2030.
"""

        return f"""You are an intelligent assistant that reasons step-by-step before acting.

You have access to the following tools:
{tool_descriptions}

Always use EXACTLY this format (no deviations):
Thought: <your reasoning about what to do next>
Action: <tool_name>(<argument>)
Observation: <result of the tool — filled in automatically>
... (repeat Thought/Action/Observation as many times as needed)
Final Answer: <your complete answer to the user>

Rules:
- Only call ONE tool per Action line.
- The Action line must match the pattern: ToolName(argument)
- Do NOT invent Observation values — they will be provided automatically.
- When you have enough information, write "Final Answer:" followed by your response.
- If you cannot answer even after {self.max_steps} steps, write "Final Answer: I was unable to determine the answer."

{few_shot_examples}
"""

    # ------------------------------------------------------------------
    # Main ReAct loop
    # ------------------------------------------------------------------

    def run(self, user_input: str) -> str:
        """
        Execute the ReAct loop for a given user query.
        Returns the Final Answer string from the LLM.
        """
        logger.log_event("AGENT_START", {
            "input": user_input,
            "model": self.llm.model_name,
            "max_steps": self.max_steps,
        })

        # The running transcript that grows with each Observation
        transcript = f"User: {user_input}\n"
        steps = 0
        final_answer = None

        while steps < self.max_steps:
            steps += 1
            logger.log_event("AGENT_STEP_START", {"step": steps, "transcript_length": len(transcript)})

            try:
                result = self.llm.generate(transcript, system_prompt=self.get_system_prompt())
            except Exception as e:
                logger.error(f"LLM generation failed at step {steps}: {e}")
                break

            llm_output = result.get("content", "")
            usage = result.get("usage", {})
            latency_ms = result.get("latency_ms", 0)
            provider = result.get("provider", "unknown")

            tracker.track_request(
                provider=provider,
                model=self.llm.model_name,
                usage=usage,
                latency_ms=latency_ms,
            )

            logger.log_event("AGENT_LLM_OUTPUT", {
                "step": steps,
                "output": llm_output,
                "latency_ms": latency_ms,
                "tokens": usage.get("total_tokens", 0),
            })

            # ---- Parse Final Answer ----
            final_match = re.search(r"Final Answer\s*:\s*(.+)", llm_output, re.DOTALL | re.IGNORECASE)
            if final_match:
                final_answer = final_match.group(1).strip()
                logger.log_event("AGENT_FINAL_ANSWER", {"step": steps, "answer": final_answer})
                break

            # ---- Parse Action ----
            action_match = re.search(r"Action\s*:\s*(\w+)\s*\(([^)]*)\)", llm_output, re.IGNORECASE)
            if action_match:
                tool_name = action_match.group(1).strip()
                tool_args = action_match.group(2).strip()

                logger.log_event("AGENT_ACTION", {
                    "step": steps,
                    "tool": tool_name,
                    "args": tool_args,
                })

                observation = self._execute_tool(tool_name, tool_args)

                logger.log_event("AGENT_OBSERVATION", {
                    "step": steps,
                    "tool": tool_name,
                    "observation": observation,
                })

                # Append the LLM output + the Observation to the transcript
                transcript += llm_output.rstrip() + f"\nObservation: {observation}\n"
            else:
                # LLM did not produce a parseable Action or Final Answer
                logger.log_event("AGENT_PARSE_ERROR", {
                    "step": steps,
                    "raw_output": llm_output,
                    "error": "No Action or Final Answer found in LLM output.",
                })
                # Append the output anyway and hint the LLM to continue
                transcript += llm_output.rstrip() + "\n"
                transcript += (
                    "Observation: [System] Could not parse an Action. "
                    "Please continue with the correct format.\n"
                )

        logger.log_event("AGENT_END", {
            "steps_used": steps,
            "success": final_answer is not None,
        })

        if final_answer:
            return final_answer
        return (
            "I reached the maximum number of reasoning steps without finding a final answer. "
            "Please try rephrasing your question."
        )

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Look up a tool by name (case-insensitive) and call its function.
        Returns the tool's string result or an error message.
        """
        normalized = tool_name.lower().strip()
        for tool in self.tools:
            if tool["name"].lower() == normalized:
                try:
                    return str(tool["func"](args))
                except Exception as e:
                    error_msg = f"Tool '{tool_name}' raised an error: {e}"
                    logger.error(error_msg, exc_info=False)
                    return error_msg
        available = [t["name"] for t in self.tools]
        return f"Tool '{tool_name}' not found. Available tools: {available}."
