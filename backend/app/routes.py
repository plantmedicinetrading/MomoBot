# app/routes.py

from flask import Blueprint, jsonify, request
from .shared_state import ticker_states
from collections import defaultdict
from .trading.core.execution import submit_order
from .db import insert_trade, get_all_trades, insert_execution, get_all_executions
from datetime import datetime
from .utils.hotkey_utils import trigger_hotkey
from .utils.voice_utils import announce_trade_exit
import csv
from flask import Response
from .trading.stream.polygon_stream import fetch_historical_aggregated_bars
import traceback

# Modular broker import (to be created)
# If broker logic is needed, replace with internal simulation or remove

main_bp = Blueprint("main", __name__)

@main_bp.route("/ping", methods=["GET"])
def ping():
    """Health check endpoint."""
    return jsonify({"status": "ok", "message": "Momo Bot backend is alive"}), 200

@main_bp.route("/state/<symbol>", methods=["GET"])
def get_symbol_state(symbol):
    """Return the full runtime state for a given symbol."""
    symbol = symbol.upper()
    state = ticker_states.get(symbol)
    if not state:
        return jsonify({"error": f"No state found for {symbol}"}), 404

    return jsonify(state), 200

@main_bp.route("/entry-type", methods=["POST"])
def set_entry_type():
    """Set the active entry type for a symbol manually."""
    data = request.json
    symbol = data.get("symbol", "").upper()
    entry_type = data.get("entry_type", "").lower()

    if symbol and entry_type in ["10s", "1m", "5m"]:
        ticker_states[symbol]["active_entry_type"] = entry_type
        return jsonify({"status": "ok", "symbol": symbol, "entry_type": entry_type}), 200

    return jsonify({"error": "Invalid symbol or entry_type"}), 400

@main_bp.route("/positions", methods=["GET"])
def get_all_positions():
    """Return all open trading positions."""
    positions = []
    for symbol, state in ticker_states.items():
        pos = state.get("position")
        if pos:
            last_quote = state.get("last_quote")
            last_price = None
            bid = ask = None
            if last_quote:
                bid = getattr(last_quote, "bid", None) or getattr(last_quote, "bid_price", None)
                ask = getattr(last_quote, "ask", None) or getattr(last_quote, "ask_price", None)
                if bid is not None and ask is not None:
                    last_price = (bid + ask) / 2
                elif bid is not None:
                    last_price = bid
                elif ask is not None:
                    last_price = ask
            entry_price = pos.get("entry_price")
            size = pos.get("size")
            unrealized = None
            diff_per_share = None
            if last_price is not None and entry_price is not None and size is not None:
                diff_per_share = last_price - entry_price
                unrealized = diff_per_share * size
            positions.append({
                "symbol": symbol,
                **pos,
                "last_price": last_price,
                "bid": bid,
                "ask": ask,
                "unrealized": unrealized,
                "diff_per_share": diff_per_share
            })
    return jsonify(positions), 200

@main_bp.route("/trade-history", methods=["GET"])
def trade_history():
    return jsonify(get_all_trades()), 200

@main_bp.route('/trade-history/<int:trade_id>', methods=['DELETE'])
def delete_trade(trade_id):
    from .db import delete_trade_by_id
    success = delete_trade_by_id(trade_id)
    if success:
        return jsonify({"status": "deleted"}), 200
    else:
        return jsonify({"error": "Trade not found"}), 404

@main_bp.route("/tradervue-export", methods=["GET"])
def tradervue_export():
    executions = get_all_executions()
    def generate():
        header = ['Date','Time','Symbol','Quantity','Price','Side','EntryType']
        yield ','.join(header) + '\n'
        for exe in executions:
            dt = datetime.fromisoformat(exe['datetime'])
            date_str = dt.strftime('%Y-%m-%d')
            time_str = dt.strftime('%H:%M:%S')
            row = [
                date_str,
                time_str,
                exe['symbol'],
                str(exe['quantity']),
                f"{exe['price']:.2f}",
                exe['side'],
                exe.get('entry_type') or ''
            ]
            yield ','.join(row) + '\n'
    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=tradervue_export.csv"})

@main_bp.route("/close-position", methods=["POST"])
def close_position():
    data = request.json
    symbol = data.get("symbol", "").upper()
    pos = None
    # Only use internal state for position
    if symbol in ticker_states and ticker_states[symbol].get("position"):
        pos = ticker_states[symbol]["position"]
    else:
        return jsonify({"error": "No open position for symbol (not found in state)"}), 400
    size = pos.get("size")
    last_quote = ticker_states[symbol].get("last_quote")
    if not last_quote or not size:
        return jsonify({"error": "No quote or size info for symbol"}), 400
    bid = getattr(last_quote, "bid", None) or getattr(last_quote, "bid_price", None)
    ask = getattr(last_quote, "ask", None) or getattr(last_quote, "ask_price", None)
    # Send hotkey FIRST for manual position close - before any logging or recording
    trigger_hotkey("sell_all_bid")
    # Announce manual position close with robotic voice
    exit_price = bid if bid is not None else ask
    announce_trade_exit(symbol, exit_price, "manual close")
    # Simulate sell order
    order = submit_order(symbol, size, "sell", bid, ask)
    # Record executions (Buy and Sell)
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    entry_time = pos.get("entry_time") or now
    entry_price = pos.get("entry_price")
    exit_price = bid if bid is not None else ask
    entry_type = pos.get("entry_type")
    # Insert Buy execution if not already present (for this trade)
    insert_execution({
        "symbol": symbol,
        "quantity": size,
        "price": entry_price,
        "side": "Buy",
        "datetime": entry_time,
        "trade_id": None,
        "commission": None,
        "entry_type": entry_type
    })
    # Insert Sell execution
    insert_execution({
        "symbol": symbol,
        "quantity": size,
        "price": exit_price,
        "side": "Sell",
        "datetime": now,
        "trade_id": None,
        "commission": None,
        "entry_type": entry_type
    })
    # Record trade in DB
    profit_loss = (exit_price - entry_price) * size if entry_price and exit_price and size else 0
    insert_trade({
        "symbol": symbol,
        "shares": size,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "entry_type": entry_type,
        "entry_time": entry_time,
        "exit_time": now,
        "profit_loss": profit_loss
    })
    # Do NOT remove the position from state here; let the order update handler do it
    # Update state
    pos["closed"] = True
    ticker_states[symbol]["position"] = None
    return jsonify({"status": "closed", "symbol": symbol, "order_id": order.get('id', None)}), 200

@main_bp.route('/api/candles')
def get_candles():
    symbol = request.args.get('symbol')
    timeframe = request.args.get('timeframe', '1m')
    limit = int(request.args.get('limit', 500))
    try:
        bars = fetch_historical_aggregated_bars(symbol, timeframe, limit)
        print(f"Bars returned for {symbol} ({timeframe}): {len(bars)}")
        return jsonify(bars)
    except Exception as e:
        print("Error in /api/candles:", e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500