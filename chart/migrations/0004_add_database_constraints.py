# Generated manually for database constraints and validation

from django.db import migrations, models
import django.core.validators
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('chart', '0003_add_plugin_processing_task_type_and_indexes'),
    ]

    operations = [
        # Add validation constraints for User model (SQLite compatible)
        migrations.RunSQL(
            # Forward SQL - add constraints (SQLite uses CHECK constraints differently)
            """
            -- Note: SQLite doesn't support ALTER TABLE ADD CONSTRAINT in the same way
            -- These constraints are handled at the Django model level instead
            """,
            # Reverse SQL - no action needed
            """
            -- No reverse action needed for SQLite
            """
        ),
        
        # Add validation constraints for Chart model (SQLite compatible)
        migrations.RunSQL(
            # Forward SQL - add constraints
            """
            -- Note: SQLite doesn't support ALTER TABLE ADD CONSTRAINT in the same way
            -- These constraints are handled at the Django model level instead
            """,
            # Reverse SQL - no action needed
            """
            -- No reverse action needed for SQLite
            """
        ),
        
        # Add validation constraints for TaskStatus model (SQLite compatible)
        migrations.RunSQL(
            # Forward SQL - add constraints
            """
            -- Note: SQLite doesn't support ALTER TABLE ADD CONSTRAINT in the same way
            -- These constraints are handled at the Django model level instead
            """,
            # Reverse SQL - no action needed
            """
            -- No reverse action needed for SQLite
            """
        ),
        
        # Add indexes for better performance (SQLite compatible)
        migrations.RunSQL(
            # Forward SQL - add indexes
            """
            CREATE INDEX IF NOT EXISTS idx_user_session_user_active 
            ON user_session (user_id, is_active);
            
            CREATE INDEX IF NOT EXISTS idx_user_session_ip_created 
            ON user_session (ip_address, created_at);
            
            CREATE INDEX IF NOT EXISTS idx_user_session_last_activity 
            ON user_session (last_activity);
            
            CREATE INDEX IF NOT EXISTS idx_password_reset_token_token_used 
            ON password_reset_token (token, is_used);
            
            CREATE INDEX IF NOT EXISTS idx_password_reset_token_expires 
            ON password_reset_token (expires_at);
            
            CREATE INDEX IF NOT EXISTS idx_task_status_progress 
            ON chart_task_status (progress);
            """,
            # Reverse SQL - remove indexes
            """
            DROP INDEX IF EXISTS idx_user_session_user_active;
            DROP INDEX IF EXISTS idx_user_session_ip_created;
            DROP INDEX IF EXISTS idx_user_session_last_activity;
            DROP INDEX IF EXISTS idx_password_reset_token_token_used;
            DROP INDEX IF EXISTS idx_password_reset_token_expires;
            DROP INDEX IF EXISTS idx_task_status_progress;
            """
        ),
    ] 