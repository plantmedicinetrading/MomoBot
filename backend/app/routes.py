# app/routes.py

from flask import Blueprint, jsonify, request
from .state import ticker_states

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