"""
Tests for SQLiteManager.
"""

import pytest
from datetime import datetime


class TestSQLiteManagerConnection:
    """Tests for connection management."""
    
    def test_connection_established(self, sqlite_manager):
        """Test that manager is connected."""
        assert sqlite_manager.is_connected() is True
        assert sqlite_manager.is_active() is True
    
    def test_connection_timestamp_set(self, sqlite_manager):
        """Test that connection timestamp is tracked."""
        timestamp = sqlite_manager.get_connection_timestamp()
        assert timestamp is not None
        assert isinstance(timestamp, datetime)
        # Should be recent (within last hour)
        age_seconds = (datetime.now() - timestamp).total_seconds()
        assert age_seconds < 3600
    
    def test_schema_validation_passed(self, sqlite_manager):
        """Test that schema validation passed."""
        assert sqlite_manager.is_schema_valid() is True
    
    def test_db_path_set(self, sqlite_manager):
        """Test that database path is set."""
        assert sqlite_manager.db_path is not None
        assert len(sqlite_manager.db_path) > 0


class TestSQLiteManagerImmutableMode:
    """Tests for immutable mode behavior."""
    
    def test_read_only_mode(self, sqlite_manager):
        """Test that database is opened in read-only mode."""
        cursor = sqlite_manager.get_cursor()
        
        # Attempt to create a temp table should fail
        with pytest.raises(Exception):
            cursor.execute("CREATE TABLE test_table (id INTEGER)")
    
    def test_no_write_operations(self, sqlite_manager):
        """Test that INSERT fails in immutable mode."""
        cursor = sqlite_manager.get_cursor()
        
        with pytest.raises(Exception):
            cursor.execute("INSERT INTO PROJECT (proj_id) VALUES (99999)")


class TestSQLiteManagerRefresh:
    """Tests for connection refresh."""
    
    def test_refresh_connection(self, sqlite_manager):
        """Test that refresh_connection works."""
        old_timestamp = sqlite_manager.get_connection_timestamp()
        
        # Refresh
        result = sqlite_manager.refresh_connection()
        
        assert result is True
        assert sqlite_manager.is_connected() is True
        
        new_timestamp = sqlite_manager.get_connection_timestamp()
        assert new_timestamp >= old_timestamp
