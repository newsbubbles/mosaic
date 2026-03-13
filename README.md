# Mosaic MCP Server & Agent

A comprehensive Python client and MCP server for the [Mosaic](https://mosaic.so) video editing automation API.

## Features

- **Video Workflow Automation**: Create, configure, and run AI-powered video editing workflows
- **Asset Management**: Upload videos, audio, and images with automatic 3-step flow handling
- **YouTube Automation**: Set up triggers to automatically process new videos from channels
- **Social Publishing**: Connect and publish to X, LinkedIn, Instagram, Facebook, TikTok, YouTube
- **Account Management**: Check credits, view plans, and manage subscriptions

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file:

```env
# Required
MOSAIC_API_KEY=mk_your_api_key_here

# For the test agent
OPENROUTER_API_KEY=your_openrouter_key

# Optional observability
LOGFIRE_API_KEY=your_logfire_key
```

Get your Mosaic API key from the [Mosaic Dashboard](https://edit.mosaic.so).

## Usage

### Testing with the Agent

The easiest way to test the MCP server is through the included agent:

```bash
python agent.py
```

This starts an interactive chat session where you can:

```
> List my agents
> Run agent abc123 on https://youtube.com/watch?v=dQw4w9WgXcQ
> Check my credit balance
> Upload video from ./my_video.mp4
```

### Using a Different Model

```bash
python agent.py --model anthropic/claude-3.5-sonnet
python agent.py --model openai/gpt-4o
```

### Using the Client Directly

```python
import asyncio
from client import (
    MosaicClient,
    ListAgentsRequest,
    RunAgentRequest,
    UploadVideoRequest,
)

async def main():
    async with MosaicClient() as client:
        # List agents
        agents = await client.list_agents(ListAgentsRequest())
        print(f"Found {len(agents.agents)} agents")
        
        # Run an agent on a YouTube video
        run = await client.run_agent(RunAgentRequest(
            agent_id="your-agent-id",
            video_urls=["https://youtube.com/watch?v=..."]
        ))
        print(f"Run started: {run.run_id}")
        
        # Upload a video (handles 3-step flow automatically)
        result = await client.upload_video(UploadVideoRequest(
            file_path="./my_video.mp4"
        ))
        print(f"Uploaded: {result.asset_id}")

asyncio.run(main())
```

## Project Structure

```
mosaic/
├── client.py           # Async API client with all endpoints
├── mcp_server.py       # FastMCP server exposing tools
├── agent.py            # PydanticAI test agent
├── agents/
│   └── mosaic.md       # Agent system prompt
├── .well-known/
│   └── agent.json      # A2A agent card
├── requirements.txt
└── README.md
```

## Available Tools (38 total)

### Agents
- `mosaic_create_agent` - Create a new video workflow
- `mosaic_update_agent` - Update agent settings
- `mosaic_delete_agent` - Delete an agent
- `mosaic_list_agents` - List all agents
- `mosaic_get_agent` - Get agent details with nodes

### Agent Runs
- `mosaic_run_agent` - Execute an agent on videos
- `mosaic_get_agent_run` - Get run status and outputs
- `mosaic_cancel_agent_run` - Cancel an active run
- `mosaic_list_agent_runs` - List runs for an agent
- `mosaic_list_all_agent_runs` - List all runs
- `mosaic_list_trigger_runs` - List trigger-initiated runs

### Agent Nodes
- `mosaic_list_agent_nodes` - List available node types
- `mosaic_get_agent_node` - Get node type details

### Triggers
- `mosaic_list_agent_triggers` - List YouTube triggers
- `mosaic_add_youtube_channels` - Add channels to monitor
- `mosaic_remove_youtube_channels` - Remove channels

### Asset Management
- `mosaic_create_upload_url` - Get signed upload URL
- `mosaic_finalize_upload` - Finalize an upload
- `mosaic_get_asset_view_url` - Get viewing URL
- `mosaic_upload_video` - Upload video (convenience)
- `mosaic_upload_audio` - Upload audio (convenience)
- `mosaic_upload_image` - Upload image (convenience)

### Credits
- `mosaic_get_credits` - Get credit balance
- `mosaic_buy_credits` - Purchase credits

### Plan
- `mosaic_get_plan` - Get current plan
- `mosaic_list_plans` - List available plans
- `mosaic_upgrade_plan` - Upgrade plan

### Social
- `mosaic_connect_social_platform` - Get OAuth link
- `mosaic_get_social_platform_status` - Check connection
- `mosaic_remove_social_platform` - Disconnect platform
- `mosaic_create_social_post` - Publish/schedule post
- `mosaic_get_social_post` - Get post status
- `mosaic_get_tracked_social_post` - Get tracked post
- `mosaic_update_social_post` - Update scheduled post
- `mosaic_delete_social_post` - Delete post

## Asset Limits

| Type | Max Size | Formats |
|------|----------|----------|
| Video | 5 GB | MP4, MOV, AVI, WebM, MKV, M4V |
| Audio | 100 MB | MP3, WAV, M4A, FLAC, OGG, AAC |
| Image | 50 MB | PNG, JPEG, GIF, WebP, SVG |

## License

MIT
