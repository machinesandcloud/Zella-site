import logging
import threading
import time
from typing import Any, Dict, List, Optional

try:
    from ibapi.client import EClient
    from ibapi.contract import Contract
    from ibapi.order import Order
    from ibapi.scanner import ScannerSubscription
    from ibapi.wrapper import EWrapper
    IBAPI_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    IBAPI_AVAILABLE = False

    class EWrapper:  # type: ignore
        pass

    def _ibapi_unavailable(*args, **kwargs) -> None:
        raise RuntimeError(
            "IBKR API placeholder: install 'ibapi' and disable USE_MOCK_IBKR to enable live connectivity."
        )

    class EClient:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            return None

        def connect(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

        def run(self) -> None:
            _ibapi_unavailable()

        def isConnected(self) -> bool:
            return False

        def reqAccountSummary(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

        def cancelAccountSummary(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

        def reqPositions(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

        def cancelPositions(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

        def reqRealTimeBars(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

        def reqMktData(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

        def reqHistoricalData(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

        def reqScannerSubscription(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

        def cancelScannerSubscription(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

        def cancelMktData(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

        def placeOrder(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

        def cancelOrder(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

        def reqOpenOrders(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

        def reqGlobalCancel(self, *args, **kwargs) -> None:
            _ibapi_unavailable()

    class Contract:  # type: ignore
        pass

    class Order:  # type: ignore
        pass

    class ScannerSubscription:  # type: ignore
        pass


class IBKRClient(EWrapper, EClient):
    def __init__(self) -> None:
        EClient.__init__(self, self)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._api_available = IBAPI_AVAILABLE
        self._connected_event = threading.Event()
        self._next_order_id: Optional[int] = None
        self._order_id_lock = threading.Lock()
        self._req_id = 1
        self._req_id_lock = threading.Lock()
        self._account_summary: Dict[str, Any] = {}
        self._positions: List[Dict[str, Any]] = []
        self._open_orders: Dict[int, Dict[str, Any]] = {}
        self._order_status: Dict[int, Dict[str, Any]] = {}
        self._paper_trading_mode = True
        self._thread: Optional[threading.Thread] = None

        self._account_event = threading.Event()
        self._positions_event = threading.Event()
        self._historical_data: Dict[int, List[Dict[str, Any]]] = {}
        self._historical_events: Dict[int, threading.Event] = {}
        self._historical_lock = threading.Lock()
        self._scanner_results: Dict[int, List[str]] = {}
        self._scanner_events: Dict[int, threading.Event] = {}

    # --- Connection management ---
    def connect_to_ibkr(self, host: str, port: int, client_id: int, is_paper_trading: bool) -> bool:
        if not self._api_available:
            self.logger.error("IBKR API not installed. Running in placeholder mode.")
            return False
        self._paper_trading_mode = is_paper_trading
        self.logger.info("Connecting to IBKR %s:%s client_id=%s", host, port, client_id)
        self.connect(host, port, client_id)

        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self.run, daemon=True)
            self._thread.start()

        connected = self._connected_event.wait(timeout=5)
        if not connected:
            self.logger.error("Failed to connect to IBKR within timeout")
        return connected

    def disconnect(self) -> None:
        self.logger.info("Disconnecting from IBKR")
        try:
            super().disconnect()
        finally:
            self._connected_event.clear()

    def is_connected(self) -> bool:
        return self.isConnected()

    def reconnect_with_retry(self, host: str, port: int, client_id: int, retries: int = 5) -> bool:
        for attempt in range(1, retries + 1):
            self.logger.info("Reconnect attempt %s/%s", attempt, retries)
            if self.connect_to_ibkr(host, port, client_id, self._paper_trading_mode):
                return True
            time.sleep(min(2 ** attempt, 30))
        return False

    # --- Account management ---
    def get_account_summary(self) -> Dict[str, Any]:
        self._account_summary = {}
        self._account_event.clear()
        req_id = self._next_req_id()
        self.reqAccountSummary(req_id, "All", "$LEDGER")
        self._account_event.wait(timeout=3)
        self.cancelAccountSummary(req_id)
        return self._account_summary

    def get_positions(self) -> List[Dict[str, Any]]:
        self._positions = []
        self._positions_event.clear()
        self.reqPositions()
        self._positions_event.wait(timeout=3)
        self.cancelPositions()
        return self._positions

    def get_cash_balance(self) -> float:
        value = self._account_summary.get("CashBalance") or 0
        return float(value)

    def get_buying_power(self) -> float:
        value = self._account_summary.get("BuyingPower") or 0
        return float(value)

    # --- Market data ---
    def subscribe_real_time_bars(self, symbol: str, bar_size: int, what_to_show: str) -> int:
        contract = self._stock_contract(symbol)
        req_id = self._next_req_id()
        self.reqRealTimeBars(req_id, contract, bar_size, what_to_show, True, [])
        return req_id

    def subscribe_market_data(self, symbol: str) -> int:
        contract = self._stock_contract(symbol)
        req_id = self._next_req_id()
        self.reqMktData(req_id, contract, "", False, False, [])
        return req_id

    def get_historical_data(self, symbol: str, duration: str, bar_size: str, what_to_show: str) -> int:
        contract = self._stock_contract(symbol)
        req_id = self._next_req_id()
        with self._historical_lock:
            self._historical_data[req_id] = []
            self._historical_events[req_id] = threading.Event()
        self.reqHistoricalData(
            req_id,
            contract,
            "",
            duration,
            bar_size,
            what_to_show,
            1,
            1,
            False,
            [],
        )
        return req_id

    def fetch_historical_data(
        self, symbol: str, duration: str, bar_size: str, what_to_show: str = "TRADES", timeout: int = 10
    ) -> List[Dict[str, Any]]:
        req_id = self.get_historical_data(symbol, duration, bar_size, what_to_show)
        event = self._historical_events.get(req_id)
        if event:
            event.wait(timeout=timeout)
        with self._historical_lock:
            data = self._historical_data.pop(req_id, [])
            self._historical_events.pop(req_id, None)
        return data

    def scan_top_movers(
        self,
        scan_code: str = "TOP_PERC_GAIN",
        location_code: str = "STK.US.MAJOR",
        instrument: str = "STK",
        rows: int = 25,
        timeout: int = 5,
    ) -> List[str]:
        req_id = self._next_req_id()
        event = threading.Event()
        self._scanner_results[req_id] = []
        self._scanner_events[req_id] = event
        sub = ScannerSubscription()
        sub.instrument = instrument
        sub.locationCode = location_code
        sub.scanCode = scan_code
        sub.numberOfRows = rows
        self.reqScannerSubscription(req_id, sub, [], [])
        event.wait(timeout=timeout)
        self.cancelScannerSubscription(req_id)
        return self._scanner_results.pop(req_id, [])

    def unsubscribe_market_data(self, req_id: int) -> None:
        self.cancelMktData(req_id)

    # --- Order management ---
    def place_market_order(self, symbol: str, quantity: int, action: str, contract_params: Optional[Dict[str, Any]] = None) -> int:
        order = Order()
        order.action = action
        order.orderType = "MKT"
        order.totalQuantity = quantity
        return self._place_order(symbol, order, contract_params)

    def place_limit_order(
        self,
        symbol: str,
        quantity: int,
        action: str,
        limit_price: float,
        contract_params: Optional[Dict[str, Any]] = None,
    ) -> int:
        order = Order()
        order.action = action
        order.orderType = "LMT"
        order.totalQuantity = quantity
        order.lmtPrice = limit_price
        return self._place_order(symbol, order, contract_params)

    def place_stop_order(
        self,
        symbol: str,
        quantity: int,
        action: str,
        stop_price: float,
        contract_params: Optional[Dict[str, Any]] = None,
    ) -> int:
        order = Order()
        order.action = action
        order.orderType = "STP"
        order.totalQuantity = quantity
        order.auxPrice = stop_price
        return self._place_order(symbol, order, contract_params)

    def place_bracket_order(
        self,
        symbol: str,
        quantity: int,
        action: str,
        take_profit: float,
        stop_loss: float,
        contract_params: Optional[Dict[str, Any]] = None,
    ) -> List[int]:
        parent_id = self._next_order_id_safe()

        parent = Order()
        parent.orderId = parent_id
        parent.action = action
        parent.orderType = "MKT"
        parent.totalQuantity = quantity
        parent.transmit = False

        take_profit_order = Order()
        take_profit_order.orderId = parent_id + 1
        take_profit_order.action = "SELL" if action == "BUY" else "BUY"
        take_profit_order.orderType = "LMT"
        take_profit_order.totalQuantity = quantity
        take_profit_order.lmtPrice = take_profit
        take_profit_order.parentId = parent_id
        take_profit_order.transmit = False

        stop_loss_order = Order()
        stop_loss_order.orderId = parent_id + 2
        stop_loss_order.action = "SELL" if action == "BUY" else "BUY"
        stop_loss_order.orderType = "STP"
        stop_loss_order.auxPrice = stop_loss
        stop_loss_order.totalQuantity = quantity
        stop_loss_order.parentId = parent_id
        stop_loss_order.transmit = True

        contract = self._build_contract(symbol, **(contract_params or {}))
        self.placeOrder(parent.orderId, contract, parent)
        self.placeOrder(take_profit_order.orderId, contract, take_profit_order)
        self.placeOrder(stop_loss_order.orderId, contract, stop_loss_order)

        return [parent_id, parent_id + 1, parent_id + 2]

    def cancel_order(self, order_id: int) -> None:
        self.cancelOrder(order_id)

    def modify_order(self, order_id: int, new_params: Dict[str, Any]) -> None:
        order = Order()
        for key, value in new_params.items():
            setattr(order, key, value)
        contract = self._build_contract(
            new_params.get("symbol", ""),
            sec_type=(new_params.get("asset_type") or "STK"),
            exchange=new_params.get("exchange") or "SMART",
            currency=new_params.get("currency") or "USD",
            expiry=new_params.get("expiry"),
            strike=new_params.get("strike"),
            right=new_params.get("right"),
            multiplier=new_params.get("multiplier"),
        )
        self.placeOrder(order_id, contract, order)

    def get_open_orders(self) -> Dict[int, Dict[str, Any]]:
        self.reqOpenOrders()
        return self._open_orders

    def close_position(self, symbol: str) -> None:
        positions = self.get_positions()
        for pos in positions:
            if pos.get("symbol") != symbol:
                continue
            qty = pos.get("position", 0)
            if qty == 0:
                return
            action = "SELL" if qty > 0 else "BUY"
            self.place_market_order(symbol, abs(int(qty)), action)
            return

    def get_order_status(self, order_id: int) -> Dict[str, Any]:
        return self._order_status.get(order_id, {})

    def set_paper_trading_mode(self, enable: bool) -> None:
        self._paper_trading_mode = enable

    def get_trading_mode(self) -> str:
        return "PAPER" if self._paper_trading_mode else "LIVE"

    def api_available(self) -> bool:
        return self._api_available

    def kill_switch(self) -> None:
        self.logger.critical("Kill switch activated. Cancelling orders and closing positions.")
        try:
            self.reqGlobalCancel()
            positions = self.get_positions()
            for pos in positions:
                qty = pos.get("position", 0)
                symbol = pos.get("symbol")
                if not symbol or qty == 0:
                    continue
                action = "SELL" if qty > 0 else "BUY"
                self.place_market_order(symbol, abs(int(qty)), action)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.error("Kill switch failed: %s", exc)

    # --- Helpers ---
    def _place_order(self, symbol: str, order: Order, contract_params: Optional[Dict[str, Any]] = None) -> int:
        order_id = self._next_order_id_safe()
        contract = self._build_contract(symbol, **(contract_params or {}))
        self.placeOrder(order_id, contract, order)
        return order_id

    def _stock_contract(self, symbol: str) -> Contract:
        return self._build_contract(symbol)

    def _build_contract(
        self,
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        expiry: Optional[str] = None,
        strike: Optional[float] = None,
        right: Optional[str] = None,
        multiplier: Optional[str] = None,
    ) -> Contract:
        contract = Contract()
        contract.symbol = symbol
        contract.secType = sec_type
        contract.exchange = exchange
        contract.currency = currency
        if sec_type in {"OPT", "FUT"} and expiry:
            contract.lastTradeDateOrContractMonth = expiry
        if sec_type == "OPT":
            if strike is not None:
                contract.strike = float(strike)
            if right is not None:
                contract.right = right
            contract.multiplier = multiplier or "100"
        if sec_type == "FUT" and multiplier:
            contract.multiplier = multiplier
        return contract

    def _next_req_id(self) -> int:
        with self._req_id_lock:
            req_id = self._req_id
            self._req_id += 1
        return req_id

    def _next_order_id_safe(self) -> int:
        with self._order_id_lock:
            if self._next_order_id is None:
                self._next_order_id = 1
            order_id = self._next_order_id
            self._next_order_id += 1
        return order_id

    # --- EWrapper overrides ---
    def nextValidId(self, orderId: int) -> None:  # pylint: disable=invalid-name
        self._next_order_id = orderId
        self._connected_event.set()
        self.logger.info("Connected. Next order id: %s", orderId)

    def error(self, reqId: int, errorCode: int, errorString: str) -> None:  # pylint: disable=invalid-name
        self.logger.error("IBKR error reqId=%s code=%s msg=%s", reqId, errorCode, errorString)

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str) -> None:  # pylint: disable=invalid-name
        self._account_summary[tag] = value

    def accountSummaryEnd(self, reqId: int) -> None:  # pylint: disable=invalid-name
        self._account_event.set()

    def position(self, account: str, contract: Contract, position: float, avgCost: float) -> None:  # pylint: disable=invalid-name
        self._positions.append(
            {
                "account": account,
                "symbol": contract.symbol,
                "position": position,
                "avg_cost": avgCost,
            }
        )

    def positionEnd(self) -> None:  # pylint: disable=invalid-name
        self._positions_event.set()

    def openOrder(self, orderId: int, contract: Contract, order: Order, orderState) -> None:  # pylint: disable=invalid-name
        self._open_orders[orderId] = {
            "symbol": contract.symbol,
            "action": order.action,
            "order_type": order.orderType,
            "quantity": order.totalQuantity,
        }

    def orderStatus(
        self,
        orderId: int,
        status: str,
        filled: float,
        remaining: float,
        avgFillPrice: float,
        permId: int,
        parentId: int,
        lastFillPrice: float,
        clientId: int,
        whyHeld: str,
        mktCapPrice: float,
    ) -> None:  # pylint: disable=invalid-name
        self._order_status[orderId] = {
            "status": status,
            "filled": filled,
            "remaining": remaining,
            "avg_fill_price": avgFillPrice,
            "last_fill_price": lastFillPrice,
        }

    def connectionClosed(self) -> None:  # pylint: disable=invalid-name
        self._connected_event.clear()
        self.logger.warning("IBKR connection closed")

    def historicalData(self, reqId: int, bar) -> None:  # pylint: disable=invalid-name
        payload = {
            "date": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        with self._historical_lock:
            if reqId in self._historical_data:
                self._historical_data[reqId].append(payload)

    def historicalDataEnd(self, reqId: int, start: str, end: str) -> None:  # pylint: disable=invalid-name
        event = self._historical_events.get(reqId)
        if event:
            event.set()

    def scannerData(self, reqId: int, rank: int, contractDetails, distance, benchmark, projection, legsStr) -> None:  # pylint: disable=invalid-name
        if reqId in self._scanner_results:
            self._scanner_results[reqId].append(contractDetails.contract.symbol)

    def scannerDataEnd(self, reqId: int) -> None:  # pylint: disable=invalid-name
        event = self._scanner_events.get(reqId)
        if event:
            event.set()


def ibkr_api_available() -> bool:
    return IBAPI_AVAILABLE
