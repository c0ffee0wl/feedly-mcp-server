"""Constants for Feedly MCP Server."""

API_BASE_URL = "https://cloud.feedly.com/v3"
CHARACTER_LIMIT = 25000  # Max response size
DEFAULT_COUNT = 20  # Default articles per request
MAX_COUNT = 100  # Max articles per request
MAX_BATCH_SIZE = 1000  # Max entries for batch operations

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
