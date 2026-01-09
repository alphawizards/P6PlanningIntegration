#!/usr/bin/env python3
"""
Utility functions for P6 GUI Automation.

Provides:
- Smart waiting functions
- Screenshot capture
- Control identifier helpers
- Retry mechanisms
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Any
from functools import wraps

from src.utils import logger
from src.config import PDF_OUTPUT_DIR


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator to retry a function on failure.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds
        exceptions: Tuple of exceptions to catch
        on_retry: Optional callback on retry(attempt, exception)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        if on_retry:
                            on_retry(attempt, e)
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed: {e}")
            raise last_exception
        return wrapper
    return decorator


def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = 30.0,
    poll_interval: float = 0.5,
    description: str = "condition"
) -> bool:
    """
    Wait for a condition to become true.
    
    Args:
        condition: Callable that returns True when condition is met
        timeout: Maximum wait time in seconds
        poll_interval: Time between checks in seconds
        description: Description for logging
        
    Returns:
        True if condition was met, False if timeout
    """
    start_time = time.time()
    logger.debug(f"Waiting for {description} (timeout={timeout}s)")
    
    while time.time() - start_time < timeout:
        try:
            if condition():
                elapsed = time.time() - start_time
                logger.debug(f"{description} satisfied in {elapsed:.1f}s")
                return True
        except Exception as e:
            logger.debug(f"Condition check error: {e}")
        time.sleep(poll_interval)
    
    logger.warning(f"Timeout waiting for {description} after {timeout}s")
    return False


def wait_for_window(
    app,
    title: Optional[str] = None,
    title_re: Optional[str] = None,
    control_type: Optional[str] = None,
    timeout: float = 30.0
):
    """
    Wait for a window to appear.
    
    Args:
        app: pywinauto Application instance
        title: Exact window title
        title_re: Regex pattern for title
        control_type: Control type filter
        timeout: Maximum wait time
        
    Returns:
        Window wrapper if found
        
    Raises:
        TimeoutError if window not found
    """
    from .exceptions import P6TimeoutError
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            kwargs = {}
            if title:
                kwargs['title'] = title
            if title_re:
                kwargs['title_re'] = title_re
            if control_type:
                kwargs['control_type'] = control_type
            
            window = app.window(**kwargs)
            if window.exists():
                window.wait('ready', timeout=5)
                return window
        except Exception:
            pass
        time.sleep(0.5)
    
    # Build descriptive error message
    criteria = []
    if title:
        criteria.append(f"title='{title}'")
    if title_re:
        criteria.append(f"title_re='{title_re}'")
    if control_type:
        criteria.append(f"control_type='{control_type}'")
    criteria_str = ", ".join(criteria) if criteria else "no criteria"
    
    raise P6TimeoutError(f"Window not found ({criteria_str}) within {timeout}s")


def capture_screenshot(
    window,
    filename: Optional[str] = None,
    output_dir: Optional[Path] = None
) -> Path:
    """
    Capture a screenshot of a window.
    
    Args:
        window: pywinauto window wrapper
        filename: Optional filename (auto-generated if not provided)
        output_dir: Output directory (defaults to PDF_OUTPUT_DIR)
        
    Returns:
        Path to saved screenshot
    """
    output_dir = Path(output_dir or PDF_OUTPUT_DIR) / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"p6_screenshot_{timestamp}.png"
    
    if not filename.endswith('.png'):
        filename += '.png'
    
    output_path = output_dir / filename
    
    try:
        image = window.capture_as_image()
        image.save(str(output_path))
        logger.info(f"Screenshot saved: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to capture screenshot: {e}")
        raise


def safe_click(control, retry_count: int = 3):
    """
    Safely click a control with retry logic.
    
    Args:
        control: pywinauto control wrapper
        retry_count: Number of retries on failure
    """
    for attempt in range(retry_count):
        try:
            control.wait('visible', timeout=5)
            control.click_input()
            return
        except Exception as e:
            if attempt < retry_count - 1:
                logger.warning(f"Click failed (attempt {attempt + 1}): {e}")
                time.sleep(0.5)
            else:
                raise


def safe_type(control, text: str, clear_first: bool = True):
    """
    Safely type text into a control.
    
    Args:
        control: pywinauto control wrapper
        text: Text to type
        clear_first: Clear existing text before typing
    """
    control.wait('visible', timeout=5)
    if clear_first:
        control.set_text('')
    control.type_keys(text, with_spaces=True)


def get_timestamp() -> str:
    """Get formatted timestamp for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string for use as a filename.
    
    Args:
        name: Original name
        
    Returns:
        Safe filename string
    """
    # Replace common problematic characters
    replacements = {
        '/': '-',
        '\\': '-',
        ':': '-',
        '*': '',
        '?': '',
        '"': '',
        '<': '',
        '>': '',
        '|': '-',
        ' ': '_'
    }
    
    result = name
    for old, new in replacements.items():
        result = result.replace(old, new)
    
    # Remove any remaining non-alphanumeric except underscores and hyphens
    result = ''.join(c for c in result if c.isalnum() or c in '_-.')
    
    return result


def print_control_tree(window, max_depth: int = 3):
    """
    Print control hierarchy for debugging.
    
    Args:
        window: pywinauto window wrapper
        max_depth: Maximum depth to traverse
    """
    print("=" * 60)
    print(f"Control Tree for: {window.window_text()}")
    print("=" * 60)
    window.print_control_identifiers(depth=max_depth)
