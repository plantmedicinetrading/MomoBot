class BrokerInterface:
    def get_positions(self):
        raise NotImplementedError

    def get_position(self, symbol):
        raise NotImplementedError

    def submit_order(self, symbol, qty, side, price):
        raise NotImplementedError 