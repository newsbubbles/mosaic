"""
Mosaic MCP Server

FastMCP server exposing Mosaic video editing automation API.
Provides tools for managing agents, runs, assets, social posting, and more.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Any, Optional, Literal

from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP, Context

from client import (
    MosaicClient,
    # Enums
    Visibility,
    AssetType,
    SocialPlatform,
    PlanId,
    # Agent requests
    CreateAgentRequest,
    UpdateAgentRequest,
    DeleteAgentRequest,
    ListAgentsRequest,
    GetAgentRequest,
    GraphNode,
    GraphConnection,
    AgentGraph,
    # Run requests
    RunAgentRequest,
    GetAgentRunRequest,
    CancelAgentRunRequest,
    ListAgentRunsRequest,
    ListAllAgentRunsRequest,
    ListTriggerRunsRequest,
    VideoInput,
    # Node requests
    ListAgentNodesRequest,
    GetAgentNodeRequest,
    # Trigger requests
    ListAgentTriggersRequest,
    AddYouTubeChannelsRequest,
    RemoveYouTubeChannelsRequest,
    # Asset requests
    CreateUploadUrlRequest,
    FinalizeUploadRequest,
    GetAssetViewUrlRequest,
    UploadVideoRequest,
    UploadAudioRequest,
    UploadImageRequest,
    # Credits requests
    GetCreditsRequest,
    BuyCreditsRequest,
    # Plan requests
    GetPlanRequest,
    ListPlansRequest,
    UpgradePlanRequest,
    # Social requests
    ConnectSocialPlatformRequest,
    GetSocialPlatformStatusRequest,
    RemoveSocialPlatformRequest,
    CreateSocialPostRequest,
    GetSocialPostRequest,
    GetTrackedSocialPostRequest,
    UpdateSocialPostRequest,
    DeleteSocialPostRequest,
)


# =============================================================================
# Logging Setup
# =============================================================================

def setup_mcp_logging():
    """Standard logging setup for MCP servers."""
    logger_name = os.getenv("LOGGER_NAME", "mosaic_mcp")
    logger_path = os.getenv("LOGGER_PATH")
    
    logger = logging.getLogger(logger_name)
    
    if logger_path and not logger.handlers:
        handler = logging.FileHandler(logger_path, mode='a')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


logger = setup_mcp_logging()


# =============================================================================
# MCP Context
# =============================================================================

class MCPContext:
    """Context holding initialized Mosaic client."""
    def __init__(self, client: MosaicClient):
        self.client = client


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[MCPContext]:
    """Manage Mosaic client lifecycle."""
    logger.info("Initializing Mosaic MCP Server")
    client = None
    try:
        api_key = os.getenv("MOSAIC_API_KEY")
        if not api_key:
            raise ValueError("MOSAIC_API_KEY environment variable is required")
        
        client = MosaicClient(api_key=api_key)
        logger.info("Mosaic client initialized")
        yield MCPContext(client=client)
    except Exception as e:
        logger.error(f"Failed to initialize Mosaic client: {e}")
        raise ValueError(f"Failed to initialize Mosaic client: {str(e)}")
    finally:
        if client:
            await client.close()
            logger.info("Mosaic client closed")


mcp = FastMCP("Mosaic", lifespan=lifespan)


# =============================================================================
# Request Models - Agents
# =============================================================================

class MosaicCreateAgentRequest(BaseModel):
    """Request to create a new Mosaic agent."""
    name: Optional[str] = Field(None, max_length=120, description="Agent name (1-120 chars)")
    description: Optional[str] = Field(None, max_length=5000, description="Agent description")
    visibility: Optional[Literal["public", "private"]] = Field(None, description="Visibility setting")
    workspace_id: Optional[str] = Field(None, description="Target workspace UUID")
    create_video_input_node: Optional[bool] = Field(True, description="Auto-create starter Video Input node")


class MosaicUpdateAgentRequest(BaseModel):
    """Request to update an existing agent."""
    agent_id: str = Field(..., description="Agent ID to update")
    name: Optional[str] = Field(None, max_length=120, description="New agent name")
    description: Optional[str] = Field(None, max_length=5000, description="New agent description")
    visibility: Optional[Literal["public", "private"]] = Field(None, description="New visibility setting")


class MosaicDeleteAgentRequest(BaseModel):
    """Request to delete an agent."""
    agent_id: str = Field(..., description="Agent ID to delete")


class MosaicListAgentsRequest(BaseModel):
    """Request to list agents."""
    limit: Optional[int] = Field(25, ge=1, le=100, description="Page size (1-100)")
    cursor: Optional[str] = Field(None, description="Pagination cursor")


class MosaicGetAgentRequest(BaseModel):
    """Request to get agent details."""
    agent_id: str = Field(..., description="Agent ID to retrieve")


# =============================================================================
# Request Models - Agent Runs
# =============================================================================

class MosaicRunAgentRequest(BaseModel):
    """Request to run an agent on videos."""
    agent_id: str = Field(..., description="Agent ID to run")
    video_urls: Optional[list[str]] = Field(None, description="Video URLs to process (YouTube or signed URLs)")
    node_render_ids: Optional[list[str]] = Field(None, description="Render IDs from prior runs to chain as input")
    update_params: Optional[dict[str, Any]] = Field(None, description="Override node parameters")
    ignore_nodes: Optional[list[str]] = Field(None, description="Agent node IDs to bypass")


class MosaicGetAgentRunRequest(BaseModel):
    """Request to get run status."""
    run_id: str = Field(..., description="Run ID to retrieve")


class MosaicCancelAgentRunRequest(BaseModel):
    """Request to cancel a run."""
    run_id: str = Field(..., description="Run ID to cancel")


class MosaicListAgentRunsRequest(BaseModel):
    """Request to list runs for an agent."""
    agent_id: str = Field(..., description="Agent ID")
    limit: Optional[int] = Field(25, ge=1, le=100, description="Page size")
    cursor: Optional[str] = Field(None, description="Pagination cursor")
    status: Optional[str] = Field(None, description="Filter by status (comma-separated: running,completed,failed)")
    from_date: Optional[str] = Field(None, description="ISO timestamp lower bound")
    to_date: Optional[str] = Field(None, description="ISO timestamp upper bound")


class MosaicListAllAgentRunsRequest(BaseModel):
    """Request to list all runs across agents."""
    limit: Optional[int] = Field(25, ge=1, le=100, description="Page size")
    cursor: Optional[str] = Field(None, description="Pagination cursor")
    status: Optional[str] = Field(None, description="Filter by status")
    from_date: Optional[str] = Field(None, description="ISO timestamp lower bound")
    to_date: Optional[str] = Field(None, description="ISO timestamp upper bound")
    agent_id: Optional[str] = Field(None, description="Filter to one agent")


class MosaicListTriggerRunsRequest(BaseModel):
    """Request to list runs from a trigger."""
    trigger_id: str = Field(..., description="Trigger ID")
    limit: Optional[int] = Field(25, ge=1, le=100, description="Page size")
    cursor: Optional[str] = Field(None, description="Pagination cursor")
    status: Optional[str] = Field(None, description="Filter by status")
    from_date: Optional[str] = Field(None, description="ISO timestamp lower bound")
    to_date: Optional[str] = Field(None, description="ISO timestamp upper bound")


# =============================================================================
# Request Models - Agent Nodes
# =============================================================================

class MosaicListAgentNodesRequest(BaseModel):
    """Request to list available node types."""
    pass


class MosaicGetAgentNodeRequest(BaseModel):
    """Request to get node type details."""
    node_id: str = Field(..., description="Node type ID or agent node instance ID")


# =============================================================================
# Request Models - Triggers
# =============================================================================

class MosaicListAgentTriggersRequest(BaseModel):
    """Request to list triggers for an agent."""
    agent_id: str = Field(..., description="Agent ID")


class MosaicAddYouTubeChannelsRequest(BaseModel):
    """Request to add YouTube channels to monitor."""
    agent_id: str = Field(..., description="Agent ID")
    youtube_channels: list[str] = Field(..., description="YouTube channel IDs or URLs")
    trigger_callback_url: Optional[str] = Field(None, description="Webhook URL for trigger events")


class MosaicRemoveYouTubeChannelsRequest(BaseModel):
    """Request to remove YouTube channels."""
    agent_id: str = Field(..., description="Agent ID")
    youtube_channels: list[str] = Field(..., description="YouTube channel IDs or URLs to remove")


# =============================================================================
# Request Models - Asset Management
# =============================================================================

class MosaicCreateUploadUrlRequest(BaseModel):
    """Request to create a signed upload URL."""
    asset_type: Literal["video", "audio", "image"] = Field(..., description="Asset type")


class MosaicFinalizeUploadRequest(BaseModel):
    """Request to finalize an upload."""
    asset_type: Literal["video", "audio", "image"] = Field(..., description="Asset type")
    asset_id: str = Field(..., description="Asset ID from create upload URL")


class MosaicGetAssetViewUrlRequest(BaseModel):
    """Request to get a viewing URL for an asset."""
    asset_type: Literal["video", "audio", "image"] = Field(..., description="Asset type")
    asset_id: str = Field(..., description="Asset ID")


class MosaicUploadVideoRequest(BaseModel):
    """Request to upload a video file."""
    file_path: str = Field(..., description="Local path to the video file")


class MosaicUploadAudioRequest(BaseModel):
    """Request to upload an audio file."""
    file_path: str = Field(..., description="Local path to the audio file")


class MosaicUploadImageRequest(BaseModel):
    """Request to upload an image file."""
    file_path: str = Field(..., description="Local path to the image file")


# =============================================================================
# Request Models - Credits
# =============================================================================

class MosaicGetCreditsRequest(BaseModel):
    """Request to get credit balance."""
    pass


class MosaicBuyCreditsRequest(BaseModel):
    """Request to buy credits."""
    credits: int = Field(..., ge=100, le=1000000, description="Number of credits (100-1,000,000)")
    success_url: Optional[str] = Field(None, description="Checkout success redirect URL")
    cancel_url: Optional[str] = Field(None, description="Checkout cancel redirect URL")


# =============================================================================
# Request Models - Plan
# =============================================================================

class MosaicGetPlanRequest(BaseModel):
    """Request to get current plan."""
    pass


class MosaicListPlansRequest(BaseModel):
    """Request to list available plans."""
    pass


class MosaicUpgradePlanRequest(BaseModel):
    """Request to upgrade plan."""
    plan_id: Literal["creator", "creator_annual", "professional", "professional_annual", "pro"] = Field(
        ..., description="Target plan ID"
    )
    success_url: Optional[str] = Field(None, description="Checkout success redirect URL")
    cancel_url: Optional[str] = Field(None, description="Checkout cancel redirect URL")


# =============================================================================
# Request Models - Social
# =============================================================================

class MosaicConnectSocialPlatformRequest(BaseModel):
    """Request to connect a social platform."""
    platform: Literal["x", "linkedin", "instagram", "facebook", "tiktok", "youtube"] = Field(
        ..., description="Social platform"
    )


class MosaicGetSocialPlatformStatusRequest(BaseModel):
    """Request to get social platform status."""
    platform: Literal["x", "linkedin", "instagram", "facebook", "tiktok", "youtube"] = Field(
        ..., description="Social platform"
    )


class MosaicRemoveSocialPlatformRequest(BaseModel):
    """Request to disconnect a social platform."""
    platform: Literal["x", "linkedin", "instagram", "facebook", "tiktok", "youtube"] = Field(
        ..., description="Social platform"
    )


class MosaicCreateSocialPostRequest(BaseModel):
    """Request to create a social post."""
    platforms: list[Literal["x", "linkedin", "instagram", "facebook", "tiktok", "youtube"]] = Field(
        ..., description="Target platforms"
    )
    post: Optional[str] = Field("", description="Post text")
    media_urls: Optional[list[str]] = Field(None, description="Public media URLs to attach")
    schedule_date: Optional[str] = Field(None, description="ISO timestamp to schedule post")
    workspace_id: Optional[str] = Field(None, description="Workspace ID")


class MosaicGetSocialPostRequest(BaseModel):
    """Request to get a social post."""
    post_id: str = Field(..., description="Provider post ID")


class MosaicGetTrackedSocialPostRequest(BaseModel):
    """Request to get a tracked social post."""
    tracking_id: str = Field(..., description="Tracking ID")


class MosaicUpdateSocialPostRequest(BaseModel):
    """Request to update a social post."""
    post_id: str = Field(..., description="Post ID to update")
    schedule_date: Optional[str] = Field(None, description="New scheduled timestamp")
    scheduled_pause: Optional[bool] = Field(None, description="Pause or resume scheduling")
    notes: Optional[str] = Field(None, description="Scheduling notes")
    approve: Optional[bool] = Field(None, description="Approve pending post")


class MosaicDeleteSocialPostRequest(BaseModel):
    """Request to delete a social post."""
    post_id: str = Field(..., description="Post ID to delete")
    mark_manual_deleted: Optional[bool] = Field(None, description="Mark as manually deleted")


# =============================================================================
# Tools - Agents
# =============================================================================

@mcp.tool()
async def mosaic_create_agent(request: MosaicCreateAgentRequest, ctx: Context) -> dict[str, Any]:
    """Create a new Mosaic video editing agent.
    
    Agents are visual workflows that process videos with AI-powered features
    like captions, music, audio enhancement, and more.
    """
    logger.info(f"Creating agent: {request.name}")
    try:
        client = ctx.request_context.lifespan_context.client
        
        visibility = Visibility(request.visibility) if request.visibility else None
        
        result = await client.create_agent(CreateAgentRequest(
            name=request.name,
            description=request.description,
            visibility=visibility,
            workspace_id=request.workspace_id,
            create_video_input_node=request.create_video_input_node
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_update_agent(request: MosaicUpdateAgentRequest, ctx: Context) -> dict[str, Any]:
    """Update an existing agent's name, description, or visibility."""
    logger.info(f"Updating agent: {request.agent_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        
        visibility = Visibility(request.visibility) if request.visibility else None
        
        result = await client.update_agent(UpdateAgentRequest(
            agent_id=request.agent_id,
            name=request.name,
            description=request.description,
            visibility=visibility
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to update agent: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_delete_agent(request: MosaicDeleteAgentRequest, ctx: Context) -> dict[str, Any]:
    """Delete an agent (soft delete)."""
    logger.info(f"Deleting agent: {request.agent_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.delete_agent(DeleteAgentRequest(agent_id=request.agent_id))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to delete agent: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_list_agents(request: MosaicListAgentsRequest, ctx: Context) -> dict[str, Any]:
    """List all agents available to the organization.
    
    Returns paginated list with agent summaries including ID, name, description.
    Use the next_cursor for pagination.
    """
    logger.info(f"Listing agents (limit={request.limit})")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.list_agents(ListAgentsRequest(
            limit=request.limit,
            cursor=request.cursor
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_get_agent(request: MosaicGetAgentRequest, ctx: Context) -> dict[str, Any]:
    """Get detailed agent information including nodes and connections.
    
    Returns the agent's graph structure with all configured nodes and their parameters.
    """
    logger.info(f"Getting agent: {request.agent_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.get_agent(GetAgentRequest(agent_id=request.agent_id))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to get agent: {e}")
        return {"error": str(e)}


# =============================================================================
# Tools - Agent Runs
# =============================================================================

@mcp.tool()
async def mosaic_run_agent(request: MosaicRunAgentRequest, ctx: Context) -> dict[str, Any]:
    """Execute an agent on videos.
    
    Supports YouTube URLs and signed URLs. Use update_params to override
    node parameters for this run.
    """
    logger.info(f"Running agent: {request.agent_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.run_agent(RunAgentRequest(
            agent_id=request.agent_id,
            video_urls=request.video_urls,
            node_render_ids=request.node_render_ids,
            update_params=request.update_params,
            ignore_nodes=request.ignore_nodes
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to run agent: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_get_agent_run(request: MosaicGetAgentRunRequest, ctx: Context) -> dict[str, Any]:
    """Get run status and outputs.
    
    Poll this endpoint to track run progress. When completed, outputs
    contain signed URLs to download rendered videos.
    """
    logger.info(f"Getting run: {request.run_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.get_agent_run(GetAgentRunRequest(run_id=request.run_id))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to get run: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_cancel_agent_run(request: MosaicCancelAgentRunRequest, ctx: Context) -> dict[str, Any]:
    """Cancel an active run."""
    logger.info(f"Cancelling run: {request.run_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.cancel_agent_run(CancelAgentRunRequest(run_id=request.run_id))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to cancel run: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_list_agent_runs(request: MosaicListAgentRunsRequest, ctx: Context) -> dict[str, Any]:
    """List runs for a specific agent.
    
    Filter by status and date range. Use next_cursor for pagination.
    """
    logger.info(f"Listing runs for agent: {request.agent_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.list_agent_runs(ListAgentRunsRequest(
            agent_id=request.agent_id,
            limit=request.limit,
            cursor=request.cursor,
            status=request.status,
            from_date=request.from_date,
            to_date=request.to_date
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to list runs: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_list_all_agent_runs(request: MosaicListAllAgentRunsRequest, ctx: Context) -> dict[str, Any]:
    """List all runs across all agents in the organization."""
    logger.info("Listing all runs")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.list_all_agent_runs(ListAllAgentRunsRequest(
            limit=request.limit,
            cursor=request.cursor,
            status=request.status,
            from_date=request.from_date,
            to_date=request.to_date,
            agent_id=request.agent_id
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to list all runs: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_list_trigger_runs(request: MosaicListTriggerRunsRequest, ctx: Context) -> dict[str, Any]:
    """List runs initiated by a specific trigger."""
    logger.info(f"Listing runs for trigger: {request.trigger_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.list_trigger_runs(ListTriggerRunsRequest(
            trigger_id=request.trigger_id,
            limit=request.limit,
            cursor=request.cursor,
            status=request.status,
            from_date=request.from_date,
            to_date=request.to_date
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to list trigger runs: {e}")
        return {"error": str(e)}


# =============================================================================
# Tools - Agent Nodes
# =============================================================================

@mcp.tool()
async def mosaic_list_agent_nodes(request: MosaicListAgentNodesRequest, ctx: Context) -> dict[str, Any]:
    """List all available node types.
    
    Returns node types like Video Input, Captions, AI Music, etc.
    with documentation links.
    """
    logger.info("Listing agent nodes")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.list_agent_nodes(ListAgentNodesRequest())
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to list nodes: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_get_agent_node(request: MosaicGetAgentNodeRequest, ctx: Context) -> dict[str, Any]:
    """Get details for a specific node type."""
    logger.info(f"Getting node: {request.node_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.get_agent_node(GetAgentNodeRequest(node_id=request.node_id))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to get node: {e}")
        return {"error": str(e)}


# =============================================================================
# Tools - Triggers
# =============================================================================

@mcp.tool()
async def mosaic_list_agent_triggers(request: MosaicListAgentTriggersRequest, ctx: Context) -> dict[str, Any]:
    """List YouTube triggers configured for an agent.
    
    Returns monitored channels and their details.
    """
    logger.info(f"Listing triggers for agent: {request.agent_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.list_agent_triggers(ListAgentTriggersRequest(agent_id=request.agent_id))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to list triggers: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_add_youtube_channels(request: MosaicAddYouTubeChannelsRequest, ctx: Context) -> dict[str, Any]:
    """Add YouTube channels to monitor for automatic agent runs.
    
    Accepts channel IDs or URLs. When a new video is published on
    a monitored channel, the agent runs automatically.
    """
    logger.info(f"Adding YouTube channels to agent: {request.agent_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.add_youtube_channels(AddYouTubeChannelsRequest(
            agent_id=request.agent_id,
            youtube_channels=request.youtube_channels,
            trigger_callback_url=request.trigger_callback_url
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to add channels: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_remove_youtube_channels(request: MosaicRemoveYouTubeChannelsRequest, ctx: Context) -> dict[str, Any]:
    """Remove YouTube channels from monitoring."""
    logger.info(f"Removing YouTube channels from agent: {request.agent_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.remove_youtube_channels(RemoveYouTubeChannelsRequest(
            agent_id=request.agent_id,
            youtube_channels=request.youtube_channels
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to remove channels: {e}")
        return {"error": str(e)}


# =============================================================================
# Tools - Asset Management
# =============================================================================

@mcp.tool()
async def mosaic_create_upload_url(request: MosaicCreateUploadUrlRequest, ctx: Context) -> dict[str, Any]:
    """Create a signed upload URL for an asset.
    
    Step 1 of the upload flow. Returns upload_url, upload_fields, and asset_id.
    Upload the file to upload_url with upload_fields, then call finalize_upload.
    """
    logger.info(f"Creating upload URL for: {request.asset_type}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.create_upload_url(CreateUploadUrlRequest(
            asset_type=AssetType(request.asset_type)
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to create upload URL: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_finalize_upload(request: MosaicFinalizeUploadRequest, ctx: Context) -> dict[str, Any]:
    """Finalize an asset upload.
    
    Step 3 of the upload flow. Call after uploading the file to the signed URL.
    """
    logger.info(f"Finalizing upload: {request.asset_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.finalize_upload(FinalizeUploadRequest(
            asset_type=AssetType(request.asset_type),
            asset_id=request.asset_id
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to finalize upload: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_get_asset_view_url(request: MosaicGetAssetViewUrlRequest, ctx: Context) -> dict[str, Any]:
    """Get a signed viewing URL for an uploaded asset."""
    logger.info(f"Getting view URL for: {request.asset_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.get_asset_view_url(GetAssetViewUrlRequest(
            asset_type=AssetType(request.asset_type),
            asset_id=request.asset_id
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to get view URL: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_upload_video(request: MosaicUploadVideoRequest, ctx: Context) -> dict[str, Any]:
    """Upload a video file (convenience method).
    
    Handles the complete 3-step upload flow automatically.
    Returns the video_id to use in agent runs.
    Max size: 5GB.
    """
    logger.info(f"Uploading video: {request.file_path}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.upload_video(UploadVideoRequest(file_path=request.file_path))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to upload video: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_upload_audio(request: MosaicUploadAudioRequest, ctx: Context) -> dict[str, Any]:
    """Upload an audio file (convenience method).
    
    Handles the complete 3-step upload flow automatically.
    Returns the audio_id to use in agent runs.
    Max size: 100MB.
    """
    logger.info(f"Uploading audio: {request.file_path}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.upload_audio(UploadAudioRequest(file_path=request.file_path))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to upload audio: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_upload_image(request: MosaicUploadImageRequest, ctx: Context) -> dict[str, Any]:
    """Upload an image file (convenience method).
    
    Handles the complete 3-step upload flow automatically.
    Returns the image_id to use in agent runs.
    Max size: 50MB.
    """
    logger.info(f"Uploading image: {request.file_path}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.upload_image(UploadImageRequest(file_path=request.file_path))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to upload image: {e}")
        return {"error": str(e)}


# =============================================================================
# Tools - Credits
# =============================================================================

@mcp.tool()
async def mosaic_get_credits(request: MosaicGetCreditsRequest, ctx: Context) -> dict[str, Any]:
    """Get organization credit balance and usage."""
    logger.info("Getting credits")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.get_credits(GetCreditsRequest())
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to get credits: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_buy_credits(request: MosaicBuyCreditsRequest, ctx: Context) -> dict[str, Any]:
    """Purchase top-up credits.
    
    May return a checkout_url if payment requires redirect.
    """
    logger.info(f"Buying credits: {request.credits}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.buy_credits(BuyCreditsRequest(
            credits=request.credits,
            success_url=request.success_url,
            cancel_url=request.cancel_url
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to buy credits: {e}")
        return {"error": str(e)}


# =============================================================================
# Tools - Plan
# =============================================================================

@mcp.tool()
async def mosaic_get_plan(request: MosaicGetPlanRequest, ctx: Context) -> dict[str, Any]:
    """Get current plan details including billing period and credits."""
    logger.info("Getting plan")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.get_plan(GetPlanRequest())
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to get plan: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_list_plans(request: MosaicListPlansRequest, ctx: Context) -> dict[str, Any]:
    """List available plans with pricing and included credits."""
    logger.info("Listing plans")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.list_plans(ListPlansRequest())
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to list plans: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_upgrade_plan(request: MosaicUpgradePlanRequest, ctx: Context) -> dict[str, Any]:
    """Upgrade or change the organization plan.
    
    May return a checkout_url if payment requires redirect.
    """
    logger.info(f"Upgrading to plan: {request.plan_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.upgrade_plan(UpgradePlanRequest(
            plan_id=PlanId(request.plan_id),
            success_url=request.success_url,
            cancel_url=request.cancel_url
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to upgrade plan: {e}")
        return {"error": str(e)}


# =============================================================================
# Tools - Social
# =============================================================================

@mcp.tool()
async def mosaic_connect_social_platform(request: MosaicConnectSocialPlatformRequest, ctx: Context) -> dict[str, Any]:
    """Generate a social linking URL for connecting a platform.
    
    Returns a connect_url to redirect the user for OAuth authorization.
    """
    logger.info(f"Connecting platform: {request.platform}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.connect_social_platform(ConnectSocialPlatformRequest(
            platform=SocialPlatform(request.platform)
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to connect platform: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_get_social_platform_status(request: MosaicGetSocialPlatformStatusRequest, ctx: Context) -> dict[str, Any]:
    """Check if a social platform is connected and get account details."""
    logger.info(f"Getting platform status: {request.platform}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.get_social_platform_status(GetSocialPlatformStatusRequest(
            platform=SocialPlatform(request.platform)
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to get platform status: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_remove_social_platform(request: MosaicRemoveSocialPlatformRequest, ctx: Context) -> dict[str, Any]:
    """Disconnect a social platform from the organization."""
    logger.info(f"Removing platform: {request.platform}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.remove_social_platform(RemoveSocialPlatformRequest(
            platform=SocialPlatform(request.platform)
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to remove platform: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_create_social_post(request: MosaicCreateSocialPostRequest, ctx: Context) -> dict[str, Any]:
    """Publish or schedule a social post to multiple platforms.
    
    Supports X, LinkedIn, Instagram, Facebook, TikTok, and YouTube.
    Use schedule_date for scheduled posts.
    """
    logger.info(f"Creating social post to: {request.platforms}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.create_social_post(CreateSocialPostRequest(
            platforms=[SocialPlatform(p) for p in request.platforms],
            post=request.post,
            media_urls=request.media_urls,
            schedule_date=request.schedule_date,
            workspace_id=request.workspace_id
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to create post: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_get_social_post(request: MosaicGetSocialPostRequest, ctx: Context) -> dict[str, Any]:
    """Get social post status and results from the provider."""
    logger.info(f"Getting post: {request.post_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.get_social_post(GetSocialPostRequest(post_id=request.post_id))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to get post: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_get_tracked_social_post(request: MosaicGetTrackedSocialPostRequest, ctx: Context) -> dict[str, Any]:
    """Get tracked social post record from Mosaic."""
    logger.info(f"Getting tracked post: {request.tracking_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.get_tracked_social_post(GetTrackedSocialPostRequest(
            tracking_id=request.tracking_id
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to get tracked post: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_update_social_post(request: MosaicUpdateSocialPostRequest, ctx: Context) -> dict[str, Any]:
    """Update a scheduled social post.
    
    Can reschedule, pause, or approve pending posts.
    """
    logger.info(f"Updating post: {request.post_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.update_social_post(UpdateSocialPostRequest(
            post_id=request.post_id,
            schedule_date=request.schedule_date,
            scheduled_pause=request.scheduled_pause,
            notes=request.notes,
            approve=request.approve
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to update post: {e}")
        return {"error": str(e)}


@mcp.tool()
async def mosaic_delete_social_post(request: MosaicDeleteSocialPostRequest, ctx: Context) -> dict[str, Any]:
    """Delete a social post."""
    logger.info(f"Deleting post: {request.post_id}")
    try:
        client = ctx.request_context.lifespan_context.client
        result = await client.delete_social_post(DeleteSocialPostRequest(
            post_id=request.post_id,
            mark_manual_deleted=request.mark_manual_deleted
        ))
        return result.model_dump()
    except Exception as e:
        logger.error(f"Failed to delete post: {e}")
        return {"error": str(e)}


# =============================================================================
# Main
# =============================================================================

def main():
    mcp.run()


if __name__ == "__main__":
    main()
