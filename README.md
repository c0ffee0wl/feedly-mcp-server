# Feedly MCP Server

An MCP (Model Context Protocol) server that enables Claude to interact with Feedly for reading feeds, getting article summaries, and marking items as read.

## Features

- **List subscriptions** - Browse all your feed subscriptions
- **Get unread counts** - Check which feeds have unread articles
- **Fetch articles** - Retrieve articles from feeds, categories, or tags
- **Get article details** - Fetch full content for summarization
- **Mark as read** - Mark articles, feeds, or categories as read
- **Keep unread** - Undo marking articles as read

## Installation

### Prerequisites

- Python 3.10 or higher
- A Feedly account with API access
- Feedly API access token from https://feedly.com/i/team/api

### Install with uv

```bash
uv tool install git+https://github.com/c0ffee0wl/feedly-mcp-server.git
```

### Install from source

```bash
git clone https://github.com/c0ffee0wl/feedly-mcp-server.git
cd feedly-mcp-server
uv tool install -e .
```

## Configuration

### Claude Code Integration

Add to your Claude Code MCP configuration (`~/.config/claude/mcp.json`):

```json
{
  "mcpServers": {
    "feedly": {
      "command": "feedly-mcp",
      "env": {
        "FEEDLY_ACCESS_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Available Tools

### Read-only Tools

| Tool | Description |
|------|-------------|
| `feedly_get_profile` | Get user profile and ID |
| `feedly_get_subscriptions` | List all feed subscriptions |
| `feedly_get_categories` | List categories/folders |
| `feedly_get_tags` | List tags |
| `feedly_get_unread_counts` | Unread counts per stream |
| `feedly_get_stream_contents` | Fetch articles from stream |
| `feedly_get_entry` | Get single article details |
| `feedly_get_entries` | Get multiple articles (batch) |

### Write Tools

| Tool | Description |
|------|-------------|
| `feedly_mark_as_read` | Mark entries as read |
| `feedly_mark_feed_as_read` | Mark entire feed as read |
| `feedly_mark_category_as_read` | Mark category as read |
| `feedly_keep_unread` | Undo mark as read |

## Usage Examples

### Typical Workflow

1. **Get your user ID** (needed for category/tag stream IDs):
   ```
   Use feedly_get_profile to get your user ID
   ```

2. **Check unread counts**:
   ```
   Use feedly_get_unread_counts to see which feeds have unread articles
   ```

3. **Fetch articles from a feed**:
   ```
   Use feedly_get_stream_contents with stream_id="feed/https://example.com/rss"
   ```

4. **Get full article content for summarization**:
   ```
   Use feedly_get_entry with entry_id="..." to get full content
   ```

5. **Mark processed articles as read**:
   ```
   Use feedly_mark_as_read with entry_ids=["id1", "id2"]
   ```

### Stream ID Formats

- **Feed**: `feed/https://example.com/rss`
- **Category**: `user/{userId}/category/{label}`
- **Tag**: `user/{userId}/tag/{label}`
- **All articles**: `user/{userId}/category/global.all`
- **Saved articles**: `user/{userId}/tag/global.saved`

## Response Formats

All tools support two response formats:

- **markdown** (default): Human-readable formatted output
- **json**: Machine-readable JSON output

Set via the `response_format` parameter.

## Development

```bash
# Install in development mode
git clone https://github.com/c0ffee0wl/feedly-mcp-server.git
cd feedly-mcp-server
uv tool install -e .

# Syntax check
uv run python -m py_compile src/feedly_mcp/server.py

# Run the server directly
feedly-mcp

# Test with MCP Inspector
npx @modelcontextprotocol/inspector
```

## Error Handling

The server returns actionable error messages:

| Error | Message |
|-------|---------|
| 401 | "Authentication failed. Check FEEDLY_ACCESS_TOKEN." |
| 403 | "Access forbidden. Check your Feedly plan." |
| 404 | "Resource not found. Check the ID." |
| 429 | "Rate limit exceeded. Wait before retrying." |
| Timeout | "Request timed out. Try again." |

## License

MIT License
