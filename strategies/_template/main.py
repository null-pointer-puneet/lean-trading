from AlgorithmImports import *


class MyStrategy(QCAlgorithm):
    def Initialize(self) -> None:
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(100_000)

        self.symbol = self.AddEquity("SPY", Resolution.Daily).Symbol

    def OnData(self, slice: Slice) -> None:
        pass
