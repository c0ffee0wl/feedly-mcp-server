#!/usr/bin/env python3
"""MCP Server for Feedly API integration."""

import json
import os
from datetime import datetime
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from .client import FeedlyClient, FeedlyError
from .constants import CHARACTER_LIMIT
from .models import (
    GetEntriesInput,
    GetEntryInput,
    GetStreamContentsInput,
    KeepUnreadInput,
    MarkAsReadInput,
    MarkCategoryAsReadInput,
    MarkFeedAsReadInput,
    ResponseFormat,
    SimpleResponseFormatInput,
)

mcp = FastMCP("feedly_mcp")


def get_client() -> FeedlyClient:
    """Get configured Feedly client."""
    token = os.environ.get("FEEDLY_ACCESS_TOKEN")
    if not token:
        raise FeedlyError("FEEDLY_ACCESS_TOKEN environment variable not set", None)
    return FeedlyClient(token)


def _handle_error(e: Exception) -> str:
    """Consistent error formatting."""
    if isinstance(e, FeedlyError):
        return f"Error: {e.message}"
    elif isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Try again."
    elif isinstance(e, httpx.HTTPStatusError):
        return f"Error: HTTP {e.response.status_code}: {e.response.text}"
    return f"Error: {type(e).__name__}: {str(e)}"


def _truncate_response(content: str) -> str:
    """Truncate response to character limit."""
    if len(content) <= CHARACTER_LIMIT:
        return content
    return content[: CHARACTER_LIMIT - 50] + "\n\n... [Response truncated at 25000 characters]"


def _format_timestamp(timestamp_ms: int | None) -> str:
    """Format epoch milliseconds to ISO date string."""
    if timestamp_ms is None:
        return "Unknown"
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        return "Unknown"


def _truncate_text(text: str | None, max_length: int = 300) -> str:
    """Truncate text with ellipsis."""
    if text is None:
        return ""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def _get_article_content(entry: dict) -> str:
    """Extract article content from entry, preferring full content over summary."""
    # Try fullContent first (from Feedly Pro)
    if "fullContent" in entry:
        return entry["fullContent"]
    # Then try content
    if "content" in entry and entry["content"].get("content"):
        return entry["content"]["content"]
    # Fall back to summary
    if "summary" in entry and entry["summary"].get("content"):
        return entry["summary"]["content"]
    return ""


def _format_entry_markdown(entry: dict, include_content: bool = False) -> str:
    """Format a single entry as markdown."""
    title = entry.get("title", "Untitled")
    author = entry.get("author", "Unknown author")
    published = _format_timestamp(entry.get("published"))
    url = entry.get("alternate", [{}])[0].get("href", entry.get("canonicalUrl", ""))
    entry_id = entry.get("id", "")
    unread = entry.get("unread", False)

    content = _get_article_content(entry)
    summary = _truncate_text(content, 300)

    lines = [
        f"### {title}",
        f"**Author:** {author} | **Published:** {published} | **Unread:** {'Yes' if unread else 'No'}",
        f"**ID:** `{entry_id}`",
    ]
    if url:
        lines.append(f"**URL:** [{url}]({url})")

    if include_content and content:
        lines.append(f"\n**Content:**\n{content}")
    elif summary:
        lines.append(f"\n**Summary:** {summary}")

    return "\n".join(lines)


def _format_entries_markdown(entries: list[dict], include_content: bool = False) -> str:
    """Format multiple entries as markdown."""
    if not entries:
        return "No articles found."
    return "\n\n---\n\n".join(
        _format_entry_markdown(entry, include_content) for entry in entries
    )


def _format_stream_contents(data: dict, response_format: ResponseFormat) -> str:
    """Format stream contents response."""
    items = data.get("items", [])
    continuation = data.get("continuation")

    if response_format == ResponseFormat.JSON:
        result = {"items": items, "count": len(items)}
        if continuation:
            result["continuation"] = continuation
        return json.dumps(result, indent=2)

    # Markdown format
    lines = [f"## Articles ({len(items)} found)\n"]
    lines.append(_format_entries_markdown(items))

    if continuation:
        lines.append(f"\n\n---\n**More articles available.** Use continuation token: `{continuation}`")

    return "\n".join(lines)


def _format_profile_markdown(profile: dict) -> str:
    """Format user profile as markdown."""
    return f"""## Feedly Profile

**User ID:** `{profile.get('id', 'Unknown')}`
**Email:** {profile.get('email', 'Not available')}
**Name:** {profile.get('fullName', profile.get('givenName', 'Not available'))}
**Locale:** {profile.get('locale', 'Not available')}
**Login:** {profile.get('login', 'Not available')}
"""


def _format_subscriptions_markdown(subscriptions: list[dict]) -> str:
    """Format subscriptions list as markdown."""
    if not subscriptions:
        return "No subscriptions found."

    lines = [f"## Subscriptions ({len(subscriptions)} feeds)\n"]
    for sub in subscriptions:
        title = sub.get("title", "Untitled")
        feed_id = sub.get("id", "")
        website = sub.get("website", "")
        categories = [c.get("label", "") for c in sub.get("categories", [])]
        cat_str = ", ".join(categories) if categories else "Uncategorized"

        lines.append(f"### {title}")
        lines.append(f"**Feed ID:** `{feed_id}`")
        if website:
            lines.append(f"**Website:** [{website}]({website})")
        lines.append(f"**Categories:** {cat_str}")
        lines.append("")

    return "\n".join(lines)


def _format_categories_markdown(categories: list[dict]) -> str:
    """Format categories list as markdown."""
    if not categories:
        return "No categories found."

    lines = [f"## Categories ({len(categories)} found)\n"]
    for cat in categories:
        label = cat.get("label", "Unlabeled")
        cat_id = cat.get("id", "")
        lines.append(f"- **{label}**")
        lines.append(f"  - ID: `{cat_id}`")

    return "\n".join(lines)


def _format_tags_markdown(tags: list[dict]) -> str:
    """Format tags list as markdown."""
    if not tags:
        return "No tags found."

    lines = [f"## Tags ({len(tags)} found)\n"]
    for tag in tags:
        label = tag.get("label", tag.get("id", "").split("/")[-1])
        tag_id = tag.get("id", "")
        lines.append(f"- **{label}**")
        lines.append(f"  - ID: `{tag_id}`")

    return "\n".join(lines)


def _format_unread_counts_markdown(data: dict) -> str:
    """Format unread counts as markdown."""
    counts = data.get("unreadcounts", [])
    if not counts:
        return "No unread counts available."

    lines = ["## Unread Counts\n"]
    # Sort by count descending
    sorted_counts = sorted(counts, key=lambda x: x.get("count", 0), reverse=True)

    for item in sorted_counts:
        stream_id = item.get("id", "")
        count = item.get("count", 0)
        updated = _format_timestamp(item.get("updated"))

        # Extract readable name from stream ID
        if "/category/" in stream_id:
            name = stream_id.split("/category/")[-1]
            stream_type = "Category"
        elif "/tag/" in stream_id:
            name = stream_id.split("/tag/")[-1]
            stream_type = "Tag"
        elif stream_id.startswith("feed/"):
            name = stream_id[5:]  # Remove 'feed/' prefix
            stream_type = "Feed"
        else:
            name = stream_id
            stream_type = "Stream"

        lines.append(f"- **{name}** ({stream_type}): {count} unread (updated: {updated})")
        lines.append(f"  - ID: `{stream_id}`")

    return "\n".join(lines)


# =============================================================================
# Tools
# =============================================================================


@mcp.tool(
    name="feedly_get_profile",
    annotations={
        "title": "Get User Profile",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def feedly_get_profile(params: SimpleResponseFormatInput) -> str:
    """Get Feedly user profile information including user ID.

    Use this tool to verify authentication and retrieve the user ID needed
    for constructing stream IDs for categories and tags.

    Args:
        params (SimpleResponseFormatInput): Validated input containing:
            - response_format (str): 'markdown' for human-readable or 'json' for machine-readable

    Returns:
        str: User profile with ID, email, name, and locale.

    Examples:
        - Get profile: response_format="markdown"
        - The user ID is needed for stream IDs like 'user/{userId}/category/Tech'
    """
    try:
        client = get_client()
        profile = await client.get_profile()

        if params.response_format == ResponseFormat.JSON:
            return _truncate_response(json.dumps(profile, indent=2))

        return _truncate_response(_format_profile_markdown(profile))
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="feedly_get_subscriptions",
    annotations={
        "title": "Get Feed Subscriptions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def feedly_get_subscriptions(params: SimpleResponseFormatInput) -> str:
    """List all feed subscriptions.

    Use this tool to discover available feeds and their IDs for fetching articles.

    Args:
        params (SimpleResponseFormatInput): Validated input containing:
            - response_format (str): 'markdown' for human-readable or 'json' for machine-readable

    Returns:
        str: List of subscriptions with feed ID, title, website, and categories.

    Examples:
        - List all subscriptions: response_format="markdown"
        - Feed IDs have format 'feed/https://example.com/rss'
    """
    try:
        client = get_client()
        subscriptions = await client.get_subscriptions()

        if params.response_format == ResponseFormat.JSON:
            return _truncate_response(json.dumps(subscriptions, indent=2))

        return _truncate_response(_format_subscriptions_markdown(subscriptions))
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="feedly_get_categories",
    annotations={
        "title": "Get Categories",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def feedly_get_categories(params: SimpleResponseFormatInput) -> str:
    """List all categories/folders.

    Use this tool to discover available categories and their IDs.

    Args:
        params (SimpleResponseFormatInput): Validated input containing:
            - response_format (str): 'markdown' for human-readable or 'json' for machine-readable

    Returns:
        str: List of categories with ID and label.

    Examples:
        - List categories: response_format="markdown"
        - Category IDs have format 'user/{userId}/category/{label}'
    """
    try:
        client = get_client()
        categories = await client.get_categories()

        if params.response_format == ResponseFormat.JSON:
            return _truncate_response(json.dumps(categories, indent=2))

        return _truncate_response(_format_categories_markdown(categories))
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="feedly_get_tags",
    annotations={
        "title": "Get Tags",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def feedly_get_tags(params: SimpleResponseFormatInput) -> str:
    """List all tags including saved articles tag.

    Use this tool to discover available tags and their IDs.

    Args:
        params (SimpleResponseFormatInput): Validated input containing:
            - response_format (str): 'markdown' for human-readable or 'json' for machine-readable

    Returns:
        str: List of tags with ID and label.

    Examples:
        - List tags: response_format="markdown"
        - Saved articles tag: 'user/{userId}/tag/global.saved'
    """
    try:
        client = get_client()
        tags = await client.get_tags()

        if params.response_format == ResponseFormat.JSON:
            return _truncate_response(json.dumps(tags, indent=2))

        return _truncate_response(_format_tags_markdown(tags))
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="feedly_get_unread_counts",
    annotations={
        "title": "Get Unread Counts",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def feedly_get_unread_counts(params: SimpleResponseFormatInput) -> str:
    """Get unread article counts per stream (feed, category, tag).

    Use this tool to check which feeds have unread articles before fetching.

    Args:
        params (SimpleResponseFormatInput): Validated input containing:
            - response_format (str): 'markdown' for human-readable or 'json' for machine-readable

    Returns:
        str: Unread counts for each stream, sorted by count descending.

    Examples:
        - Check unread counts: response_format="markdown"
    """
    try:
        client = get_client()
        counts = await client.get_unread_counts()

        if params.response_format == ResponseFormat.JSON:
            return _truncate_response(json.dumps(counts, indent=2))

        return _truncate_response(_format_unread_counts_markdown(counts))
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="feedly_get_stream_contents",
    annotations={
        "title": "Get Stream Contents",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def feedly_get_stream_contents(params: GetStreamContentsInput) -> str:
    """Fetch articles from a Feedly stream (feed, category, or tag).

    Use this tool to retrieve articles for reading and summarization.
    Supports pagination via continuation token.

    Args:
        params (GetStreamContentsInput): Validated input containing:
            - stream_id (str): Stream ID ('feed/URL', 'user/ID/category/label', etc.)
            - count (int): Articles to return, 1-100 (default: 20)
            - unread_only (bool): Only unread articles (default: True)
            - continuation (str): Pagination token
            - ranked (str): Sort order 'newest' or 'oldest'
            - response_format (str): 'markdown' or 'json'

    Returns:
        str: Articles with id, title, author, published date, summary, and URL.
             Includes continuation token if more articles available.

    Examples:
        - Get unread from feed: stream_id="feed/https://example.com/rss"
        - Get all articles: stream_id="user/{id}/category/global.all"
        - Get saved articles: stream_id="user/{id}/tag/global.saved"
    """
    try:
        client = get_client()
        data = await client.get_stream_contents(
            stream_id=params.stream_id,
            count=params.count,
            unread_only=params.unread_only,
            continuation=params.continuation,
            ranked=params.ranked,
        )
        return _truncate_response(_format_stream_contents(data, params.response_format))
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="feedly_get_entry",
    annotations={
        "title": "Get Article Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def feedly_get_entry(params: GetEntryInput) -> str:
    """Get full details for a single article by its entry ID.

    Use this tool to retrieve the complete content of an article for summarization.

    Args:
        params (GetEntryInput): Validated input containing:
            - entry_id (str): Unique entry/article ID
            - response_format (str): 'markdown' or 'json'

    Returns:
        str: Article with full content, title, author, published date, and URL.

    Examples:
        - Get article: entry_id="..."
    """
    try:
        client = get_client()
        entries = await client.get_entry(params.entry_id)

        if not entries:
            return "Error: Article not found."

        entry = entries[0] if isinstance(entries, list) else entries

        if params.response_format == ResponseFormat.JSON:
            return _truncate_response(json.dumps(entry, indent=2))

        return _truncate_response(_format_entry_markdown(entry, include_content=True))
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="feedly_get_entries",
    annotations={
        "title": "Get Multiple Articles",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def feedly_get_entries(params: GetEntriesInput) -> str:
    """Get full details for multiple articles by their entry IDs.

    Use this tool to batch fetch articles for summarization (max 1000).

    Args:
        params (GetEntriesInput): Validated input containing:
            - entry_ids (list[str]): List of entry IDs (max 1000)
            - response_format (str): 'markdown' or 'json'

    Returns:
        str: Articles with full content, title, author, published date, and URL.

    Examples:
        - Get articles: entry_ids=["id1", "id2", "id3"]
    """
    try:
        client = get_client()
        entries = await client.get_entries(params.entry_ids)

        if params.response_format == ResponseFormat.JSON:
            return _truncate_response(json.dumps(entries, indent=2))

        return _truncate_response(_format_entries_markdown(entries, include_content=True))
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="feedly_mark_as_read",
    annotations={
        "title": "Mark Articles as Read",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def feedly_mark_as_read(params: MarkAsReadInput) -> str:
    """Mark articles as read by their entry IDs.

    Use this after processing articles to track progress.

    Args:
        params (MarkAsReadInput): Validated input containing:
            - entry_ids (list[str]): Entry IDs to mark as read (max 1000)

    Returns:
        str: Confirmation message with count of marked entries.

    Examples:
        - Mark as read: entry_ids=["id1", "id2"]
    """
    try:
        client = get_client()
        await client.mark_as_read(params.entry_ids)
        return f"Successfully marked {len(params.entry_ids)} article(s) as read."
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="feedly_mark_feed_as_read",
    annotations={
        "title": "Mark Feed as Read",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def feedly_mark_feed_as_read(params: MarkFeedAsReadInput) -> str:
    """Mark all articles in a feed as read.

    Use this to mark an entire feed as read at once.

    Args:
        params (MarkFeedAsReadInput): Validated input containing:
            - feed_id (str): Feed stream ID (format: 'feed/URL')
            - as_of (int, optional): Mark only entries older than this timestamp (epoch ms)

    Returns:
        str: Confirmation message.

    Examples:
        - Mark feed as read: feed_id="feed/https://example.com/rss"
        - Mark older entries: feed_id="...", as_of=1704067200000
    """
    try:
        client = get_client()
        await client.mark_feed_as_read(params.feed_id, params.as_of)
        msg = f"Successfully marked feed as read: {params.feed_id}"
        if params.as_of:
            msg += f" (entries before {_format_timestamp(params.as_of)})"
        return msg
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="feedly_mark_category_as_read",
    annotations={
        "title": "Mark Category as Read",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def feedly_mark_category_as_read(params: MarkCategoryAsReadInput) -> str:
    """Mark all articles in a category as read.

    Use this to mark an entire category/folder as read at once.

    Args:
        params (MarkCategoryAsReadInput): Validated input containing:
            - category_id (str): Category stream ID (format: 'user/ID/category/label')
            - as_of (int, optional): Mark only entries older than this timestamp (epoch ms)

    Returns:
        str: Confirmation message.

    Examples:
        - Mark category as read: category_id="user/123/category/Tech"
        - Mark older entries: category_id="...", as_of=1704067200000
    """
    try:
        client = get_client()
        await client.mark_category_as_read(params.category_id, params.as_of)
        msg = f"Successfully marked category as read: {params.category_id}"
        if params.as_of:
            msg += f" (entries before {_format_timestamp(params.as_of)})"
        return msg
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="feedly_keep_unread",
    annotations={
        "title": "Keep Articles Unread",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def feedly_keep_unread(params: KeepUnreadInput) -> str:
    """Keep articles unread (undo mark as read).

    Use this to undo marking articles as read.

    Args:
        params (KeepUnreadInput): Validated input containing:
            - entry_ids (list[str]): Entry IDs to keep unread (max 1000)

    Returns:
        str: Confirmation message with count of entries.

    Examples:
        - Keep unread: entry_ids=["id1", "id2"]
    """
    try:
        client = get_client()
        await client.keep_unread(params.entry_ids)
        return f"Successfully kept {len(params.entry_ids)} article(s) as unread."
    except Exception as e:
        return _handle_error(e)


def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
