# WebSocket Hotkey Integration & Voice Announcements

This document describes the WebSocket hotkey integration feature and voice announcement system that automatically sends hotkey commands and provides audio feedback when trade events occur.

## Overview

The MomoBot now includes WebSocket hotkey functionality that sends commands to a local hotkey server at `ws://192.168.1.11:8765` when specific trade events occur, along with robotic voice announcements for enhanced trading feedback.

## Hotkey Commands

The following hotkey commands are sent based on trade events:

### Entry (Buy Order)
- **Command**: `buy_ask`
- **Trigger**: When a buy order is submitted for position entry
- **Voice**: "New trade taken for {TICKER} at {Entry Price}"

### Take Profit 1 (TP1)
- **Commands**: `sell_ask`, `cancel_all`, `break_even` (sent in sequence)
- **Trigger**: When TP1 price level is hit
- **Voice**: "Trade closed for {TICKER} at {Exit Price} due to take profit one"

### Take Profit 2 (TP2)
- **Command**: `sell_ask`
- **Trigger**: When TP2 price level is hit
- **Voice**: "Trade closed for {TICKER} at {Exit Price} due to take profit two"

### Stop Loss (SL)
- **Command**: `sell_all_bid`
- **Trigger**: When stop loss price level is hit
- **Voice**: "Trade closed for {TICKER} at {Exit Price} due to stop loss"

### Manual Position Close
- **Command**: `sell_all_bid`
- **Trigger**: When manually closing a position via the API
- **Voice**: "Trade closed for {TICKER} at {Exit Price} due to manual close"

## Implementation Details

### Files Modified

1. **`requirements.txt`** - Added `pyttsx3` library dependency
2. **`backend/app/utils/voice_utils.py`** - New voice announcement utility module
3. **`backend/app/utils/hotkey_utils.py`** - Existing hotkey utility module
4. **`backend/app/trading/core/execution.py`** - Added voice announcements to order submission
5. **`backend/app/trading/core/trade_monitor.py`** - Added voice announcements to trade target monitoring
6. **`backend/app/routes.py`** - Added voice announcement to manual position close

### Key Functions

#### Voice Announcements
- `announce_new_trade(ticker: str, entry_price: float)` - Announces new trade entries
- `announce_trade_exit(ticker: str, exit_price: float, reason: str)` - Announces trade exits
- `speak_announcement(text: str)` - Generic text-to-speech function

#### Hotkey Functions
- `send_hotkey(action: str)` - Connects to WebSocket server and sends action
- `send_hotkey_sequence(actions: List[str])` - Sends multiple actions in sequence
- `trigger_hotkey(action: str)` / `trigger_hotkey_sequence(actions: List[str])` - Non-blocking async triggers

## Configuration

### WebSocket Server
The WebSocket server URL is configured in `backend/app/utils/hotkey_utils.py`:

```python
HOTKEY_SERVER_URL = "ws://192.168.1.11:8765"
```

### Voice Settings
Voice settings are configured in `backend/app/utils/voice_utils.py`:

```python
_engine.setProperty('rate', 150)      # Speed of speech
_engine.setProperty('volume', 0.8)    # Volume level
```

The system automatically selects a male voice for a more robotic sound.

## Testing

### Test Voice Announcements
Run the voice test script to verify text-to-speech functionality:

```bash
cd backend/app
python test_voice.py
```

### Test Hotkey Connectivity
Run the hotkey test script to verify WebSocket connectivity:

```bash
cd backend/app
python test_hotkey.py
```

## Error Handling

- Connection errors are logged but don't interrupt trade execution
- Failed hotkey sends are logged with error details
- Voice announcement failures are logged but don't block trading
- Trade execution continues normally even if hotkey or voice fails

## Logging

### Hotkey Events
Hotkey events are logged with the `[Hotkey]` prefix:
- `[Hotkey] Sent: buy_ask`
- `[Hotkey] Failed to send 'sell_ask': Connection refused`

### Voice Events
Voice events are logged with the `[Voice]` prefix:
- `[Voice] Spoke: New trade taken for AAPL at 150.25`
- `[Voice] Failed to speak announcement: Text-to-speech engine not available`

## Integration Points

The hotkey and voice functionality is integrated at the following points in the trading system:

1. **Entry Orders**: `submit_order()` for buy orders
2. **Bracket Orders**: `submit_bracket_order()` for complex entries
3. **TP1 Hits**: `check_trade_targets()` when TP1 level is reached
4. **TP2 Hits**: `check_trade_targets()` when TP2 level is reached
5. **Stop Loss**: `check_trade_targets()` when stop level is reached
6. **Manual Close**: `/close-position` API endpoint

## Dependencies

### Hotkey System
- `websockets` Python library
- Async/await support for non-blocking operation
- Network connectivity to `192.168.1.11:8765`

### Voice System
- `pyttsx3` Python library for text-to-speech
- System text-to-speech engine (built into macOS, Windows, Linux)
- Threading support for non-blocking voice announcements 