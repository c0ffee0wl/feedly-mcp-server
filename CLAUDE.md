# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python MCP (Model Context Protocol) server that enables Claude to interact with the Feedly API. It provides 12 tools for reading feeds, fetching articles, and marking items as read.

## Development Commands

```bash
# Install in development mode
uv tool install -e .

# Syntax check
uv run python -m py_compile src/feedly_mcp/server.py

# Run the server
feedly-mcp

# Test with MCP Inspector
npx @modelcontextprotocol/inspector
```

## Architecture

```
src/feedly_mcp/
├── server.py      # FastMCP server - all 12 tools defined here with @mcp.tool decorators
├── client.py      # FeedlyClient - async httpx client for Feedly API
├── models.py      # Pydantic v2 input models for tool parameters
└── constants.py   # API URL, limits, User-Agent
```

**Key patterns:**
- Tools use Pydantic models for input validation (e.g., `GetStreamContentsInput`)
- All API calls go through `FeedlyClient._request()` which handles auth and error mapping
- Response formatting supports both markdown and JSON via `ResponseFormat` enum
- Tool annotations specify `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`

## Feedly API

**Base URL:** `https://cloud.feedly.com/v3`

**Authentication:** Bearer token via `FEEDLY_ACCESS_TOKEN` environment variable

**Stream ID formats:**
- Feed: `feed/https://example.com/rss`
- Category: `user/{userId}/category/{label}`
- Tag: `user/{userId}/tag/global.saved`

## Tools (12 total)

**Read-only (8):** `feedly_get_profile`, `feedly_get_subscriptions`, `feedly_get_categories`, `feedly_get_tags`, `feedly_get_unread_counts`, `feedly_get_stream_contents`, `feedly_get_entry`, `feedly_get_entries`

**Write (4):** `feedly_mark_as_read`, `feedly_mark_feed_as_read`, `feedly_mark_category_as_read`, `feedly_keep_unread`
