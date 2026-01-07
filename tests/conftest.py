"""
Pytest fixtures for SQLite DAO tests.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.dao.sqlite import SQLiteManager


@pytest.fixture(scope="session")
def sqlite_manager():
    """
    Session-scoped fixture providing a connected SQLiteManager.
    
    Uses the live P6 database in read-only (immutable) mode.
    Connection is shared across all tests for efficiency.
    """
    manager = SQLiteManager()
    manager.connect()
    yield manager
    manager.disconnect()


@pytest.fixture
def project_dao(sqlite_manager):
    """Fixture providing ProjectDAO instance."""
    return sqlite_manager.get_project_dao()


@pytest.fixture
def activity_dao(sqlite_manager):
    """Fixture providing ActivityDAO instance."""
    return sqlite_manager.get_activity_dao()


@pytest.fixture
def relationship_dao(sqlite_manager):
    """Fixture providing RelationshipDAO instance."""
    return sqlite_manager.get_relationship_dao()
