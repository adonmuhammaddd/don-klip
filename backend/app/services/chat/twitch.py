from typing import Any

import httpx

from app.services.chat.base import ChatFetcher, ChatMessage
from app.services.errors import ChatError

GQL_URL = "https://gql.twitch.tv/gql"
# Persisted query hash untuk operation VideoCommentsByOffsetOrCursor (§5.3).
# Endpoint unofficial — kalau berubah, ganti di sini saja (adapter, §14).
PERSISTED_HASH = "b70a3591ff0f4e0313d126c6a1502d79a1c02baebb288227c582044aa76adf6a"


def parse_comments(comments: dict[str, Any]) -> list[ChatMessage]:
    """Parse blok `comments` dari respons GQL jadi list ChatMessage (pure, testable)."""
    messages: list[ChatMessage] = []
    for edge in comments.get("edges", []):
        node = edge.get("node", {})
        offset = node.get("contentOffsetSeconds")
        if offset is None:
            continue
        fragments = node.get("message", {}).get("fragments", []) or []
        text = "".join(str(f.get("text") or "") for f in fragments)
        emotes = sum(1 for f in fragments if f.get("emote"))
        messages.append(ChatMessage(offset_seconds=float(offset), text=text, emote_count=emotes))
    return messages


class TwitchChatFetcher(ChatFetcher):
    """Ambil chat replay Twitch VOD via GQL (Client-ID public, tanpa OAuth user)."""

    def __init__(self, client_id: str, max_messages: int = 50_000) -> None:
        self._client_id = client_id
        self._max_messages = max_messages

    async def fetch(self, video_id: str) -> list[ChatMessage]:
        messages: list[ChatMessage] = []
        cursor: str | None = None
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                while True:
                    comments = await self._page(client, video_id, cursor)
                    messages.extend(parse_comments(comments))
                    page_info = comments.get("pageInfo", {})
                    edges = comments.get("edges", [])
                    if not page_info.get("hasNextPage") or not edges:
                        break
                    if len(messages) >= self._max_messages:
                        break
                    cursor = edges[-1].get("cursor")
                    if cursor is None:
                        break
        except httpx.HTTPError as exc:
            raise ChatError(f"gagal ambil chat Twitch: {exc}") from exc
        return messages

    async def _page(
        self, client: httpx.AsyncClient, video_id: str, cursor: str | None
    ) -> dict[str, Any]:
        variables: dict[str, Any] = {"videoID": video_id}
        if cursor is None:
            variables["contentOffsetSeconds"] = 0
        else:
            variables["cursor"] = cursor
        body = [
            {
                "operationName": "VideoCommentsByOffsetOrCursor",
                "variables": variables,
                "extensions": {"persistedQuery": {"version": 1, "sha256Hash": PERSISTED_HASH}},
            }
        ]
        resp = await client.post(GQL_URL, json=body, headers={"Client-ID": self._client_id})
        resp.raise_for_status()
        data: Any = resp.json()
        try:
            return dict(data[0]["data"]["video"]["comments"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ChatError(f"format respons Twitch GQL tak terduga: {exc}") from exc
