import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.marketplace_deduper import MarketplaceRecord, decide_duplicate


def test_same_seller_near_match_is_sent_to_review():
    record = MarketplaceRecord("new-2", "seller-7", "Blue studio microphone", "USB microphone")
    candidates = [{"id": "old-1", "score": 0.95, "metadata": {"seller_id": "seller-7"}}]

    decision = decide_duplicate(record, candidates)

    assert decision.action == "review"
    assert decision.match_id == "old-1"


def test_other_seller_match_can_publish():
    record = MarketplaceRecord("new-3", "seller-7", "Blue studio microphone", "USB microphone")
    candidates = [{"id": "old-2", "score": 0.99, "metadata": {"seller_id": "seller-8"}}]

    assert decide_duplicate(record, candidates).action == "publish"
