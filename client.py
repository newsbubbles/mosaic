"""
Mosaic API Client

A comprehensive async client for the Mosaic video editing automation API.
https://docs.mosaic.so/api/introduction
"""

import os
from typing import Optional, Literal, Union
from datetime import datetime
from enum import Enum

import httpx
from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class Visibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL_COMPLETE = "partial_complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssetType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"


class SocialPlatform(str, Enum):
    X = "x"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


class PlanId(str, Enum):
    CREATOR = "creator"
    CREATOR_ANNUAL = "creator_annual"
    PROFESSIONAL = "professional"
    PROFESSIONAL_ANNUAL = "professional_annual"
    PRO = "pro"


# =============================================================================
# Request Models - Agents
# =============================================================================

class GraphNode(BaseModel):
    """A node in the agent graph."""
    id: str = Field(..., description="Unique identifier for the node instance")
    node_id: str = Field(..., description="Type identifier for the node")
    position_x: float = Field(0, description="X coordinate position in the graph")
    position_y: float = Field(0, description="Y coordinate position in the graph")
    params_used: dict = Field(default_factory=dict, description="Parameters configured for the node")


class GraphConnection(BaseModel):
    """A connection between nodes in the agent graph."""
    source_agent_node_id: str = Field(..., description="ID of the source node")
    target_agent_node_id: str = Field(..., description="ID of the target node")


class AgentGraph(BaseModel):
    """Graph structure for an agent."""
    nodes: list[GraphNode] = Field(default_factory=list, description="Graph nodes")
    connections: list[GraphConnection] = Field(default_factory=list, description="Directed edges")


class CreateAgentRequest(BaseModel):
    """Request to create a new agent."""
    name: Optional[str] = Field(None, max_length=120, description="Agent name (1-120 chars)")
    description: Optional[str] = Field(None, max_length=5000, description="Agent description")
    visibility: Optional[Visibility] = Field(None, description="Public or private visibility")
    workspace_id: Optional[str] = Field(None, description="Target workspace UUID")
    create_video_input_node: Optional[bool] = Field(True, description="Auto-create starter Video Input node when graph is omitted")
    graph: Optional[AgentGraph] = Field(None, description="Graph nodes and connections")


class CreateNodeOperation(BaseModel):
    """Operation to create a node in the agent graph."""
    op: Literal["create_node"] = "create_node"
    node_type_id: str = Field(..., description="Node type UUID to instantiate")
    temp_ref_id: Optional[str] = Field(None, description="Request-scoped temporary reference for this node")
    params_used: Optional[dict] = Field(None, description="Initial node parameters")


class UpdateNodeOperation(BaseModel):
    """Operation to update an existing node's parameters."""
    op: Literal["update_node"] = "update_node"
    agent_node_id: str = Field(..., description="Existing persisted node ID to update")
    params_used: dict = Field(..., description="Parameter patch object merged into current node params")


class DeleteNodeOperation(BaseModel):
    """Operation to delete a node from the agent graph."""
    op: Literal["delete_node"] = "delete_node"
    agent_node_id: str = Field(..., description="Existing persisted node ID to delete")


class CreateConnectionOperation(BaseModel):
    """Operation to create a connection between nodes."""
    op: Literal["create_connection"] = "create_connection"
    source_agent_node_id: Optional[str] = Field(None, description="Source existing node ID")
    source_temp_ref_id: Optional[str] = Field(None, description="Source temp ref from earlier operation")
    target_agent_node_id: Optional[str] = Field(None, description="Target existing node ID")
    target_temp_ref_id: Optional[str] = Field(None, description="Target temp ref from earlier operation")


class DeleteConnectionOperation(BaseModel):
    """Operation to delete a connection between nodes."""
    op: Literal["delete_connection"] = "delete_connection"
    source_agent_node_id: Optional[str] = Field(None, description="Source existing node ID")
    source_temp_ref_id: Optional[str] = Field(None, description="Source temp ref from earlier operation")
    target_agent_node_id: Optional[str] = Field(None, description="Target existing node ID")
    target_temp_ref_id: Optional[str] = Field(None, description="Target temp ref from earlier operation")


# Union type for graph operations
GraphOperation = CreateNodeOperation | UpdateNodeOperation | DeleteNodeOperation | CreateConnectionOperation | DeleteConnectionOperation


class UpdateAgentRequest(BaseModel):
    """Request to update an existing agent."""
    agent_id: str = Field(..., description="Agent ID to update")
    name: Optional[str] = Field(None, max_length=120, description="Agent name")
    description: Optional[str] = Field(None, max_length=5000, description="Agent description")
    visibility: Optional[Visibility] = Field(None, description="Public or private visibility")
    operations: Optional[list[GraphOperation]] = Field(None, description="Ordered graph operations for node/connection mutations")


class DuplicateAgentRequest(BaseModel):
    """Request to duplicate an agent."""
    agent_id: str = Field(..., description="Agent ID to duplicate")
    name: Optional[str] = Field(None, max_length=120, description="Name for the duplicated agent")
    description: Optional[str] = Field(None, max_length=5000, description="Description override")
    visibility: Optional[Visibility] = Field(None, description="Visibility override")


class DeleteAgentRequest(BaseModel):
    """Request to delete an agent."""
    agent_id: str = Field(..., description="Agent ID to delete")


class ListAgentsRequest(BaseModel):
    """Request to list agents."""
    limit: Optional[int] = Field(25, ge=1, le=100, description="Page size (1-100)")
    cursor: Optional[str] = Field(None, description="Pagination cursor from next_cursor")


class GetAgentRequest(BaseModel):
    """Request to get an agent."""
    agent_id: str = Field(..., description="Agent ID to retrieve")


class WhoAmIRequest(BaseModel):
    """Request to validate API key and get organization info."""
    pass  # No parameters required


# =============================================================================
# Request Models - Agent Runs
# =============================================================================

class VideoInput(BaseModel):
    """Input mapping for multi-input workflows."""
    agent_node_id: str = Field(..., description="Agent node ID for the Video Input tile")
    video_ids: Optional[list[str]] = Field(None, description="Mosaic video asset IDs")
    video_urls: Optional[list[str]] = Field(None, description="Direct video URLs")
    signed_urls: Optional[list[str]] = Field(None, description="Signed video URLs")
    youtube_urls: Optional[list[str]] = Field(None, description="YouTube video URLs")
    node_render_ids: Optional[list[str]] = Field(None, description="Render IDs from prior runs")


class RunAgentRequest(BaseModel):
    """Request to run an agent."""
    agent_id: str = Field(..., description="Agent ID to run")
    video_urls: Optional[list[str]] = Field(None, description="Video URLs to process (YouTube or signed URLs)")
    video_inputs: Optional[list[VideoInput]] = Field(None, description="Explicit per-tile input mapping for multi-input agents")
    node_render_ids: Optional[list[str]] = Field(None, description="Render IDs from prior runs to chain as input")
    callback_url: Optional[str] = Field(None, description="Webhook URL for status updates")
    update_params: Optional[dict] = Field(None, description="Override node parameters")
    ignore_nodes: Optional[list[str]] = Field(None, description="Agent node IDs to bypass for this run")


class GetAgentRunRequest(BaseModel):
    """Request to get an agent run."""
    run_id: str = Field(..., description="Run ID to retrieve")


class CancelAgentRunRequest(BaseModel):
    """Request to cancel an agent run."""
    run_id: str = Field(..., description="Run ID to cancel")


class ListAgentRunsRequest(BaseModel):
    """Request to list runs for an agent."""
    agent_id: str = Field(..., description="Agent ID")
    limit: Optional[int] = Field(25, ge=1, le=100, description="Page size (1-100)")
    cursor: Optional[str] = Field(None, description="Pagination cursor")
    status: Optional[str] = Field(None, description="Comma-separated statuses (e.g., 'running,completed')")
    from_date: Optional[str] = Field(None, description="ISO timestamp lower bound on created_at")
    to_date: Optional[str] = Field(None, description="ISO timestamp upper bound on created_at")


class ListAllAgentRunsRequest(BaseModel):
    """Request to list all runs across agents."""
    limit: Optional[int] = Field(25, ge=1, le=100, description="Page size (1-100)")
    cursor: Optional[str] = Field(None, description="Pagination cursor")
    status: Optional[str] = Field(None, description="Comma-separated statuses")
    from_date: Optional[str] = Field(None, description="ISO timestamp lower bound")
    to_date: Optional[str] = Field(None, description="ISO timestamp upper bound")
    agent_id: Optional[str] = Field(None, description="Filter runs to one agent ID")


class ListTriggerRunsRequest(BaseModel):
    """Request to list runs from a trigger."""
    trigger_id: str = Field(..., description="Trigger ID")
    limit: Optional[int] = Field(25, ge=1, le=100, description="Page size (1-100)")
    cursor: Optional[str] = Field(None, description="Pagination cursor")
    status: Optional[str] = Field(None, description="Comma-separated statuses")
    from_date: Optional[str] = Field(None, description="ISO timestamp lower bound")
    to_date: Optional[str] = Field(None, description="ISO timestamp upper bound")


# =============================================================================
# Request Models - Agent Nodes
# =============================================================================

class ListAgentNodesRequest(BaseModel):
    """Request to list available node types."""
    pass  # No parameters required


class GetAgentNodeRequest(BaseModel):
    """Request to get a node type."""
    node_id: str = Field(..., description="Node type ID or agent node instance ID")


class GetNodeTypeRequest(BaseModel):
    """Request to get node type from the public catalog."""
    node_type_id: str = Field(..., description="Node type UUID")


class GetAgentRunNodesRequest(BaseModel):
    """Request to get node-level details for a run."""
    run_id: str = Field(..., description="Run ID to get node details for")


# =============================================================================
# Request Models - Triggers
# =============================================================================

class ListAgentTriggersRequest(BaseModel):
    """Request to list triggers for an agent."""
    agent_id: str = Field(..., description="Agent ID")


class AddYouTubeChannelsRequest(BaseModel):
    """Request to add YouTube channels to monitor."""
    agent_id: str = Field(..., description="Agent ID")
    youtube_channels: list[str] = Field(..., description="YouTube channel IDs or URLs to add")
    trigger_callback_url: Optional[str] = Field(None, description="Webhook URL (replaces existing if provided)")


class RemoveYouTubeChannelsRequest(BaseModel):
    """Request to remove YouTube channels."""
    agent_id: str = Field(..., description="Agent ID")
    youtube_channels: list[str] = Field(..., description="YouTube channel IDs or URLs to remove")


# =============================================================================
# Request Models - Asset Management
# =============================================================================

class CreateUploadUrlRequest(BaseModel):
    """Request to create an upload URL."""
    asset_type: AssetType = Field(..., description="Asset type: video, audio, or image")


class FinalizeUploadRequest(BaseModel):
    """Request to finalize an upload."""
    asset_type: AssetType = Field(..., description="Asset type: video, audio, or image")
    asset_id: str = Field(..., description="Asset ID returned from create upload URL")


class GetAssetViewUrlRequest(BaseModel):
    """Request to get a viewing URL for an asset."""
    asset_type: AssetType = Field(..., description="Asset type: video, audio, or image")
    asset_id: str = Field(..., description="Asset ID")


class UploadVideoRequest(BaseModel):
    """Convenience request to upload a video file."""
    file_path: str = Field(..., description="Local path to the video file")


class UploadAudioRequest(BaseModel):
    """Convenience request to upload an audio file."""
    file_path: str = Field(..., description="Local path to the audio file")


class UploadImageRequest(BaseModel):
    """Convenience request to upload an image file."""
    file_path: str = Field(..., description="Local path to the image file")


# =============================================================================
# Request Models - Credits
# =============================================================================

class GetCreditsRequest(BaseModel):
    """Request to get credit balance."""
    pass  # No parameters required


class GetCreditUsageRequest(BaseModel):
    """Request to get credit usage breakdown."""
    start_date: Optional[str] = Field(None, description="ISO date/datetime start bound (defaults to 30 days before end_date)")
    end_date: Optional[str] = Field(None, description="ISO date/datetime end bound (defaults to now)")
    limit: Optional[int] = Field(5000, ge=1, le=10000, description="Max raw usage events scanned (1-10,000)")


class BuyCreditsRequest(BaseModel):
    """Request to buy credits."""
    credits: int = Field(..., ge=100, le=1000000, description="Number of credits to buy (100-1,000,000)")
    success_url: Optional[str] = Field(None, description="Override checkout success redirect URL")
    cancel_url: Optional[str] = Field(None, description="Override checkout cancel redirect URL")


# =============================================================================
# Request Models - Plan
# =============================================================================

class GetPlanRequest(BaseModel):
    """Request to get current plan."""
    pass  # No parameters required


class ListPlansRequest(BaseModel):
    """Request to list available plans."""
    pass  # No parameters required


class UpgradePlanRequest(BaseModel):
    """Request to upgrade plan."""
    plan_id: PlanId = Field(..., description="Target plan ID")
    success_url: Optional[str] = Field(None, description="Override checkout success redirect URL")
    cancel_url: Optional[str] = Field(None, description="Override checkout cancel redirect URL")


# =============================================================================
# Request Models - Social
# =============================================================================

class ConnectSocialPlatformRequest(BaseModel):
    """Request to connect a social platform."""
    platform: SocialPlatform = Field(..., description="Social platform to connect")


class GetSocialPlatformStatusRequest(BaseModel):
    """Request to get social platform status."""
    platform: SocialPlatform = Field(..., description="Social platform to check")


class RemoveSocialPlatformRequest(BaseModel):
    """Request to remove a social platform."""
    platform: SocialPlatform = Field(..., description="Social platform to disconnect")


class CreateSocialPostRequest(BaseModel):
    """Request to create a social post."""
    platforms: list[SocialPlatform] = Field(..., description="Target platforms")
    post: Optional[str] = Field("", description="Post text")
    media_urls: Optional[list[str]] = Field(None, description="Public media URLs to attach")
    schedule_date: Optional[str] = Field(None, description="ISO timestamp to schedule post")
    workspace_id: Optional[str] = Field(None, description="Workspace to associate with the post")


class GetSocialPostRequest(BaseModel):
    """Request to get a social post."""
    post_id: str = Field(..., description="Provider post ID")


class GetTrackedSocialPostRequest(BaseModel):
    """Request to get a tracked social post."""
    tracking_id: str = Field(..., description="Tracking ID")


class UpdateSocialPostRequest(BaseModel):
    """Request to update a social post."""
    post_id: str = Field(..., description="Post ID to update")
    schedule_date: Optional[str] = Field(None, description="New scheduled publish timestamp")
    scheduled_pause: Optional[bool] = Field(None, description="Pause or resume scheduled publishing")
    notes: Optional[str] = Field(None, description="Scheduling notes")
    approve: Optional[bool] = Field(None, description="Approve a pending post")


class DeleteSocialPostRequest(BaseModel):
    """Request to delete a social post."""
    post_id: str = Field(..., description="Post ID to delete")
    mark_manual_deleted: Optional[bool] = Field(None, description="Provider hint for manually-deleted state")


# =============================================================================
# Response Models
# =============================================================================

class WhoAmIResponse(BaseModel):
    """Response for whoami endpoint."""
    organization_id: str
    organization_name: str
    organization_slug: str
    created_at: str
    last_used_at: Optional[str] = None


class AgentSummary(BaseModel):
    """Summary of an agent."""
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str


class AgentDetails(BaseModel):
    """Detailed agent information."""
    id: str
    name: str
    description: Optional[str] = None
    visibility: Optional[str] = None
    created_at: str
    updated_at: str


class NodeDetails(BaseModel):
    """Node instance details."""
    id: str
    node_type_id: str
    node_type_name: str
    position_x: float
    position_y: float
    z_index: Optional[int] = None
    instance_id: Optional[str] = None
    notification_settings: Optional[dict] = None
    params_used: dict = Field(default_factory=dict)


class ConnectionDetails(BaseModel):
    """Connection details."""
    source_agent_node_id: str
    target_agent_node_id: str


class GetAgentResponse(BaseModel):
    """Response for get agent."""
    agent: AgentDetails
    nodes: list[NodeDetails]
    connections: list[ConnectionDetails]


class ListAgentsResponse(BaseModel):
    """Response for list agents."""
    agents: list[AgentSummary]
    next_cursor: Optional[str] = None


class CreateAgentResponse(BaseModel):
    """Response for create agent."""
    success: bool
    agent_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[str] = None
    workspace_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CreatedNode(BaseModel):
    """Node created during an update operation."""
    temp_ref_id: Optional[str] = None
    agent_node_id: str


class UpdateAgentResponse(BaseModel):
    """Response for update agent."""
    success: bool
    agent_id: str
    operations_applied: Optional[int] = None
    created_nodes: Optional[list[CreatedNode]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[str] = None
    workspace_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DuplicateAgentResponse(BaseModel):
    """Response for duplicate agent."""
    agent: AgentDetails
    agent_nodes: list[NodeDetails]
    connections: list[ConnectionDetails]


class DeleteAgentResponse(BaseModel):
    """Response for delete agent."""
    success: bool
    agent_id: str
    message: str


class RunOutput(BaseModel):
    """Output from an agent run."""
    id: str
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    premiere_prproj_url: Optional[str] = None
    completed_at: Optional[str] = None
    original_node_id: Optional[str] = None


class RunInput(BaseModel):
    """Input to an agent run."""
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None


class NodeStatusCounts(BaseModel):
    """Node status counts."""
    completed: int = 0
    in_progress: int = 0
    failed: int = 0


class TriggeredBy(BaseModel):
    """What triggered the run."""
    trigger_id: Optional[str] = None


class RunAgentResponse(BaseModel):
    """Response for run agent."""
    run_id: str
    agent_id: str
    status: str
    status_message: Optional[str] = None
    started_at: str
    updated_at: str
    node_status_counts: NodeStatusCounts
    inputs: list[RunInput] = Field(default_factory=list)
    outputs: list[RunOutput] = Field(default_factory=list)
    triggered_by: Optional[TriggeredBy] = None


class GetAgentRunResponse(BaseModel):
    """Response for get agent run."""
    agent_id: str
    started_at: str
    status: str
    status_message: Optional[str] = None
    node_status_counts: NodeStatusCounts
    inputs: list[RunInput] = Field(default_factory=list)
    outputs: list[RunOutput] = Field(default_factory=list)


class CancelAgentRunResponse(BaseModel):
    """Response for cancel agent run."""
    success: bool
    run_id: str
    tasks_cancelled: int
    nodes_reset: int
    message: str


class RunSummary(BaseModel):
    """Summary of an agent run."""
    run_id: str
    agent_id: str
    status: str
    status_message: Optional[str] = None
    started_at: str
    updated_at: str
    node_status_counts: NodeStatusCounts
    inputs: list[RunInput] = Field(default_factory=list)
    outputs: list[RunOutput] = Field(default_factory=list)
    triggered_by: Optional[TriggeredBy] = None


class ListAgentRunsResponse(BaseModel):
    """Response for list agent runs."""
    runs: list[RunSummary]
    next_cursor: Optional[str] = None


class NodeTypeDocs(BaseModel):
    """Documentation for a node type."""
    path: Optional[str] = None
    anchor: Optional[str] = None
    url: Optional[str] = None


class NodeType(BaseModel):
    """Node type information."""
    node_type_id: str
    name: str
    docs: Optional[NodeTypeDocs] = None


class ListAgentNodesResponse(BaseModel):
    """Response for list agent nodes."""
    agent_nodes: list[NodeType]


class GetAgentNodeResponse(BaseModel):
    """Response for get agent node."""
    agent_node: NodeType


class NodeTypeInfo(BaseModel):
    """Node type from the public catalog."""
    node_type_id: str
    node_type_name: Optional[str] = None
    docs_url: Optional[str] = None
    params_docs_url: Optional[str] = None


class GetNodeTypeResponse(BaseModel):
    """Response for get node type."""
    node_type: NodeTypeInfo


class RunNodeStatus(BaseModel):
    """Status of a node in a run."""
    agent_node_id: str
    node_type_id: Optional[str] = None
    node_type_name: Optional[str] = None
    status: str
    status_message: Optional[str] = None
    needs_credits: Optional[bool] = None
    error: Optional[str] = None


class GetAgentRunNodesResponse(BaseModel):
    """Response for get agent run nodes."""
    run_id: str
    nodes: list[RunNodeStatus]


class YouTubeChannelDetails(BaseModel):
    """YouTube channel details."""
    channel_id: str
    channel_name: Optional[str] = None
    channel_handle: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subscriber_count: Optional[int] = None


class TriggerInfo(BaseModel):
    """Trigger information."""
    id: str
    type: str
    youtube_channels: list[str] = Field(default_factory=list)
    youtube_channel_details: list[YouTubeChannelDetails] = Field(default_factory=list)


class ListAgentTriggersResponse(BaseModel):
    """Response for list agent triggers."""
    triggers: list[TriggerInfo] = Field(default_factory=list)


class ChannelMapping(BaseModel):
    """Mapping of input to channel ID."""
    input: str
    channel_id: str


class AddYouTubeChannelsResponse(BaseModel):
    """Response for add YouTube channels."""
    message: str
    channel_ids: list[str]
    channels: list[ChannelMapping]
    youtube_channel_details: list[YouTubeChannelDetails]


class RemoveYouTubeChannelsResponse(BaseModel):
    """Response for remove YouTube channels."""
    message: str
    removed_channels: list[str] = Field(default_factory=list)


class UploadFields(BaseModel):
    """Upload fields for signed URL."""
    key: Optional[str] = None
    policy: Optional[str] = None
    # Google Cloud Storage signature
    x_goog_signature: Optional[str] = Field(None, alias="x-goog-signature")
    # AWS S3 fields
    x_amz_credential: Optional[str] = Field(None, alias="x-amz-credential")
    x_amz_algorithm: Optional[str] = Field(None, alias="x-amz-algorithm")
    x_amz_date: Optional[str] = Field(None, alias="x-amz-date")
    x_amz_signature: Optional[str] = Field(None, alias="x-amz-signature")

    class Config:
        populate_by_name = True


class CreateUploadUrlResponse(BaseModel):
    """Response for create upload URL."""
    upload_url: str
    upload_fields: dict  # Keep as dict for flexibility
    max_file_size_bytes: Optional[int] = None
    video_id: Optional[str] = None
    audio_id: Optional[str] = None
    image_id: Optional[str] = None


class FinalizeUploadResponse(BaseModel):
    """Response for finalize upload."""
    video_id: Optional[str] = None
    audio_id: Optional[str] = None
    image_id: Optional[str] = None


class GetAssetViewUrlResponse(BaseModel):
    """Response for get asset view URL."""
    asset_type: str
    asset_id: str
    signed_url: str
    thumbnail_url: Optional[str] = None


class UploadAssetResponse(BaseModel):
    """Response for convenience upload methods."""
    asset_id: str
    asset_type: str


class CreditsInfo(BaseModel):
    """Credit balance information."""
    balance: int
    unlimited: bool
    usage: int
    included_usage: int
    next_reset_at: Optional[str] = None


class GetCreditsResponse(BaseModel):
    """Response for get credits."""
    organization_id: str
    credits: CreditsInfo
    plan: str


class BuyCreditsResponse(BaseModel):
    """Response for buy credits."""
    success: bool
    requires_checkout: bool
    credits_purchased: Optional[int] = None
    amount_charged_usd: Optional[float] = None
    plan: Optional[str] = None
    checkout_url: Optional[str] = None


class TileUsage(BaseModel):
    """Credit usage by tile."""
    tile_id: str
    tile_name: Optional[str] = None
    credits_used: int
    events: int


class DateUsage(BaseModel):
    """Credit usage by date."""
    date: str
    credits_used: int
    events: int


class DateTileUsage(BaseModel):
    """Credit usage by date and tile."""
    date: str
    tile_id: str
    tile_name: Optional[str] = None
    credits_used: int
    events: int


class UsageBreakdown(BaseModel):
    """Credit usage breakdown."""
    by_tile: list[TileUsage] = Field(default_factory=list)
    by_date: list[DateUsage] = Field(default_factory=list)
    by_date_and_tile: list[DateTileUsage] = Field(default_factory=list)


class UsageSummary(BaseModel):
    """Summary of credit usage."""
    total_credits_used: int
    total_events: int
    matching_events: int
    returned_events: int
    truncated: bool


class DateRange(BaseModel):
    """Date range for usage query."""
    start_date: str
    end_date: str


class GetCreditUsageResponse(BaseModel):
    """Response for get credit usage."""
    organization_id: str
    date_range: DateRange
    summary: UsageSummary
    breakdown: UsageBreakdown


class PlanInfo(BaseModel):
    """Plan information."""
    id: str
    family: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[str] = None
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    canceled_at: Optional[str] = None


class GetPlanResponse(BaseModel):
    """Response for get plan."""
    organization_id: str
    plan: PlanInfo
    scheduled_plan: Optional[PlanInfo] = None
    credits: CreditsInfo


class PlanOption(BaseModel):
    """Available plan option."""
    id: str
    aliases: list[str] = Field(default_factory=list)
    monthly_price_usd: Optional[float] = None
    annual_price_usd: Optional[float] = None
    credits_per_month: Optional[int] = None
    top_up_rate_per_100_credits_usd: float
    notes: Optional[str] = None


class ListPlansResponse(BaseModel):
    """Response for list plans."""
    plans: list[PlanOption]


class UpgradePlanResponse(BaseModel):
    """Response for upgrade plan."""
    success: bool
    requires_checkout: bool
    plan_id: str
    plan_family: Optional[str] = None
    checkout_url: Optional[str] = None


class ConnectSocialPlatformResponse(BaseModel):
    """Response for connect social platform."""
    platform: str
    connect_url: str


class SocialAccount(BaseModel):
    """Social account information."""
    username: Optional[str] = None
    display_name: Optional[str] = None
    profile_url: Optional[str] = None
    user_image: Optional[str] = None


class GetSocialPlatformStatusResponse(BaseModel):
    """Response for get social platform status."""
    platform: str
    connected: bool
    account: Optional[SocialAccount] = None


class RemoveSocialPlatformResponse(BaseModel):
    """Response for remove social platform."""
    success: bool
    platform: str


class PostLink(BaseModel):
    """Link to a social post."""
    platform: str
    post_url: str


class PostResult(BaseModel):
    """Result for a platform post."""
    platform: str
    status: str
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    message: Optional[str] = None


class CreateSocialPostResponse(BaseModel):
    """Response for create social post."""
    post_id: str
    status: str
    links: list[PostLink] = Field(default_factory=list)
    results: list[PostResult] = Field(default_factory=list)
    error: Optional[dict] = None
    tracking_id: Optional[str] = None
    tracked_status: Optional[str] = None


class PostStats(BaseModel):
    """Post analytics stats."""
    status: Optional[str] = None


class GetSocialPostResponse(BaseModel):
    """Response for get social post."""
    post_id: str
    status: str
    links: list[PostLink] = Field(default_factory=list)
    results: list[PostResult] = Field(default_factory=list)
    stats: Optional[PostStats] = None
    error: Optional[dict] = None
    tracking_id: Optional[str] = None
    tracked_status: Optional[str] = None


class GetTrackedSocialPostResponse(BaseModel):
    """Response for get tracked social post."""
    tracking_id: str
    provider_post_id: Optional[str] = None
    status: str
    scheduled_at: Optional[str] = None
    platforms: list[str] = Field(default_factory=list)
    links: list[PostLink] = Field(default_factory=list)
    results: list[PostResult] = Field(default_factory=list)
    error: Optional[dict] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UpdateSocialPostResponse(BaseModel):
    """Response for update social post."""
    post_id: str
    status: str
    tracking_id: Optional[str] = None
    tracked_status: Optional[str] = None


class DeleteSocialPostResponse(BaseModel):
    """Response for delete social post."""
    post_id: str
    status: str
    tracking_id: Optional[str] = None
    tracked_status: Optional[str] = None


# =============================================================================
# Client
# =============================================================================

class MosaicClient:
    """
    Async client for the Mosaic video editing automation API.
    
    Usage:
        client = MosaicClient(api_key="mk_your_key")
        # or set MOSAIC_API_KEY environment variable
        client = MosaicClient()
        
        # List agents
        response = await client.list_agents(ListAgentsRequest())
        
        # Run an agent on a YouTube video
        response = await client.run_agent(RunAgentRequest(
            agent_id="...",
            video_urls=["https://youtube.com/watch?v=..."]
        ))
    """
    
    BASE_URL = "https://api.mosaic.so"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0
    ):
        """
        Initialize the Mosaic client.
        
        Args:
            api_key: Mosaic API key (prefix mk_). Falls back to MOSAIC_API_KEY env var.
            base_url: Override the base URL.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or os.environ.get("MOSAIC_API_KEY")
        if not self.api_key:
            raise ValueError("API key required. Pass api_key or set MOSAIC_API_KEY env var.")
        
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=self.timeout
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None
    ) -> dict:
        """Make an HTTP request."""
        client = await self._get_client()
        
        # Filter out None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        
        response = await client.request(
            method=method,
            url=path,
            params=params,
            json=json_data
        )
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # Agents
    # =========================================================================
    
    async def create_agent(self, request: CreateAgentRequest) -> CreateAgentResponse:
        """Create a new agent."""
        data = request.model_dump(exclude_none=True)
        result = await self._request("POST", "/agent/create", json_data=data)
        return CreateAgentResponse(**result)
    
    async def update_agent(self, request: UpdateAgentRequest) -> UpdateAgentResponse:
        """Update an existing agent."""
        agent_id = request.agent_id
        data = request.model_dump(exclude_none=True, exclude={"agent_id"})
        result = await self._request("POST", f"/agent/{agent_id}/update", json_data=data)
        return UpdateAgentResponse(**result)
    
    async def delete_agent(self, request: DeleteAgentRequest) -> DeleteAgentResponse:
        """Delete an agent."""
        result = await self._request("POST", f"/agent/{request.agent_id}/delete")
        return DeleteAgentResponse(**result)
    
    async def list_agents(self, request: ListAgentsRequest) -> ListAgentsResponse:
        """List all agents."""
        params = request.model_dump(exclude_none=True)
        result = await self._request("GET", "/agents", params=params)
        return ListAgentsResponse(**result)
    
    async def get_agent(self, request: GetAgentRequest) -> GetAgentResponse:
        """Get an agent with nodes and connections."""
        result = await self._request("GET", f"/agent/{request.agent_id}")
        return GetAgentResponse(**result)
    
    async def duplicate_agent(self, request: DuplicateAgentRequest) -> DuplicateAgentResponse:
        """Duplicate an agent with all its nodes and connections."""
        agent_id = request.agent_id
        data = request.model_dump(exclude_none=True, exclude={"agent_id"})
        result = await self._request("POST", f"/agent/{agent_id}/duplicate", json_data=data if data else None)
        return DuplicateAgentResponse(**result)
    
    async def whoami(self, request: WhoAmIRequest) -> WhoAmIResponse:
        """Validate API key and get organization info."""
        result = await self._request("GET", "/whoami")
        return WhoAmIResponse(**result)
    
    # =========================================================================
    # Agent Runs
    # =========================================================================
    
    async def run_agent(self, request: RunAgentRequest) -> RunAgentResponse:
        """Execute an agent on videos."""
        agent_id = request.agent_id
        data = request.model_dump(exclude_none=True, exclude={"agent_id"})
        result = await self._request("POST", f"/agent/{agent_id}/run", json_data=data)
        return RunAgentResponse(**result)
    
    async def get_agent_run(self, request: GetAgentRunRequest) -> GetAgentRunResponse:
        """Get run status and outputs."""
        result = await self._request("GET", f"/agent_run/{request.run_id}")
        return GetAgentRunResponse(**result)
    
    async def cancel_agent_run(self, request: CancelAgentRunRequest) -> CancelAgentRunResponse:
        """Cancel an active run."""
        result = await self._request("POST", f"/agent_run/{request.run_id}/cancel")
        return CancelAgentRunResponse(**result)
    
    async def list_agent_runs(self, request: ListAgentRunsRequest) -> ListAgentRunsResponse:
        """List runs for an agent."""
        params = {
            "limit": request.limit,
            "cursor": request.cursor,
            "status": request.status,
            "from": request.from_date,
            "to": request.to_date
        }
        result = await self._request("GET", f"/agent/{request.agent_id}/runs", params=params)
        return ListAgentRunsResponse(**result)
    
    async def list_all_agent_runs(self, request: ListAllAgentRunsRequest) -> ListAgentRunsResponse:
        """List all runs across agents."""
        params = {
            "limit": request.limit,
            "cursor": request.cursor,
            "status": request.status,
            "from": request.from_date,
            "to": request.to_date,
            "agent_id": request.agent_id
        }
        result = await self._request("GET", "/agent_runs", params=params)
        return ListAgentRunsResponse(**result)
    
    async def list_trigger_runs(self, request: ListTriggerRunsRequest) -> ListAgentRunsResponse:
        """List runs from a trigger."""
        params = {
            "limit": request.limit,
            "cursor": request.cursor,
            "status": request.status,
            "from": request.from_date,
            "to": request.to_date
        }
        result = await self._request("GET", f"/trigger/{request.trigger_id}/runs", params=params)
        return ListAgentRunsResponse(**result)
    
    async def get_agent_run_nodes(self, request: GetAgentRunNodesRequest) -> GetAgentRunNodesResponse:
        """Get node-level details for a run including credit-blocked status."""
        result = await self._request("GET", f"/agent_run/{request.run_id}/nodes")
        return GetAgentRunNodesResponse(**result)
    
    # =========================================================================
    # Agent Nodes
    # =========================================================================
    
    async def list_agent_nodes(self, request: ListAgentNodesRequest) -> ListAgentNodesResponse:
        """List available node types."""
        result = await self._request("GET", "/agent_nodes")
        return ListAgentNodesResponse(**result)
    
    async def get_agent_node(self, request: GetAgentNodeRequest) -> GetAgentNodeResponse:
        """Get node type details."""
        result = await self._request("GET", f"/agent_nodes/{request.node_id}")
        return GetAgentNodeResponse(**result)
    
    async def get_node_type(self, request: GetNodeTypeRequest) -> GetNodeTypeResponse:
        """Get node type from the public catalog."""
        result = await self._request("GET", f"/node_type/{request.node_type_id}")
        return GetNodeTypeResponse(**result)
    
    # =========================================================================
    # Triggers
    # =========================================================================
    
    async def list_agent_triggers(self, request: ListAgentTriggersRequest) -> ListAgentTriggersResponse:
        """List YouTube triggers for an agent."""
        result = await self._request("GET", f"/agent/{request.agent_id}/triggers")
        # API returns array directly
        if isinstance(result, list):
            return ListAgentTriggersResponse(triggers=result)
        return ListAgentTriggersResponse(**result)
    
    async def add_youtube_channels(self, request: AddYouTubeChannelsRequest) -> AddYouTubeChannelsResponse:
        """Add YouTube channels to monitor."""
        data = request.model_dump(exclude_none=True, exclude={"agent_id"})
        result = await self._request(
            "POST",
            f"/agent/{request.agent_id}/triggers/add_youtube_channels",
            json_data=data
        )
        return AddYouTubeChannelsResponse(**result)
    
    async def remove_youtube_channels(self, request: RemoveYouTubeChannelsRequest) -> RemoveYouTubeChannelsResponse:
        """Remove YouTube channels."""
        data = request.model_dump(exclude_none=True, exclude={"agent_id"})
        result = await self._request(
            "POST",
            f"/agent/{request.agent_id}/triggers/remove_youtube_channels",
            json_data=data
        )
        return RemoveYouTubeChannelsResponse(**result)
    
    # =========================================================================
    # Asset Management
    # =========================================================================
    
    async def create_upload_url(self, request: CreateUploadUrlRequest) -> CreateUploadUrlResponse:
        """Create a signed upload URL for an asset."""
        result = await self._request(
            "POST",
            f"/uploads/{request.asset_type.value}/get_upload_url"
        )
        return CreateUploadUrlResponse(**result)
    
    async def finalize_upload(self, request: FinalizeUploadRequest) -> FinalizeUploadResponse:
        """Finalize an asset upload."""
        asset_type = request.asset_type.value
        id_field = f"{asset_type}_id"
        data = {id_field: request.asset_id}
        result = await self._request(
            "POST",
            f"/uploads/{asset_type}/finalize_upload",
            json_data=data
        )
        return FinalizeUploadResponse(**result)
    
    async def get_asset_view_url(self, request: GetAssetViewUrlRequest) -> GetAssetViewUrlResponse:
        """Get a signed viewing URL for an asset."""
        data = {
            "asset_type": request.asset_type.value,
            "asset_id": request.asset_id
        }
        result = await self._request("POST", "/uploads/get_view_url", json_data=data)
        return GetAssetViewUrlResponse(**result)
    
    async def _upload_file(
        self,
        file_path: str,
        asset_type: AssetType
    ) -> UploadAssetResponse:
        """
        Internal method to handle the 3-step upload flow.
        
        1. Get signed upload URL
        2. Upload file to signed URL
        3. Finalize upload
        """
        # Step 1: Get upload URL
        upload_response = await self.create_upload_url(
            CreateUploadUrlRequest(asset_type=asset_type)
        )
        
        # Get the asset ID from response
        asset_id = (
            upload_response.video_id or
            upload_response.audio_id or
            upload_response.image_id
        )
        if not asset_id:
            raise ValueError("No asset ID returned from create_upload_url")
        
        # Step 2: Upload file to signed URL
        with open(file_path, "rb") as f:
            file_data = f.read()
        
        # Build form data with upload fields
        async with httpx.AsyncClient(timeout=300.0) as upload_client:
            # Prepare multipart form data
            files = {"file": (os.path.basename(file_path), file_data)}
            data = upload_response.upload_fields
            
            response = await upload_client.post(
                upload_response.upload_url,
                data=data,
                files=files
            )
            response.raise_for_status()
        
        # Step 3: Finalize upload
        await self.finalize_upload(
            FinalizeUploadRequest(asset_type=asset_type, asset_id=asset_id)
        )
        
        return UploadAssetResponse(asset_id=asset_id, asset_type=asset_type.value)
    
    async def upload_video(self, request: UploadVideoRequest) -> UploadAssetResponse:
        """
        Upload a video file (convenience method).
        
        Handles the complete 3-step flow:
        1. Get signed upload URL
        2. Upload file
        3. Finalize upload
        
        Returns the video_id to use in agent runs.
        """
        return await self._upload_file(request.file_path, AssetType.VIDEO)
    
    async def upload_audio(self, request: UploadAudioRequest) -> UploadAssetResponse:
        """
        Upload an audio file (convenience method).
        
        Handles the complete 3-step flow:
        1. Get signed upload URL
        2. Upload file
        3. Finalize upload
        
        Returns the audio_id to use in agent runs.
        """
        return await self._upload_file(request.file_path, AssetType.AUDIO)
    
    async def upload_image(self, request: UploadImageRequest) -> UploadAssetResponse:
        """
        Upload an image file (convenience method).
        
        Handles the complete 3-step flow:
        1. Get signed upload URL
        2. Upload file
        3. Finalize upload
        
        Returns the image_id to use in agent runs.
        """
        return await self._upload_file(request.file_path, AssetType.IMAGE)
    
    # =========================================================================
    # Credits
    # =========================================================================
    
    async def get_credits(self, request: GetCreditsRequest) -> GetCreditsResponse:
        """Get organization credit balance."""
        result = await self._request("GET", "/credits")
        return GetCreditsResponse(**result)
    
    async def get_credit_usage(self, request: GetCreditUsageRequest) -> GetCreditUsageResponse:
        """Get credit usage breakdown by tile and date."""
        params = request.model_dump(exclude_none=True)
        result = await self._request("GET", "/credits/usage", params=params)
        return GetCreditUsageResponse(**result)
    
    async def buy_credits(self, request: BuyCreditsRequest) -> BuyCreditsResponse:
        """Purchase top-up credits."""
        data = request.model_dump(exclude_none=True)
        result = await self._request("POST", "/credits/buy", json_data=data)
        return BuyCreditsResponse(**result)
    
    # =========================================================================
    # Plan
    # =========================================================================
    
    async def get_plan(self, request: GetPlanRequest) -> GetPlanResponse:
        """Get current plan details."""
        result = await self._request("GET", "/plan")
        return GetPlanResponse(**result)
    
    async def list_plans(self, request: ListPlansRequest) -> ListPlansResponse:
        """List available plans."""
        result = await self._request("GET", "/plan/list")
        return ListPlansResponse(**result)
    
    async def upgrade_plan(self, request: UpgradePlanRequest) -> UpgradePlanResponse:
        """Upgrade or change plan."""
        data = request.model_dump(exclude_none=True)
        data["plan_id"] = data["plan_id"].value if isinstance(data["plan_id"], PlanId) else data["plan_id"]
        result = await self._request("POST", "/plan/upgrade", json_data=data)
        return UpgradePlanResponse(**result)
    
    # =========================================================================
    # Social
    # =========================================================================
    
    async def connect_social_platform(self, request: ConnectSocialPlatformRequest) -> ConnectSocialPlatformResponse:
        """Generate a social linking URL."""
        result = await self._request(
            "POST",
            f"/social/{request.platform.value}/connect"
        )
        return ConnectSocialPlatformResponse(**result)
    
    async def get_social_platform_status(self, request: GetSocialPlatformStatusRequest) -> GetSocialPlatformStatusResponse:
        """Check platform connection status."""
        result = await self._request(
            "GET",
            f"/social/{request.platform.value}/status"
        )
        return GetSocialPlatformStatusResponse(**result)
    
    async def remove_social_platform(self, request: RemoveSocialPlatformRequest) -> RemoveSocialPlatformResponse:
        """Disconnect a social platform."""
        result = await self._request(
            "DELETE",
            f"/social/{request.platform.value}/remove"
        )
        return RemoveSocialPlatformResponse(**result)
    
    async def create_social_post(self, request: CreateSocialPostRequest) -> CreateSocialPostResponse:
        """Publish or schedule a social post."""
        data = request.model_dump(exclude_none=True)
        # Convert platform enums to strings
        data["platforms"] = [p.value if isinstance(p, SocialPlatform) else p for p in data["platforms"]]
        result = await self._request("POST", "/social/post", json_data=data)
        return CreateSocialPostResponse(**result)
    
    async def get_social_post(self, request: GetSocialPostRequest) -> GetSocialPostResponse:
        """Get social post status."""
        result = await self._request("GET", f"/social/post/{request.post_id}")
        return GetSocialPostResponse(**result)
    
    async def get_tracked_social_post(self, request: GetTrackedSocialPostRequest) -> GetTrackedSocialPostResponse:
        """Get tracked social post record."""
        result = await self._request("GET", f"/social/post/track/{request.tracking_id}")
        return GetTrackedSocialPostResponse(**result)
    
    async def update_social_post(self, request: UpdateSocialPostRequest) -> UpdateSocialPostResponse:
        """Update a scheduled social post."""
        post_id = request.post_id
        data = request.model_dump(exclude_none=True, exclude={"post_id"})
        result = await self._request("PATCH", f"/social/post/{post_id}", json_data=data)
        return UpdateSocialPostResponse(**result)
    
    async def delete_social_post(self, request: DeleteSocialPostRequest) -> DeleteSocialPostResponse:
        """Delete a social post."""
        post_id = request.post_id
        data = request.model_dump(exclude_none=True, exclude={"post_id"})
        result = await self._request("DELETE", f"/social/post/{post_id}", json_data=data if data else None)
        return DeleteSocialPostResponse(**result)
