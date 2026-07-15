from quantforge_stock.strategies.base import Strategy
class DemoStrategy(Strategy):
    def warmup(self):
        return 20
    def on_bar(self, symbol, bar, history):
        return []
