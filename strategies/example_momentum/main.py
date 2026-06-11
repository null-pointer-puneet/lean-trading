from AlgorithmImports import *


class MomentumSmaCross(QCAlgorithm):
    def Initialize(self) -> None:
        self.SetStartDate(2015, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(100_000)

        self.symbol = self.AddEquity("SPY", Resolution.Daily).Symbol
        self.fast = self.SMA(self.symbol, 20, Resolution.Daily)
        self.slow = self.SMA(self.symbol, 100, Resolution.Daily)

        self.SetWarmup(100)

    def OnData(self, slice: Slice) -> None:
        if self.IsWarmingUp:
            return
        if not self.fast.IsReady or not self.slow.IsReady:
            return

        fast = self.fast.Current.Value
        slow = self.slow.Current.Value

        if fast > slow and not self.Portfolio[self.symbol].Invested:
            self.SetHoldings(self.symbol, 1.0)
        elif fast < slow and self.Portfolio[self.symbol].Invested:
            self.Liquidate(self.symbol)
