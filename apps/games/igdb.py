import time
from datetime import date

import httpx
from django.conf import settings


class IGDBClient:
    _token: str | None = None
    _token_expires_at: float = 0.0

    TOKEN_URL = "https://id.twitch.tv/oauth2/token"
    GAMES_URL = "https://api.igdb.com/v4/games"

    FIELDS = (
        "fields name, summary, cover.url, genres.name, "
        "platforms.name, first_release_date, rating, slug;"
    )

    def _get_access_token(self) -> str:
        if IGDBClient._token and time.time() < IGDBClient._token_expires_at - 60:
            return IGDBClient._token
        resp = httpx.post(
            self.TOKEN_URL,
            params={
                "client_id": settings.IGDB_CLIENT_ID,
                "client_secret": settings.IGDB_CLIENT_SECRET,
                "grant_type": "client_credentials",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        IGDBClient._token = data["access_token"]
        IGDBClient._token_expires_at = time.time() + data["expires_in"]
        return IGDBClient._token

    def _headers(self) -> dict:
        return {
            "Client-ID": settings.IGDB_CLIENT_ID,
            "Authorization": f"Bearer {self._get_access_token()}",
        }

    def _normalize(self, raw: dict) -> dict:
        cover_url = ""
        if raw.get("cover"):
            url = raw["cover"]["url"]
            if url.startswith("//"):
                url = "https:" + url
            url = url.replace("t_thumb", "t_cover_big")
            cover_url = url

        release_year = None
        if raw.get("first_release_date"):
            release_year = date.fromtimestamp(raw["first_release_date"]).year

        rating = None
        if raw.get("rating") is not None:
            rating = round(raw["rating"] / 20, 1)

        return {
            "igdb_id": raw["id"],
            "title": raw["name"],
            "slug": raw.get("slug", ""),
            "cover_url": cover_url,
            "summary": raw.get("summary", ""),
            "genres": [g["name"] for g in raw.get("genres", [])],
            "platforms": [p["name"] for p in raw.get("platforms", [])],
            "release_year": release_year,
            "rating": rating,
        }

    def _query(self, body: str) -> list:
        resp = httpx.post(
            self.GAMES_URL,
            headers=self._headers(),
            content=body,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def search(self, query: str, limit: int = 10) -> list[dict]:
        body = f'{self.FIELDS} search "{query}"; limit {limit};'
        return [self._normalize(r) for r in self._query(body)]

    def get_by_id(self, igdb_id: int) -> dict | None:
        body = f"{self.FIELDS} where id = {igdb_id}; limit 1;"
        results = self._query(body)
        return self._normalize(results[0]) if results else None
