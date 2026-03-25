"""
Logging utility for DriftWatch.
"""

import logging
import os
import sys

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Simple console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        # Consistent format
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)-8s %(name)-15s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Set level based on environment if needed
        if os.getenv("DEBUG", "").lower() in ("true", "1", "yes"):
            logger.setLevel(logging.DEBUG)
            handler.setLevel(logging.DEBUG)
            
    return logger
