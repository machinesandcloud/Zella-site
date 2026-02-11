from core.risk_manager import RiskConfig, RiskManager


def test_position_size_limit():
    config = RiskConfig(10, 500, 5, 2)
    rm = RiskManager(config)
    assert rm.check_position_size_limit("AAPL", 10, 100, 20000) is True
    assert rm.check_position_size_limit("AAPL", 10, 1000, 20000) is False


def test_position_sizing():
    config = RiskConfig(10, 500, 5, 2)
    rm = RiskManager(config)
    size = rm.calculate_position_size("AAPL", 2, 1.0, 10000)
    assert size > 0
