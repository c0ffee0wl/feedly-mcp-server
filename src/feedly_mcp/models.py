"""Pydantic v2 input models for Feedly MCP Server."""

from typing import Optional, Literal, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


class GetStreamContentsInput(BaseModel):
    """Input for fetching articles from a stream."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    stream_id: str = Field(
        ...,
        description="Stream ID: 'feed/URL' for feeds, 'user/ID/category/label' for categories, 'user/ID/tag/global.saved' for saved articles",
        min_length=1,
    )
    count: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of articles to return (1-100, default 20)",
    )
    unread_only: bool = Field(
        default=True,
        description="Only return unread articles (default: True)",
    )
    continuation: Optional[str] = Field(
        default=None,
        description="Continuation token for pagination",
    )
    ranked: Literal["newest", "oldest"] = Field(
        default="newest",
        description="Sort order: 'newest' or 'oldest'",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable",
    )


class MarkAsReadInput(BaseModel):
    """Input for marking entries as read."""

    model_config = ConfigDict(extra="forbid")

    entry_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of entry IDs to mark as read (max 1000)",
    )


class MarkFeedAsReadInput(BaseModel):
    """Input for marking an entire feed as read."""

    model_config = ConfigDict(extra="forbid")

    feed_id: str = Field(
        ...,
        description="Feed stream ID (format: 'feed/URL')",
        min_length=1,
    )
    as_of: Optional[int] = Field(
        default=None,
        description="Mark only entries older than this timestamp (epoch ms)",
    )


class MarkCategoryAsReadInput(BaseModel):
    """Input for marking an entire category as read."""

    model_config = ConfigDict(extra="forbid")

    category_id: str = Field(
        ...,
        description="Category stream ID (format: 'user/ID/category/label')",
        min_length=1,
    )
    as_of: Optional[int] = Field(
        default=None,
        description="Mark only entries older than this timestamp (epoch ms)",
    )


class GetEntryInput(BaseModel):
    """Input for getting a single entry."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(
        ...,
        description="Unique entry/article ID",
        min_length=1,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable",
    )


class GetEntriesInput(BaseModel):
    """Input for getting multiple entries."""

    model_config = ConfigDict(extra="forbid")

    entry_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of entry IDs to fetch (max 1000)",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable",
    )


class KeepUnreadInput(BaseModel):
    """Input for keeping entries unread (undo mark as read)."""

    model_config = ConfigDict(extra="forbid")

    entry_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of entry IDs to keep unread (max 1000)",
    )


class SimpleResponseFormatInput(BaseModel):
    """Input for tools that only need response format."""

    model_config = ConfigDict(extra="forbid")

    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable",
    )
