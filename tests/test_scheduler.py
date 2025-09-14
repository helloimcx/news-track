"""
Tests for the scheduler setup.
This is a basic test to ensure the scheduler logic is sound.
More comprehensive testing of scheduling behavior would require complex async/time mocks.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.main import run_scheduler

class TestScheduler:

    @pytest.mark.asyncio
    async def test_run_scheduler_initialization_and_job_add(self):
        """
        Test that run_scheduler initializes the scheduler and attempts to add a job.
        This is a basic integration-like test for the setup logic.
        """
        # Mock the AsyncIOScheduler
        with patch('app.main.AsyncIOScheduler') as MockSchedulerClass:
            mock_scheduler_instance = MockSchedulerClass.return_value
            
            # Mock add_job to succeed
            mock_scheduler_instance.add_job = MagicMock()
            
            # Mock scheduler.start and shutdown to do nothing
            mock_scheduler_instance.start = MagicMock()
            mock_scheduler_instance.shutdown = MagicMock()
            
            # Mock asyncio.sleep to raise an exception to break the infinite loop quickly
            with patch('app.main.asyncio.sleep', side_effect=KeyboardInterrupt):
                # Mock settings if needed (they are imported, so changing them directly is tricky)
                # For this test, we rely on the default settings from app.config
                
                try:
                    await run_scheduler()
                except KeyboardInterrupt:
                    pass # Expected due to our mock
                
                # Assertions
                # 1. Scheduler class was instantiated
                MockSchedulerClass.assert_called_once()
                
                # 2. add_job was called with the correct arguments
                mock_scheduler_instance.add_job.assert_called_once()
                call_args = mock_scheduler_instance.add_job.call_args
                args, kwargs = call_args
                # Assert the function to be scheduled
                assert args[0].__name__ == 'run_pipeline' # The function object
                # Assert the trigger type is 'cron' (check if it's in kwargs)
                # APScheduler's add_job signature is add_job(func, trigger=None, ...)
                # If trigger is not explicitly passed as kwarg, it might default based on other args.
                # Let's check if 'trigger' kwarg is 'cron' or if args[1] (the trigger positional arg) is 'cron'
                trigger_arg = kwargs.get('trigger') or (args[1] if len(args) > 1 else None)
                assert trigger_arg == 'cron', f"Expected trigger 'cron', got {trigger_arg}. kwargs: {kwargs}"
                # Assert the job ID
                assert kwargs.get('id') == 'news_digest_job'
                # Assert timezone is present (value checked by config tests)
                assert 'timezone' in kwargs
                
                # 3. scheduler.start was called
                mock_scheduler_instance.start.assert_called_once()
                
                # 4. scheduler.shutdown was called due to KeyboardInterrupt
                mock_scheduler_instance.shutdown.assert_called_once()