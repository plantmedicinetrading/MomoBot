# WebSocket Hotkey Integration

This document describes the WebSocket hotkey integration feature that automatically sends hotkey commands to a local hotkey server when trade events occur.

## Overview

The MomoBot now includes WebSocket hotkey functionality that sends commands to a local hotkey server at `ws://192.168.1.11:8765` when specific trade events occur. This allows for automated execution of trades on external platforms.

## Hotkey Commands

The following hotkey commands are sent based on trade events:

### Entry (Buy Order)
- **Command**: `buy_ask`
- **Trigger**: When a buy order is submitted for position entry

### Take Profit 1 (TP1)
- **Commands**: `sell_ask`, `cancel_all`, `break_even` (sent in sequence)
- **Trigger**: When TP1 price level is hit

### Take Profit 2 (TP2)
- **Command**: `sell_ask`
- **Trigger**: When TP2 price level is hit

### Stop Loss (SL)
- **Command**: `sell_all_bid`
- **Trigger**: When stop loss price level is hit

### Manual Position Close
- **Command**: `sell_all_bid`
- **Trigger**: When manually closing a position via the API

## Implementation Details

### Files Modified

1. **`requirements.txt`** - Added `websockets` library dependency
2. **`backend/app/utils/hotkey_utils.py`** - New hotkey utility module
3. **`backend/app/trading/core/execution.py`** - Added hotkey triggers to order submission
4. **`backend/app/trading/core/trade_monitor.py`** - Added hotkey triggers to trade target monitoring
5. **`backend/app/routes.py`** - Added hotkey trigger to manual position close

### Key Functions

#### `send_hotkey(action: str)`
- Connects to WebSocket server
- Sends the action string
- Handles connection errors gracefully
- Logs success/failure

#### `send_hotkey_sequence(actions: List[str])`
- Sends multiple actions in sequence
- Includes small delay between actions
- Returns success only if all actions succeed

#### `trigger_hotkey(action: str)` / `trigger_hotkey_sequence(actions: List[str])`
- Non-blocking async triggers
- Use `asyncio.create_task()` for fire-and-forget operation

## Configuration

The WebSocket server URL is configured in `backend/app/utils/hotkey_utils.py`:

```python
HOTKEY_SERVER_URL = "ws://192.168.1.11:8765"
```

## Testing

Run the test script to verify WebSocket connectivity:

```bash
cd backend/app
python test_hotkey.py
```

## Error Handling

- Connection errors are logged but don't interrupt trade execution
- Failed hotkey sends are logged with error details
- Trade execution continues normally even if hotkey fails

## Logging

Hotkey events are logged with the `[Hotkey]` prefix:
- `[Hotkey] Sent: buy_ask`
- `[Hotkey] Failed to send 'sell_ask': Connection refused`

## Integration Points

The hotkey functionality is integrated at the following points in the trading system:

1. **Entry Orders**: `submit_order()` for buy orders
2. **TP1 Hits**: `check_trade_targets()` when TP1 level is reached
3. **TP2 Hits**: `check_trade_targets()` when TP2 level is reached
4. **Stop Loss**: `check_trade_targets()` when stop level is reached
5. **Manual Close**: `/close-position` API endpoint

## Dependencies

- `websockets` Python library
- Async/await support for non-blocking operation
- Network connectivity to `192.168.1.11:8765` 