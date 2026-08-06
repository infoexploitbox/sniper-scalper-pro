import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict
import config

class MT5Connector:
    def __init__(self):
        self.connected = False
        
    def connect(self) -> bool:
        """Connect to MT5 terminal"""
        if not mt5.initialize():
            print(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        
        if config.MT5_LOGIN and config.MT5_PASSWORD and config.MT5_SERVER:
            authorized = mt5.login(
                login=config.MT5_LOGIN,
                password=config.MT5_PASSWORD,
                server=config.MT5_SERVER
            )
            if not authorized:
                print(f"MT5 login failed: {mt5.last_error()}")
                mt5.shutdown()
                return False
        
        self.connected = True
        print(f"Connected to MT5. Account: {mt5.account_info().login}")
        return True
    
    def disconnect(self):
        """Disconnect from MT5"""
        mt5.shutdown()
        self.connected = False
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account information"""
        if not self.connected:
            return None
        
        account = mt5.account_info()
        if account is None:
            return None
        
        return {
            "login": account.login,
            "server": account.server,
            "balance": account.balance,
            "equity": account.equity,
            "margin": account.margin,
            "free_margin": account.margin_free,
            "margin_level": account.margin_level,
            "profit": account.profit,
            "currency": account.currency,
            "leverage": account.leverage,
            "name": account.name,
            "company": account.company
        }
    
    def get_positions(self) -> List[Dict]:
        """Get open positions"""
        if not self.connected:
            return []
        
        positions = mt5.positions_get()
        if positions is None:
            return []
        
        return [{
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "type": pos.type,
            "volume": pos.volume,
            "price_open": pos.price_open,
            "price_current": pos.price_current,
            "sl": pos.sl,
            "tp": pos.tp,
            "profit": pos.profit,
            "swap": pos.swap,
            "time": datetime.fromtimestamp(pos.time).isoformat(),
            "comment": pos.comment,
            "magic": pos.magic
        } for pos in positions]
    
    def resolve_symbol(self, symbol: str) -> str:
        """Resolve requested symbol against actual MT5 broker symbols (handles 'm', '.a', etc.)."""
        if not self.connected:
            return symbol

        # Direct match
        if mt5.symbol_info(symbol) is not None:
            return symbol

        all_symbols = mt5.symbols_get()
        if not all_symbols:
            return symbol

        avail_names = [s.name for s in all_symbols]

        # Suffix variations
        for suffix in ["m", ".a", ".pro", "_i"]:
            candidate = symbol + suffix
            if candidate in avail_names:
                return candidate

        # Partial matching
        base = symbol.replace("m", "").upper()
        for name in avail_names:
            if base in name.upper():
                return name

        return symbol

    def get_candles(self, symbol: str, timeframe: str, count: int = 1000) -> pd.DataFrame:
        """Get historical candle data"""
        if not self.connected:
            return pd.DataFrame()

        symbol = self.resolve_symbol(symbol)
        timeframe_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }

        tf = timeframe_map.get(timeframe, mt5.TIMEFRAME_M5)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)

        if rates is None or len(rates) == 0:
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    
    def place_order(self, symbol: str, order_type: str, volume: float, 
                    sl: float = 0, tp: float = 0, comment: str = "AI Bot") -> Optional[Dict]:
        """Place a market order"""
        if not self.connected:
            return None
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"Symbol {symbol} not found")
            return None
        
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                print(f"Failed to select {symbol}")
                return None
        
        price = mt5.symbol_info_tick(symbol).ask if order_type == "BUY" else mt5.symbol_info_tick(symbol).bid
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if order_type == "BUY" else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 234000,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
        }
        
        # Brokers support different filling modes. Try them in order.
        fillings = [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN]
        result = None
        for filling in fillings:
            request["type_filling"] = filling
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                break
        
        if not result or result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Order failed: {result.comment if result else 'Unknown error'}")
            return None
        
        return {
            "ticket": result.order,
            "volume": result.volume,
            "price": result.price,
            "comment": result.comment
        }
    
    def close_position(self, ticket: int) -> bool:
        """Close a position by ticket"""
        if not self.connected:
            return False
        
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False
        
        position = position[0]
        
        order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(position.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(position.symbol).ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Close by bot",
            "type_time": mt5.ORDER_TIME_GTC,
        }
        
        fillings = [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN]
        result = None
        for filling in fillings:
            request["type_filling"] = filling
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                return True
                
        return False

    def modify_position(self, ticket: int, sl: float = 0.0, tp: float = 0.0) -> bool:
        """Modify SL and TP of an open position."""
        if not self.connected:
            return False

        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False

        pos = position[0]
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": pos.symbol,
            "sl": float(sl),
            "tp": float(tp if tp > 0 else pos.tp),
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return True
        else:
            comment = result.comment if result else "Unknown error"
            print(f"  [MT5] Failed to modify position #{ticket}: {comment}")
            return False

    
    def get_tick(self, symbol: str) -> Optional[Dict]:
        """Get current tick data"""
        if not self.connected:
            return None
        
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        
        return {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last,
            "time": datetime.fromtimestamp(tick.time).isoformat()
        }

    def get_deal_history(self, ticket: int) -> Optional[Dict]:
        """Fetch closed deal outcome details for a position ticket from MT5 history."""
        if not self.connected:
            return None

        # Fetch deals for position
        deals = mt5.history_deals_get(position=ticket)
        if deals is None or len(deals) == 0:
            return None

        # Sum profit, swap, commission across deals for this position
        total_profit = sum(d.profit + d.swap + d.commission for d in deals)
        exit_deal = deals[-1]  # The closing deal
        entry_deal = deals[0]   # The opening deal

        close_price = exit_deal.price
        entry_price = entry_deal.price
        close_time = datetime.fromtimestamp(exit_deal.time).isoformat()

        # Calculate pips gained/lost
        pips = 0.0
        if entry_price > 0 and close_price > 0:
            direction = 1 if entry_deal.type == mt5.DEAL_TYPE_BUY else -1
            diff = (close_price - entry_price) * direction
            if "JPY" in entry_deal.symbol:
                pips = diff * 100
            elif "XAU" in entry_deal.symbol or "GOLD" in entry_deal.symbol:
                pips = diff * 10
            else:
                pips = diff * 10000

        # Determine close reason heuristic
        comment = exit_deal.comment.upper() if exit_deal.comment else ""
        if "SL" in comment:
            reason = "SL_HIT"
        elif "TP" in comment:
            reason = "TP_HIT"
        elif total_profit > 0:
            reason = "CLOSED_PROFIT"
        else:
            reason = "CLOSED_LOSS"

        return {
            "ticket": ticket,
            "close_price": close_price,
            "profit": total_profit,
            "pips": pips,
            "close_time": close_time,
            "close_reason": reason,
        }

