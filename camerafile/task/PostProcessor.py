import subprocess
from typing import List, Optional

from camerafile.core.Logging import Logger

LOGGER = Logger(__name__)


class PostProcessor:
    """
    Utility class for executing post-processing scripts after file operations.
    """

    @staticmethod
    def execute_for_paths(script_path: Optional[str], mode: str, paths_list: List[str]) -> None:
        """
        Execute a post-processing script for a list of paths.
        
        Args:
            script_path: Path to the post-processing script to execute. If None, no action is taken.
            mode: Mode parameter passed to the script ('o' for origin, 'd' for destination)
            paths_list: List of directory paths that were modified
        """
        if script_path is None or not paths_list:
            return
        
        for path in paths_list:
            LOGGER.info(f"This path has been modified in {'origin' if mode == 'o' else 'target'} media set: {path}")
            cmd = [script_path, mode, path]
            cmd_str = " ".join(cmd)
            LOGGER.info(f"Executing post-processing script: {cmd_str}")
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minutes
                )
                
                if result.stdout:
                    LOGGER.info(f"Post-processing output: {result.stdout.strip()}")
                
                if result.returncode != 0:
                    LOGGER.info(
                        f"Post-processing script exited with code {result.returncode}: {cmd_str}"
                    )
                    if result.stderr:
                        LOGGER.info(f"Post-processing stderr: {result.stderr.strip()}")
                        
            except subprocess.TimeoutExpired:
                LOGGER.info(f"Post-processing script timed out after 300 seconds: {cmd_str}")
            except FileNotFoundError:
                LOGGER.info(f"Post-processing script not found: {script_path}")
            except Exception as e:
                LOGGER.info(f"Post-processing script error: {e}")
