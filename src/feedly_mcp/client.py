"""Async client for Feedly API."""

from typing import Optional, Any
from urllib.parse import quote
import httpx

from .constants import API_BASE_URL, USER_AGENT


class FeedlyError(Exception):
    """Base exception for Feedly API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class FeedlyClient:
    """Async client for Feedly API."""

    def __init__(
        self, access_token: str, base_url: str = API_BASE_URL, timeout: float = 30.0
    ):
        self.access_token = access_token
        self.base_url = base_url
        self.timeout = timeout

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[Any] = None,
    ) -> Any:
        """Make authenticated request to Feedly API."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                f"{self.base_url}{endpoint}",
                params=params,
                json=json_data,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                },
            )

            if response.status_code == 401:
                raise FeedlyError(
                    "Authentication failed. Check FEEDLY_ACCESS_TOKEN.", 401
                )
            elif response.status_code == 403:
                raise FeedlyError("Access forbidden. Check your Feedly plan.", 403)
            elif response.status_code == 404:
                raise FeedlyError("Resource not found. Check the ID.", 404)
            elif response.status_code == 429:
                raise FeedlyError("Rate limit exceeded. Wait before retrying.", 429)

            response.raise_for_status()

            if response.status_code == 204:
                return None
            return response.json()

    async def get_profile(self) -> dict:
        """Get user profile information including user ID."""
        return await self._request("GET", "/profile")

    async def get_subscriptions(self) -> list[dict]:
        """List all feed subscriptions."""
        return await self._request("GET", "/subscriptions")

    async def get_categories(self) -> list[dict]:
        """List all categories/folders."""
        return await self._request("GET", "/categories")

    async def get_tags(self) -> list[dict]:
        """List all tags."""
        return await self._request("GET", "/tags")

    async def get_unread_counts(self) -> dict:
        """Get unread counts per stream."""
        return await self._request("GET", "/markers/counts")

    async def get_stream_contents(
        self,
        stream_id: str,
        count: int = 20,
        unread_only: bool = True,
        continuation: Optional[str] = None,
        ranked: str = "newest",
    ) -> dict:
        """Fetch articles from a stream (feed, category, or tag).

        Args:
            stream_id: Stream ID to fetch from
            count: Number of articles (1-100)
            unread_only: Only return unread articles
            continuation: Pagination token
            ranked: Sort order ('newest' or 'oldest')

        Returns:
            Dict with 'items' list and optional 'continuation' token
        """
        params = {
            "streamId": stream_id,
            "count": count,
            "ranked": ranked,
        }
        if unread_only:
            params["unreadOnly"] = "true"
        if continuation:
            params["continuation"] = continuation

        return await self._request("GET", "/streams/contents", params=params)

    async def get_entry(self, entry_id: str) -> list[dict]:
        """Get a single article by its entry ID.

        Args:
            entry_id: Unique entry/article ID

        Returns:
            List containing the entry (Feedly API returns array)
        """
        encoded_entry_id = quote(entry_id, safe="")
        return await self._request("GET", f"/entries/{encoded_entry_id}")

    async def get_entries(self, entry_ids: list[str]) -> list[dict]:
        """Get multiple articles by their entry IDs.

        Args:
            entry_ids: List of entry IDs (max 1000)

        Returns:
            List of entries
        """
        return await self._request("POST", "/entries/.mget", json_data=entry_ids)

    async def mark_as_read(self, entry_ids: list[str]) -> None:
        """Mark entries as read.

        Args:
            entry_ids: List of entry IDs to mark as read (max 1000)
        """
        await self._request(
            "POST",
            "/markers",
            json_data={
                "action": "markAsRead",
                "type": "entries",
                "entryIds": entry_ids,
            },
        )

    async def mark_feed_as_read(
        self, feed_id: str, as_of: Optional[int] = None
    ) -> None:
        """Mark an entire feed as read.

        Args:
            feed_id: Feed stream ID (format: 'feed/URL')
            as_of: Mark only entries older than this timestamp (epoch ms)
        """
        data: dict[str, Any] = {
            "action": "markAsRead",
            "type": "feeds",
            "feedIds": [feed_id],
        }
        if as_of is not None:
            data["asOf"] = as_of

        await self._request("POST", "/markers", json_data=data)

    async def mark_category_as_read(
        self, category_id: str, as_of: Optional[int] = None
    ) -> None:
        """Mark an entire category as read.

        Args:
            category_id: Category stream ID (format: 'user/ID/category/label')
            as_of: Mark only entries older than this timestamp (epoch ms)
        """
        data: dict[str, Any] = {
            "action": "markAsRead",
            "type": "categories",
            "categoryIds": [category_id],
        }
        if as_of is not None:
            data["asOf"] = as_of

        await self._request("POST", "/markers", json_data=data)

    async def keep_unread(self, entry_ids: list[str]) -> None:
        """Keep entries unread (undo mark as read).

        Args:
            entry_ids: List of entry IDs to keep unread (max 1000)
        """
        await self._request(
            "POST",
            "/markers",
            json_data={
                "action": "keepUnread",
                "type": "entries",
                "entryIds": entry_ids,
            },
        )
