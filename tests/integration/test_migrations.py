"""Integration tests for Alembic migration system."""

import os
import pytest
import tempfile
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.core.config import get_settings


class TestMigrationSystem:
    """Test suite for Alembic migration system."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database for testing."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def alembic_config(self, temp_db):
        """Create Alembic configuration for testing."""
        # Get the base alembic.ini path
        ini_path = os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")
        config = Config(ini_path)
        
        # Override the database URL to use our temp database
        config.set_main_option("sqlalchemy.url", f"sqlite:///{temp_db}")
        
        return config
    
    def test_migration_upgrade_downgrade(self, alembic_config, temp_db):
        """Test that migration can be applied and rolled back."""
        # Run the migration
        command.upgrade(alembic_config, "head")
        
        # Verify tables exist
        engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
        with Session(engine) as session:
            # Check that all expected tables exist
            result = session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ))
            tables = [row[0] for row in result.fetchall()]
            
            expected_tables = {
                'users', 'topics', 'exercises', 'lessons', 
                'lesson_exercises', 'user_progress', 
                'evaluation_logs', 'content_generation_logs',
                'alembic_version'  # Alembic tracking table
            }
            
            assert expected_tables.issubset(set(tables)), f"Missing tables: {expected_tables - set(tables)}"
        
        # Test rollback
        command.downgrade(alembic_config, "base")
        
        # Verify tables are gone (except alembic_version)
        engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
        with Session(engine) as session:
            result = session.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ))
            tables = [row[0] for row in result.fetchall()]
            
            # Only alembic_version should remain
            assert 'alembic_version' in tables
            assert 'users' not in tables
            assert 'topics' not in tables
    
    def test_migration_current_version(self, alembic_config):
        """Test checking current migration version."""
        # Run migration first
        command.upgrade(alembic_config, "head")
        
        # Check current version
        engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
        with Session(engine) as session:
            result = session.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            
            assert version is not None
            assert len(version) == 12  # Alembic revision IDs are 12 chars
    
    def test_migration_idempotency(self, alembic_config):
        """Test that running migration multiple times is safe."""
        # Run migration twice
        command.upgrade(alembic_config, "head")
        command.upgrade(alembic_config, "head")  # Should be no-op
        
        # Verify database is still in correct state
        engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
        with Session(engine) as session:
            result = session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            # Table should exist but be empty
            assert count == 0
    
    def test_migration_with_data(self, alembic_config, temp_db):
        """Test that migration works with existing data."""
        # First, run migration
        command.upgrade(alembic_config, "head")
        
        # Insert some test data
        engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
        with Session(engine) as session:
            # Insert a user
            session.execute(text("""
                INSERT INTO users (wa_id, name, native_lang, target_lang, level, is_premium, daily_lessons_count, streak_days)
                VALUES ('12345', 'Test User', 'es', 'en', 'A1', 0, 0, 0)
            """))
            
            # Insert a topic
            session.execute(text("""
                INSERT INTO topics (name, description)
                VALUES ('Test Topic', 'A topic for testing')
            """))
            
            session.commit()
        
        # Run migration again (should preserve data)
        command.upgrade(alembic_config, "head")
        
        # Verify data is still there
        with Session(engine) as session:
            # Check user
            result = session.execute(text("SELECT name FROM users WHERE wa_id = '12345'"))
            assert result.scalar() == 'Test User'
            
            # Check topic
            result = session.execute(text("SELECT name FROM topics WHERE name = 'Test Topic'"))
            assert result.scalar() == 'Test Topic'
    
    def test_migration_history(self, alembic_config):
        """Test viewing migration history."""
        # Run migration
        command.upgrade(alembic_config, "head")
        
        # Get history
        engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
        with Session(engine) as session:
            result = session.execute(text("SELECT version_num FROM alembic_version"))
            current_version = result.scalar()
            
            assert current_version is not None
            assert len(current_version) == 12
