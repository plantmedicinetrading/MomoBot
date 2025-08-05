# app/utils/hotkey_utils.py

import asyncio
import websockets
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

HOTKEY_SERVER_URL = "ws://192.168.1.28:8765"

async def send_hotkey(action: str) -> bool:
    """
    Send a hotkey action to the WebSocket server.
    
    Args:
        action: The action string to send (e.g., "buy_ask", "sell_ask", etc.)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        async with websockets.connect(HOTKEY_SERVER_URL) as websocket:
            await websocket.send(action)
            print(f"[Hotkey] Sent: {action}")
            logger.info(f"[Hotkey] Sent: {action}")
            return True
    except Exception as e:
        logger.error(f"[Hotkey] Failed to send '{action}': {e}")
        print(f"[Hotkey] Failed to send '{action}': {e}")
        return False

async def send_hotkey_sequence(actions: List[str]) -> bool:
    """
    Send multiple hotkey actions in sequence.
    
    Args:
        actions: List of action strings to send in order
    
    Returns:
        bool: True if all actions were successful, False otherwise
    """
    for action in actions:
        success = await send_hotkey(action)
        if not success:
            return False
        # Small delay between actions
        await asyncio.sleep(0.1)
    return True

def trigger_hotkey(action: str) -> None:
    """
    Trigger a hotkey action asynchronously without blocking.
    
    Args:
        action: The action string to send
    """
    try:
        # Try to create task if we're in an async context
        asyncio.create_task(send_hotkey(action))
    except RuntimeError:
        # If no event loop is running, run the coroutine in a new event loop
        import threading
        def run_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(send_hotkey(action))
                loop.close()
            except Exception as e:
                logger.error(f"[Hotkey] Thread execution failed for '{action}': {e}")
        
        thread = threading.Thread(target=run_in_thread)
        thread.daemon = True
        thread.start()

def trigger_hotkey_sequence(actions: List[str]) -> None:
    """
    Trigger multiple hotkey actions in sequence asynchronously without blocking.
    
    Args:
        actions: List of action strings to send in order
    """
    try:
        # Try to create task if we're in an async context
        asyncio.create_task(send_hotkey_sequence(actions))
    except RuntimeError:
        # If no event loop is running, run the coroutine in a new event loop
        import threading
        def run_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(send_hotkey_sequence(actions))
                loop.close()
            except Exception as e:
                logger.error(f"[Hotkey] Thread execution failed for sequence {actions}: {e}")
        
        thread = threading.Thread(target=run_in_thread)
        thread.daemon = True
        thread.start() 