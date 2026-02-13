from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from api.routes.auth import get_current_user
from models import User

router = APIRouter(prefix="/api/news", tags=["news"])


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
