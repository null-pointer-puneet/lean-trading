"""Minimal LEAN API stubs for offline type checking.

Covers the most common QuantConnect Python API surface (QCAlgorithm, Symbol,
Slice, indicators, ordering helpers, scheduling, etc.). When LEAN CLI is
installed, point your editor's Python interpreter at LEAN's bundled Python
(``lean config get python``) to use the real stubs instead — these are
fallbacks only.
"""
from typing import Any, Callable, Iterable, overload
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Resolution:
    Tick: "Resolution"
    Second: "Resolution"
    Minute: "Resolution"
    Hour: "Resolution"
    Daily: "Resolution"

class DataNormalizationMode:
    Raw: "DataNormalizationMode"
    Adjusted: "DataNormalizationMode"
    SplitAdjusted: "DataNormalizationMode"
    TotalReturn: "DataNormalizationMode"

class SecurityType:
    Equity: "SecurityType"
    Forex: "SecurityType"
    Crypto: "SecurityType"
    Future: "SecurityType"
    Option: "SecurityType"
    Cfd: "SecurityType"

class Market:
    USA: "Market"
    FXCM: "Market"
    Oanda: "Market"
    Bitfinex: "Market"
    Binance: "Market"
    Coinbase: "Market"
    InteractiveBrokers: "Market"

class BrokerageName:
    INTERACTIVE_BROKERS_BROKERAGE: "BrokerageName"
    OANDA_BROKERAGE: "BrokerageName"
    DEFAULT: "BrokerageName"

class AccountType:
    CASH: "AccountType"
    MARGIN: "AccountType"

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class Symbol:
    Value: str
    ID: str
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...
    def __str__(self) -> str: ...
    def __bool__(self) -> bool: ...

class BaseData:
    Symbol: Symbol
    Time: datetime
    EndTime: datetime
    Value: float
    def __init__(self) -> None: ...

class Bar(BaseData):
    Open: float
    High: float
    Low: float
    Close: float
    Volume: float
    def __init__(self) -> None: ...

class TradeBar(Bar):
    def __init__(self) -> None: ...

class QuoteBar(Bar):
    Bid: Bar
    Ask: Bar
    BidSize: float
    AskSize: float
    def __init__(self) -> None: ...

class Slice:
    Time: datetime
    Bars: dict[Symbol, TradeBar]
    QuoteBars: dict[Symbol, QuoteBar]
    def __init__(self) -> None: ...
    def __getitem__(self, symbol: Symbol | str) -> TradeBar | QuoteBar | None: ...
    def __contains__(self, symbol: Symbol | str) -> bool: ...
    def Get(self, symbol: Symbol | str) -> TradeBar | QuoteBar | None: ...
    def ContainsKey(self, symbol: Symbol | str) -> bool: ...
    def Keys(self) -> Iterable[Symbol]: ...
    def Values(self) -> Iterable[TradeBar | QuoteBar]: ...

# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

class OrderStatus:
    New: "OrderStatus"
    Submitted: "OrderStatus"
    PartiallyFilled: "OrderStatus"
    Filled: "OrderStatus"
    Canceled: "OrderStatus"
    CancelPending: "OrderStatus"
    Invalid: "OrderStatus"

class OrderType:
    Market: "OrderType"
    Limit: "OrderType"
    StopMarket: "OrderType"
    MarketOnOpen: "OrderType"
    MarketOnClose: "OrderType"
    LimitIfTouched: "OrderType"

class OrderDirection:
    Buy: "OrderDirection"
    Sell: "OrderDirection"
    Hold: "OrderDirection"

class OrderEvent:
    OrderId: int
    Symbol: Symbol
    Direction: OrderDirection
    FillQuantity: float
    FillPrice: float
    FillQuantityRemaining: float
    FillPriceRemaining: float
    FillCost: float
    FillFee: float
    Status: OrderStatus
    Message: str

class OrderTicket:
    OrderId: int
    Symbol: Symbol
    Quantity: float
    Status: OrderStatus
    OrderType: OrderType
    OrderEvents: list[OrderEvent]
    def Get(self, field: Any) -> Any: ...
    def Cancel(self, message: str = ...) -> None: ...
    def Update(self, *args: Any, **kwargs: Any) -> None: ...

# ---------------------------------------------------------------------------
# Portfolio / Securities
# ---------------------------------------------------------------------------

class SecurityHolding:
    Symbol: Symbol
    Quantity: float
    AveragePrice: float
    Price: float
    UnrealizedProfit: float
    HoldingsCost: float
    MarketValue: float
    Invested: bool
    IsLong: bool
    IsShort: bool
    IsFlat: bool
    def __init__(self) -> None: ...

class Security:
    Symbol: Symbol
    Type: SecurityType
    Resolution: Resolution
    Holdings: SecurityHolding
    Price: float
    Open: float
    High: float
    Low: float
    Close: float
    Volume: float
    HasData: bool
    IsTradable: bool
    def __init__(self) -> None: ...

class SecurityPortfolioManager:
    Cash: float
    TotalPortfolioValue: float
    TotalAbsoluteHoldingsCost: float
    TotalUnrealizedProfit: float
    TotalRealizedProfit: float
    TotalFees: float
    def __getitem__(self, symbol: Symbol | str) -> SecurityHolding: ...
    def ContainsKey(self, symbol: Symbol | str) -> bool: ...
    def Keys(self) -> Iterable[Symbol]: ...
    def Values(self) -> Iterable[SecurityHolding]: ...

# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

class IndicatorDataPoint:
    Time: datetime
    Value: float
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class IndicatorBase:
    Current: IndicatorDataPoint
    IsReady: bool
    Samples: int
    WarmUpPeriod: int
    Name: str
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def Update(self, *args: Any, **kwargs: Any) -> bool: ...
    def Reset(self) -> None: ...

class SimpleMovingAverage(IndicatorBase):
    def __init__(self, period: int) -> None: ...

class ExponentialMovingAverage(IndicatorBase):
    def __init__(self, period: int) -> None: ...

class RelativeStrengthIndex(IndicatorBase):
    def __init__(self, period: int, movingAverageType: Any = ...) -> None: ...

class MovingAverageConvergenceDivergence(IndicatorBase):
    Fast: IndicatorBase
    Slow: IndicatorBase
    Signal: IndicatorBase
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class BollingerBands(IndicatorBase):
    UpperBand: IndicatorBase
    MiddleBand: IndicatorBase
    LowerBand: IndicatorBase
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

class AverageTrueRange(IndicatorBase):
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

# ---------------------------------------------------------------------------
# Scheduling / Settings
# ---------------------------------------------------------------------------

class DateRules:
    def EveryDay(self, symbol: Symbol | str | None = ...) -> Any: ...
    def WeekStart(self, symbol: Symbol | str | None = ...) -> Any: ...
    def MonthStart(self, symbol: Symbol | str | None = ...) -> Any: ...
    def On(self, year: int, month: int, day: int) -> Any: ...
    def Today(self) -> Any: ...

class TimeRules:
    def At(self, hour: int, minute: int = ..., second: int = ...) -> Any: ...
    def AfterMarketOpen(self, symbol: Symbol | str, minutesAfterOpen: int = ...) -> Any: ...
    def BeforeMarketClose(self, symbol: Symbol | str, minutesBeforeClose: int = ...) -> Any: ...
    def Every(self, interval: timedelta) -> Any: ...

class ScheduleManager:
    @overload
    def On(self, dateRule: Any, timeRule: Any, action: Callable[..., Any]) -> ScheduledEvent: ...
    @overload
    def On(self, symbol: Symbol | str, action: Callable[..., Any]) -> ScheduledEvent: ...

class ScheduledEvent: ...

class UniverseSettings:
    Resolution: Resolution
    Leverage: float
    FillForward: bool
    ExtendedMarketHours: bool
    DataNormalizationMode: DataNormalizationMode
    def __init__(self) -> None: ...

class AlgorithmSettings:
    FreePortfolioValue: float
    FreePortfolioValuePercentage: float
    LiquidateWithoutMargin: bool
    def __init__(self) -> None: ...

# ---------------------------------------------------------------------------
# Algorithm
# ---------------------------------------------------------------------------

class QCAlgorithm:
    Time: datetime
    StartDate: datetime
    EndDate: datetime
    Portfolio: SecurityPortfolioManager
    Securities: dict[Symbol, Security]
    UniverseSettings: UniverseSettings
    Settings: AlgorithmSettings
    Schedule: ScheduleManager
    IsWarmingUp: bool
    LiveMode: bool

    def Initialize(self) -> None: ...
    def OnData(self, slice: Slice) -> None: ...
    def OnOrderEvent(self, orderEvent: OrderEvent) -> None: ...
    def OnWarmupFinished(self) -> None: ...
    def OnEndOfAlgorithm(self) -> None: ...
    def OnSecuritiesChanged(self, changes: Any) -> None: ...

    def Debug(self, message: str) -> None: ...
    def Log(self, message: str) -> None: ...
    def Error(self, message: str) -> None: ...
    def Quit(self, message: str = ...) -> None: ...

    def SetStartDate(self, year: int, month: int, day: int) -> None: ...
    def SetEndDate(self, year: int, month: int, day: int) -> None: ...
    def SetCash(self, amount: float) -> None: ...
    def SetBrokerageModel(
        self,
        brokerage: BrokerageName,
        accountType: AccountType = ...,
    ) -> None: ...
    def SetBenchmark(self, ticker: Symbol | str) -> None: ...
    @overload
    def SetWarmup(self, period: int | timedelta) -> None: ...
    @overload
    def SetWarmup(self, barCount: int, resolution: Resolution) -> None: ...

    def AddEquity(
        self,
        ticker: str,
        resolution: Resolution = ...,
        market: Market | str = ...,
        fillDataForward: bool = ...,
        leverage: float = ...,
        extendedMarketHours: bool = ...,
    ) -> Security: ...
    def AddForex(
        self,
        ticker: str,
        resolution: Resolution = ...,
        market: Market | str = ...,
        leverage: float = ...,
        fillDataForward: bool = ...,
    ) -> Security: ...
    def AddCrypto(
        self,
        ticker: str,
        resolution: Resolution = ...,
        market: Market | str = ...,
        leverage: float = ...,
        fillDataForward: bool = ...,
    ) -> Security: ...
    def AddFuture(self, ticker: str, *args: Any, **kwargs: Any) -> Security: ...
    def AddOption(self, ticker: str, *args: Any, **kwargs: Any) -> Security: ...

    def MarketOrder(
        self, symbol: Symbol | str, quantity: float, asynchronous: bool = ..., tag: str = ...
    ) -> OrderTicket: ...
    def LimitOrder(
        self, symbol: Symbol | str, quantity: float, limitPrice: float, tag: str = ...
    ) -> OrderTicket: ...
    def StopMarketOrder(
        self, symbol: Symbol | str, quantity: float, stopPrice: float, tag: str = ...
    ) -> OrderTicket: ...
    def MarketOnOpenOrder(
        self, symbol: Symbol | str, quantity: float, tag: str = ...
    ) -> OrderTicket: ...
    def MarketOnCloseOrder(
        self, symbol: Symbol | str, quantity: float, tag: str = ...
    ) -> OrderTicket: ...
    def LimitIfTouchedOrder(
        self,
        symbol: Symbol | str,
        quantity: float,
        triggerPrice: float,
        limitPrice: float,
        tag: str = ...,
    ) -> OrderTicket: ...
    def Liquidate(self, symbol: Symbol | str | None = ...) -> None: ...
    def SetHoldings(
        self,
        symbol: Symbol | str,
        percentage: float,
        liquidateExistingHoldings: bool = ...,
        tag: str = ...,
    ) -> list[OrderTicket]: ...

    @overload
    def Plot(self, chart: str, series: str, value: float) -> None: ...
    @overload
    def Plot(self, chart: str, value: float) -> None: ...
    def PlotIndicator(self, indicator: IndicatorBase, value: float | None = ...) -> None: ...

    def SMA(
        self, symbol: Symbol | str, period: int, resolution: Resolution | None = ...
    ) -> SimpleMovingAverage: ...
    def EMA(
        self, symbol: Symbol | str, period: int, resolution: Resolution | None = ...
    ) -> ExponentialMovingAverage: ...
    def RSI(
        self,
        symbol: Symbol | str,
        period: int,
        movingAverageType: Any = ...,
        resolution: Resolution | None = ...,
    ) -> RelativeStrengthIndex: ...
    def MACD(
        self,
        symbol: Symbol | str,
        fastPeriod: int = ...,
        slowPeriod: int = ...,
        signalPeriod: int = ...,
        movingAverageType: Any = ...,
        resolution: Resolution | None = ...,
    ) -> MovingAverageConvergenceDivergence: ...
    def BB(
        self,
        symbol: Symbol | str,
        period: int = ...,
        k: float = ...,
        movingAverageType: Any = ...,
        resolution: Resolution | None = ...,
    ) -> BollingerBands: ...
    def ATR(
        self,
        symbol: Symbol | str,
        period: int = ...,
        movingAverageType: Any = ...,
        resolution: Resolution | None = ...,
    ) -> AverageTrueRange: ...

    @overload
    def History(self, symbol: Symbol | str, periods: int, resolution: Resolution | None = ...) -> list[TradeBar]: ...
    @overload
    def History(self, symbols: Iterable[Symbol | str], periods: int, resolution: Resolution | None = ...) -> list[TradeBar]: ...
    @overload
    def History(
        self,
        symbol: Symbol | str,
        start: datetime,
        end: datetime | None = ...,
        resolution: Resolution | None = ...,
    ) -> list[TradeBar]: ...

    def Consolidate(self, *args: Any, **kwargs: Any) -> None: ...
