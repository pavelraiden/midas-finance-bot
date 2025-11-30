"""
PID File Manager for Single Instance Control
Prevents multiple bot instances from running simultaneously
"""
import os
import sys
import logging
import atexit
from pathlib import Path

logger = logging.getLogger(__name__)


class PIDManager:
    """
    Manages PID file to ensure only one bot instance runs at a time.
    """
    
    def __init__(self, pid_file_path: str = "/tmp/midas_bot.pid"):
        """
        Initialize PID manager.
        
        Args:
            pid_file_path: Path to PID file
        """
        self.pid_file = Path(pid_file_path)
        self.current_pid = os.getpid()
    
    def check_single_instance(self) -> bool:
        """
        Check if another instance is already running.
        
        Returns:
            True if this is the only instance, False otherwise
        """
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    old_pid = int(f.read().strip())
                
                # Check if process with old PID exists
                try:
                    os.kill(old_pid, 0)  # Signal 0 just checks if process exists
                    logger.error(
                        f"Another bot instance is already running (PID {old_pid}). "
                        f"Please stop it before starting a new instance."
                    )
                    return False
                except OSError:
                    # Process doesn't exist, PID file is stale
                    logger.info(f"Removing stale PID file (PID {old_pid})")
                    self.pid_file.unlink()
            
            except (ValueError, IOError) as e:
                logger.warning(f"Failed to read PID file: {e}")
                # Remove corrupted PID file
                try:
                    self.pid_file.unlink()
                except Exception:
                    pass
        
        # Write current PID
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(self.current_pid))
            logger.info(f"PID file created: {self.pid_file} (PID {self.current_pid})")
            
            # Register cleanup on exit
            atexit.register(self.cleanup)
            
            return True
            
        except IOError as e:
            logger.error(f"Failed to create PID file: {e}")
            return False
    
    def cleanup(self):
        """
        Remove PID file on exit.
        """
        try:
            if self.pid_file.exists():
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                # Only remove if it's our PID
                if pid == self.current_pid:
                    self.pid_file.unlink()
                    logger.info(f"PID file removed: {self.pid_file}")
        except Exception as e:
            logger.warning(f"Failed to cleanup PID file: {e}")
    
    def force_remove(self):
        """
        Force remove PID file (use with caution).
        """
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
                logger.info(f"PID file force removed: {self.pid_file}")
        except Exception as e:
            logger.error(f"Failed to force remove PID file: {e}")


def ensure_single_instance(pid_file_path: str = "/tmp/midas_bot.pid") -> bool:
    """
    Ensure only one bot instance is running.
    
    Args:
        pid_file_path: Path to PID file
    
    Returns:
        True if this is the only instance, False otherwise
    """
    manager = PIDManager(pid_file_path)
    return manager.check_single_instance()
