from datetime import datetime, timezone
from typing import List
import xml.etree.ElementTree as ET
import logging

import httpx
from fastapi import APIRouter, Depends, Query

from api.routes.auth import get_current_user
from models import User

router = APIRouter(prefix="/api/news", tags=["news"])
logger = logging.getLogger(__name__)


@router.get("")
def news_feed(current_user: User = Depends(get_current_user)) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "items": [
            {
                "headline": "Tech stocks rally on easing inflation expectations",
                "source": "Market Wire",
                "timestamp": now,
                "symbols": ["AAPL", "MSFT"],
                "sentiment": "POSITIVE",
                "sentiment_score": 62,
            },
            {
                "headline": "Energy sector dips as crude oil slips",
                "source": "Energy Desk",
                "timestamp": now,
                "symbols": ["XOM"],
                "sentiment": "NEGATIVE",
                "sentiment_score": -48,
            },
            {
                "headline": "Fed minutes hint at steady rates",
                "source": "Macro Insights",
                "timestamp": now,
                "symbols": ["SPY"],
                "sentiment": "NEUTRAL",
                "sentiment_score": 5,
            },
        ]
    }


def _rss_fetch(url: str, headers: dict) -> List[dict]:
    try:
        with httpx.Client(timeout=8.0, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            root = ET.fromstring(response.text)
    except Exception as e:
        logger.warning(f"RSS fetch failed for {url}: {e}")
        return []
    items = []
    for item in root.findall(".//item")[:10]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        pub_date = item.findtext("pubDate") or ""
        items.append({"title": title.strip(), "link": link.strip(), "published": pub_date.strip()})
    return items


@router.get("/catalysts")
def catalysts(
    symbols: str = Query("", description="Comma-separated symbols"),
    current_user: User = Depends(get_current_user),
) -> dict:
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    user_agent = {"User-Agent": "ZellaAI/1.0 (contact: support@zella.ai)"}
    results = []
    for symbol in symbol_list[:10]:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
        items = _rss_fetch(url, user_agent)
        for item in items:
            headline = item.get("title", "")
            catalyst = "OTHER"
            lower = headline.lower()
            if any(word in lower for word in ["earnings", "eps", "guidance"]):
                catalyst = "EARNINGS"
            elif any(word in lower for word in ["fda", "approval", "clinical"]):
                catalyst = "FDA"
            elif any(word in lower for word in ["merger", "acquire", "acquisition", "buyout"]):
                catalyst = "M&A"
            elif any(word in lower for word in ["upgrade", "downgrade", "rating"]):
                catalyst = "ANALYST"
            results.append(
                {
                    "symbol": symbol,
                    "headline": headline,
                    "link": item.get("link", ""),
                    "published": item.get("published", ""),
                    "catalyst": catalyst,
                }
            )
    return {"items": results}
