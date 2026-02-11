export type AccountSummary = {
  accountValue?: number;
  cashBalance?: number;
  buyingPower?: number;
  dailyPnl?: number;
};

export type Position = {
  symbol: string;
  quantity: number;
  entryPrice?: number;
  currentPrice?: number;
  unrealizedPnl?: number;
  stopLoss?: number;
  takeProfit?: number;
};

export type Trade = {
  symbol: string;
  action: string;
  quantity: number;
  pnl?: number;
  entryTime?: string;
};

export type StrategyPerformance = {
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  totalPnl: number;
};
