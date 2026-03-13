"""Mosaic Agent - PydanticAI Agent with MCP for testing the Mosaic MCP Server."""

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.messages import (
    ModelMessage,
    SystemPromptPart,
    UserPromptPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.agent import AgentRunResult
import logfire

from dotenv import load_dotenv
import os
import argparse
import asyncio
import traceback
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

load_dotenv()

# Configure Logfire for observability
logfire_key = os.getenv("LOGFIRE_API_KEY")
if logfire_key:
    logfire.configure(token=logfire_key)
    logfire.instrument_openai()


def parse_args():
    """Parse command line arguments."""
    default_model = "x-ai/grok-4-fast"
    parser = argparse.ArgumentParser(description="Mosaic Agent")
    parser.add_argument(
        "--model",
        type=str,
        default=default_model,
        help=f"Model identifier to use with OpenRouter (default: {default_model})",
    )
    return parser.parse_args()


args = parse_args()

# Set up OpenRouter based model
API_KEY = os.getenv("OPENROUTER_API_KEY")
model = OpenAIModel(
    args.model,
    provider=OpenAIProvider(
        base_url="https://openrouter.ai/api/v1",
        api_key=API_KEY,
    ),
)

# MCP Environment variables for the Mosaic MCP Server
env = {
    "MOSAIC_API_KEY": os.getenv("MOSAIC_API_KEY"),
}

# Set up MCP Server for the Agent
mcp_servers = [
    MCPServerStdio("python", ["./mcp_server.py"], env=env),
]


def filtered_message_history(
    result: Optional[AgentRunResult],
    limit: Optional[int] = None,
    include_tool_messages: bool = True,
) -> Optional[List[ModelMessage]]:
    """
    Filter and limit the message history from an AgentRunResult.

    Args:
        result: The AgentRunResult object with message history
        limit: Optional int, if provided returns only system message + last N messages
        include_tool_messages: Whether to include tool messages in the history

    Returns:
        Filtered list of messages in the format expected by the agent
    """
    if result is None:
        return None

    # Get all messages
    messages: list[ModelMessage] = result.all_messages()

    # Extract system message (always the first one with role="system")
    system_message = next(
        (msg for msg in messages if type(msg.parts[0]) == SystemPromptPart), None
    )

    # Filter non-system messages
    non_system_messages = [
        msg for msg in messages if type(msg.parts[0]) != SystemPromptPart
    ]

    # Apply tool message filtering if requested
    if not include_tool_messages:
        non_system_messages = [
            msg
            for msg in non_system_messages
            if not any(
                isinstance(part, ToolCallPart) or isinstance(part, ToolReturnPart)
                for part in msg.parts
            )
        ]

    # Find the most recent UserPromptPart before applying limit
    latest_user_prompt_part = None
    latest_user_prompt_index = -1
    for i, msg in enumerate(non_system_messages):
        for part in msg.parts:
            if isinstance(part, UserPromptPart):
                latest_user_prompt_part = part
                latest_user_prompt_index = i

    # Apply limit if specified, but ensure paired tool calls and returns stay together
    if limit is not None and limit > 0:
        # Identify tool call IDs and their corresponding return parts
        tool_call_ids = {}
        tool_return_ids = set()

        for i, msg in enumerate(non_system_messages):
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    tool_call_ids[part.tool_call_id] = i
                elif isinstance(part, ToolReturnPart):
                    tool_return_ids.add(part.tool_call_id)

        # Take the last 'limit' messages but ensure we include paired messages
        if len(non_system_messages) > limit:
            included_indices = set(
                range(len(non_system_messages) - limit, len(non_system_messages))
            )

            # Include any missing tool call messages for tool returns that are included
            for i, msg in enumerate(non_system_messages):
                if i in included_indices:
                    for part in msg.parts:
                        if (
                            isinstance(part, ToolReturnPart)
                            and part.tool_call_id in tool_call_ids
                        ):
                            included_indices.add(tool_call_ids[part.tool_call_id])

            # Check if the latest UserPromptPart would be excluded by the limit
            if (
                latest_user_prompt_index >= 0
                and latest_user_prompt_index not in included_indices
                and latest_user_prompt_part is not None
                and system_message is not None
            ):
                # Find if system_message already has a UserPromptPart
                user_prompt_index = next(
                    (
                        i
                        for i, part in enumerate(system_message.parts)
                        if isinstance(part, UserPromptPart)
                    ),
                    None,
                )

                if user_prompt_index is not None:
                    # Replace existing UserPromptPart
                    system_message.parts[user_prompt_index] = latest_user_prompt_part
                else:
                    # Add new UserPromptPart to system message
                    system_message.parts.append(latest_user_prompt_part)

            # Create a new list with only the included messages
            non_system_messages = [
                msg for i, msg in enumerate(non_system_messages) if i in included_indices
            ]

    # Combine system message with other messages
    result_messages = []
    if system_message:
        result_messages.append(system_message)
    result_messages.extend(non_system_messages)

    return result_messages


# Set up Agent with Server
agent_name = "mosaic"


def load_agent_prompt(agent: str) -> str:
    """Loads given agent replacing `time_now` var with current time."""
    print(f"Loading {agent}")
    time_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    agent_path = os.path.join(
        os.path.dirname(__file__), "agents", f"{agent}.md"
    )
    with open(agent_path, "r") as f:
        agent_prompt = f.read()
    agent_prompt = agent_prompt.replace("{time_now}", time_now)
    return agent_prompt


# Load up the agent system prompt
agent_prompt = load_agent_prompt(agent_name)

# Display the selected model
print(f"Using model: {args.model}")

agent = Agent(model, mcp_servers=mcp_servers, system_prompt=agent_prompt)


async def main():
    """CLI testing in a conversation with the agent."""
    async with agent.run_mcp_servers():
        result: AgentRunResult = None

        # Chat Loop
        while True:
            if result:
                print(f"\n{result.output}")
            user_input = input("\n> ")
            err = None
            for i in range(0, 2):
                try:
                    # Use the filtered message history
                    result = await agent.run(
                        user_input,
                        message_history=filtered_message_history(
                            result,
                            limit=24,  # Last 24 non-system messages
                            include_tool_messages=True,  # Include tool messages
                        ),
                    )
                    break
                except Exception as e:
                    err = e
                    traceback.print_exc()
                    await asyncio.sleep(2)
            if result is None:
                print(f"\nError {err}. Try again...\n")
                continue
            elif len(result.output) == 0:
                continue


if __name__ == "__main__":
    asyncio.run(main())
