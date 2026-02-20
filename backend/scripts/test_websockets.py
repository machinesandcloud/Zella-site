#!/usr/bin/env python3
"""
WebSocket Endpoint Validation Script
Tests the enhanced WebSocket endpoints for real-time market data streaming.

Usage:
    python scripts/test_websockets.py [--host localhost] [--port 8000]
"""

import asyncio
import json
import sys
from datetime import datetime

try:
    import websockets
except ImportError:
    print("Installing websockets package...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets


async def test_live_ticker(host: str, port: int, duration: int = 5):
    """Test /ws/live-ticker endpoint"""
    uri = f"ws://{host}:{port}/ws/live-ticker?symbols=AAPL,TSLA,NVDA"
    print(f"\n{'='*60}")
    print(f"Testing: /ws/live-ticker")
    print(f"URI: {uri}")
    print(f"Duration: {duration}s")
    print(f"{'='*60}")

    try:
        async with websockets.connect(uri) as ws:
            start = datetime.now()
            msg_count = 0

            while (datetime.now() - start).seconds < duration:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(msg)
                    msg_count += 1

                    if data.get("type") == "subscribed":
                        print(f"  [SUBSCRIBED] Symbols: {data.get('symbols')}")
                        print(f"  [SUBSCRIBED] Interval: {data.get('interval_ms')}ms")
                    elif data.get("type") == "update":
                        tickers = data.get("data", [])
                        print(f"  [UPDATE #{msg_count}] {len(tickers)} tickers at {data.get('timestamp')}")
                        for t in tickers[:3]:  # Show first 3
                            direction = "↑" if t.get("direction") == "up" else "↓" if t.get("direction") == "down" else "→"
                            print(f"    {t.get('symbol')}: ${t.get('price'):.2f} {direction} ({t.get('change_pct'):+.2f}%)")
                except asyncio.TimeoutError:
                    print("  [TIMEOUT] No message received in 2s")

            print(f"\n  ✓ Received {msg_count} messages in {duration}s")
            return True
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False


async def test_market_data(host: str, port: int, duration: int = 3):
    """Test /ws/market-data endpoint"""
    uri = f"ws://{host}:{port}/ws/market-data?symbols=AAPL,MSFT&interval=0.5"
    print(f"\n{'='*60}")
    print(f"Testing: /ws/market-data")
    print(f"URI: {uri}")
    print(f"Duration: {duration}s")
    print(f"{'='*60}")

    try:
        async with websockets.connect(uri) as ws:
            start = datetime.now()
            msg_count = 0

            while (datetime.now() - start).seconds < duration:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(msg)
                    msg_count += 1

                    if data.get("type") == "batch":
                        batch = data.get("data", [])
                        print(f"  [BATCH #{msg_count}] {len(batch)} symbols at {data.get('timestamp')}")
                        for item in batch:
                            print(f"    {item.get('symbol')}: ${item.get('price', 0):.2f} (bid: ${item.get('bid', 0):.2f}, ask: ${item.get('ask', 0):.2f})")
                except asyncio.TimeoutError:
                    print("  [TIMEOUT] No message received in 2s")

            print(f"\n  ✓ Received {msg_count} messages in {duration}s")
            return True
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False


async def test_bot_activity(host: str, port: int, duration: int = 3):
    """Test /ws/bot-activity endpoint"""
    uri = f"ws://{host}:{port}/ws/bot-activity"
    print(f"\n{'='*60}")
    print(f"Testing: /ws/bot-activity")
    print(f"URI: {uri}")
    print(f"Duration: {duration}s")
    print(f"{'='*60}")

    try:
        async with websockets.connect(uri) as ws:
            start = datetime.now()
            msg_count = 0

            while (datetime.now() - start).seconds < duration:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(msg)
                    msg_count += 1

                    msg_type = data.get("type")
                    if msg_type == "connected":
                        print(f"  [CONNECTED] Bot activity stream connected")
                    elif msg_type == "status":
                        status = data.get("data", {})
                        print(f"  [STATUS #{msg_count}]")
                        print(f"    Running: {status.get('running')}")
                        print(f"    Mode: {status.get('mode')}")
                        print(f"    Symbols Scanned: {status.get('symbols_scanned', 0)}")
                        print(f"    Opportunities: {status.get('opportunities_found', 0)}")
                        top_picks = status.get("top_picks", [])
                        if top_picks:
                            print(f"    Top Picks: {[p.get('symbol') for p in top_picks[:3]]}")
                        if status.get("new_scan"):
                            print(f"    [NEW SCAN DETECTED]")
                    elif msg_type == "error":
                        print(f"  [ERROR] {data.get('message')}")
                except asyncio.TimeoutError:
                    print("  [TIMEOUT] No message received in 2s")

            print(f"\n  ✓ Received {msg_count} messages in {duration}s")
            return True
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test WebSocket endpoints")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  WEBSOCKET ENDPOINT VALIDATION")
    print(f"  Server: {args.host}:{args.port}")
    print("="*60)

    results = {}

    # Test each endpoint
    results["live-ticker"] = await test_live_ticker(args.host, args.port)
    results["market-data"] = await test_market_data(args.host, args.port)
    results["bot-activity"] = await test_bot_activity(args.host, args.port)

    # Summary
    print("\n" + "="*60)
    print("  VALIDATION SUMMARY")
    print("="*60)

    all_passed = True
    for endpoint, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  /ws/{endpoint}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("  All WebSocket endpoints validated successfully!")
    else:
        print("  Some endpoints failed. Check server logs.")
    print("="*60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
