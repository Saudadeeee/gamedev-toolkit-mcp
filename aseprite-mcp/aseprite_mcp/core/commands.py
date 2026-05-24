import subprocess
import tempfile
import os
import dotenv
from .path_resolver import get_aseprite_path

dotenv.load_dotenv()

class AsepriteCommand:
    """Helper class for running Aseprite commands."""

    @staticmethod
    def get_aseprite_executable():
        """Get the Aseprite executable path."""
        env_path = os.getenv('ASEPRITE_PATH')
        if env_path and os.path.exists(env_path):
            return env_path
        return get_aseprite_path() or 'aseprite'

    @staticmethod
    def run_command(args):
        """Run an Aseprite command with proper error handling.

        Args:
            args: List of command arguments

        Returns:
            tuple: (success, output) where success is a boolean and output is the command output
        """
        try:
            cmd = [AsepriteCommand.get_aseprite_executable()] + args
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
    
    @staticmethod
    def execute_lua_script(script_content, filename=None):
        """Execute a Lua script in Aseprite.
        
        Args:
            script_content: Lua script code to execute
            filename: Optional filename to open before executing script
            
        Returns:
            tuple: (success, output)
        """
        # Create a temporary file for the script
        with tempfile.NamedTemporaryFile(suffix='.lua', delete=False, mode='w') as tmp:
            tmp.write(script_content)
            script_path = tmp.name
        
        try:
            args = ["--batch"]
            if filename and os.path.exists(filename):
                args.append(filename)
            args.extend(["--script", script_path])
            
            success, output = AsepriteCommand.run_command(args)
            return success, output
        finally:
            # Clean up the temporary script file
            os.remove(script_path)