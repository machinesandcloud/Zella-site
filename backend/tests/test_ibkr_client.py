from core.ibkr_client import IBKRClient


def test_ibkr_client_initial_state():
    client = IBKRClient()
    assert client.get_trading_mode() == "PAPER"
    assert client.is_connected() is False
