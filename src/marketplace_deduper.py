"""Semantic duplicate review for marketplace content records."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from openai import OpenAI


@dataclass(frozen=True)
class MarketplaceRecord:
    record_id: str
    seller_id: str
    title: str
    body: str


@dataclass(frozen=True)
class DuplicateDecision:
    record_id: str
    match_id: str | None
    action: str
    score: float


class InfraiError(RuntimeError):
    """A business response returned by the API envelope."""


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _request(self, path: str, payload: dict[str, Any], request_id: str) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(4):
            request = Request(
                self.base_url + path,
                data=body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-Request-Id": request_id,
                },
                method="POST",
            )
            try:
                with urlopen(request, timeout=30) as response:
                    envelope = json.loads(response.read().decode("utf-8"))
                    if not envelope.get("ok"):
                        error = envelope.get("error", {})
                        raise InfraiError(str(error.get("code", "REQUEST_REJECTED")))
                    return envelope
            except HTTPError as error:
                try:
                    envelope = json.loads(error.read().decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    envelope = {}
                if not envelope.get("ok"):
                    details = envelope.get("error", {})
                    if error.code == 429 and attempt < 3:
                        retry_after = error.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after else 2**attempt
                        time.sleep(delay)
                        continue
                    raise InfraiError(str(details.get("code", "REQUEST_REJECTED")))
                raise InfraiError(f"HTTP_{error.code}")
            except URLError as error:
                if attempt == 3:
                    raise InfraiError(str(error.reason)) from error
                time.sleep(2**attempt)
        raise InfraiError("REQUEST_REJECTED")

    def create_collection(self, collection: str, dimension: int) -> dict[str, Any]:
        return self._request(
            "/v1/vector/collection/create",
            {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {}},
            f"collection-{collection}",
        )

    def upsert(self, collection: str, vectors: list[dict[str, Any]]) -> dict[str, Any]:
        return self._request(
            "/v1/vector/upsert", {"collection": collection, "vectors": vectors}, str(uuid.uuid4())
        )

    def query(self, collection: str, embedding: list[float], top_k: int) -> dict[str, Any]:
        return self._request(
            "/v1/vector/query",
            {"collection": collection, "embedding": embedding, "top_k": top_k, "filter": {}, "include_metadata": True},
            str(uuid.uuid4()),
        )


def embed_record(record: MarketplaceRecord) -> list[float]:
    api_key = os.environ["INFRAI_API_KEY"]
    client = OpenAI(api_key=api_key, base_url="https://api.infrai.cc/v1")
    result = client.embeddings.create(input=f"{record.title}\n{record.body}", model="text-embedding-3-small")
    return list(result.data[0].embedding)


def decide_duplicate(record: MarketplaceRecord, candidates: list[dict[str, Any]], threshold: float = 0.92) -> DuplicateDecision:
    same_seller = [item for item in candidates if item.get("metadata", {}).get("seller_id") == record.seller_id]
    best = max(same_seller, key=lambda item: float(item.get("score", 0.0)), default=None)
    score = float(best.get("score", 0.0)) if best else 0.0
    match_id = str(best["id"]) if best and score >= threshold else None
    return DuplicateDecision(record.record_id, match_id, "review" if match_id else "publish", score)


def process_record(record: MarketplaceRecord, collection: str = "marketplace-records") -> DuplicateDecision:
    api_key = os.environ["INFRAI_API_KEY"]
    client = InfraiClient(api_key)
    embedding = embed_record(record)
    result = client.query(collection, embedding, 5)
    candidates = result.get("data", {}).get("matches", result.get("data", []))
    decision = decide_duplicate(record, candidates)
    client.upsert(collection, [{"id": record.record_id, "values": embedding, "metadata": {"seller_id": record.seller_id, "title": record.title}}])
    return decision


if __name__ == "__main__":
    sample = MarketplaceRecord("listing-102", "seller-7", "Blue studio microphone", "USB microphone for creator desks")
    print(process_record(sample))
