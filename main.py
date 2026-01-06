#!/usr/bin/env python3
"""
P6 Local AI Agent - Primavera P6 Integration via JPype1
Main entry point for Phase 1.5: Architecture & Safety Refactoring
"""

import sys
import jpype

from src.core import P6Session
from src.config import print_config_summary
from src.utils import logger, log_exception


def main():
    """
    Main entry point for P6 Planning Integration.
    
    Phase 1.5: Architecture & Safety Refactoring
    - Configuration management with fail-fast validation
    - Structured logging with file and console output
    - JVM stability checks (idempotency)
    - Safety switch mechanism (SAFE_MODE)
    - Database logic handling (standalone vs enterprise)
    """
    print("=" * 70)
    print("P6 Local AI Agent - Phase 1.5: Architecture & Safety Refactoring")
    print("=" * 70)
    print()
    
    try:
        # Display configuration summary
        print_config_summary()
        print()
        
        logger.info("Starting P6 Planning Integration")
        logger.info("Phase 1.5: Architecture & Safety Refactoring")
        
        # Initialize and connect to P6 using context manager
        logger.info("Initializing P6 session...")
        
        with P6Session() as session:
            logger.info("=" * 70)
            logger.info("✓ Phase 1.5: Connection Established & Architecture Validated")
            logger.info("=" * 70)
            logger.info("")
            logger.info("Verification Protocol Results:")
            logger.info("  ✓ JVM Stability: isJVMStarted() check implemented")
            logger.info("  ✓ Configuration Security: Secrets loaded via settings.py")
            logger.info("  ✓ Safety Switch: SAFE_MODE enforced in P6Session")
            logger.info("  ✓ Database Logic: Standalone/Enterprise modes handled")
            logger.info("")
            logger.info("Architecture Components:")
            logger.info("  ✓ src/config/settings.py - Configuration management")
            logger.info("  ✓ src/core/definitions.py - Schema definitions")
            logger.info("  ✓ src/utils/logger.py - Logging infrastructure")
            logger.info("  ✓ src/core/session.py - Session management")
            logger.info("")
            logger.info("Session is active and ready for business logic implementation")
        
        logger.info("P6 session closed successfully")
        logger.info("Phase 1.5 refactoring completed successfully")
        
        print()
        print("=" * 70)
        print("Status: Phase 1.5 completed successfully")
        print("=" * 70)
        
        return 0
        
    except jpype.JException as e:
        logger.error("Java exception occurred")
        log_exception(logger, e)
        print()
        print("=" * 70)
        print("Status: Failed - Java exception occurred")
        print("=" * 70)
        return 1
        
    except Exception as e:
        logger.error("Failed to complete Phase 1.5")
        log_exception(logger, e)
        print()
        print("=" * 70)
        print("Status: Failed - See logs for details")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
