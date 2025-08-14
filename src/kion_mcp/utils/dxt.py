"""DXT-related utility functions."""

import os


def is_dxt_mode() -> bool:
    """Check if running in DXT mode.
    
    Returns:
        bool: True if running in DXT mode, False otherwise.
    """
    return os.getenv('KION_DXT_MODE', '').lower() == 'true'