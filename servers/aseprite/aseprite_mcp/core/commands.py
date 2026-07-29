import subprocess
import tempfile
import os
import dotenv
from .path_resolver import get_aseprite_path

# Resolve .env relative to the package root, not the process cwd: an MCP
# server is normally spawned from the client's working directory, so a
# cwd-relative load silently finds nothing.
_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
dotenv.load_dotenv(dotenv_path=_ENV_PATH)
dotenv.load_dotenv()


def lua_escape(s: str) -> str:
    """Escape a string for safe embedding inside a Lua double-quoted string literal."""
    return (
        s.replace("\\", "\\\\")
         .replace('"', '\\"')
         .replace("\n", "\\n")
         .replace("\r", "\\r")
         .replace("\0", "\\0")
    )


def reject_traversal(path: str) -> str | None:
    """Reject parent-directory traversal in a user-supplied path.

    Returns an error message string when the path contains a `..`
    component, or None when the path looks safe.

    The check works on normalized path components, so it does not
    false-positive on filenames like `foo..bar.aseprite` (a plain
    `'..' in path` substring check does). Absolute paths and tilde
    expansion are not rejected here: this targets traversal only, not
    access scoping.
    """
    parts = os.path.normpath(path).replace("\\", "/").split("/")
    if ".." in parts:
        return "Invalid filename: parent directory traversal not allowed"
    return None


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
        executable = AsepriteCommand.get_aseprite_executable()
        try:
            result = subprocess.run(
                [executable] + args, check=True, capture_output=True, text=True
            )
            output = (result.stdout or "").strip()
            if not output:
                output = (result.stderr or "").strip()
            return True, output
        except subprocess.CalledProcessError as e:
            output = (e.stderr or "").strip()
            if not output:
                output = (e.stdout or "").strip()
            return False, output
        except (FileNotFoundError, NotADirectoryError, PermissionError) as e:
            # A missing or unusable executable must surface as a tool-level
            # error, not an exception that takes the MCP server down.
            return False, (
                f"Cannot run Aseprite at '{executable}': {e.strerror or e}. "
                "Set ASEPRITE_PATH in .env or on the environment."
            )

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
        with tempfile.NamedTemporaryFile(suffix='.lua', delete=False, mode='w', encoding='utf-8') as tmp:
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

    @staticmethod
    def execute_lua_script_checked(script_content, filename=None):
        """Execute a Lua script and surface in-script errors.

        Scripts using this helper signal failure by printing a line
        starting with "ERROR:" — batch-mode scripts cannot affect the
        process exit code from Lua, and a bare `return "message"` at Lua
        top level is discarded, so failures are otherwise silent.

        Returns:
            tuple: (success, output) where output is the error message
            when an ERROR: line was printed, or the raw stdout otherwise.
        """
        success, output = AsepriteCommand.execute_lua_script(script_content, filename)
        if not success:
            return False, output
        for line in output.splitlines():
            if line.startswith("ERROR:"):
                return False, line[len("ERROR:"):]
        return True, output
