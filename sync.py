import os
import sys
import subprocess
import platform
from secure_ssh import get_vps_password

# Configuration - Update these if needed
IP = "43.131.49.3"
USER = "ubuntu"
REPO_DIR = "~/ai-portfolio"
DEFAULT_COMMIT_MESSAGE = "Minor update"


def run_cmd(cmd, shell=False):
    """Run a shell command and print output."""
    print(f"> {cmd}")
    try:
        subprocess.check_call(cmd, shell=shell)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return False


def safe_print(text: str) -> None:
    """Print text without crashing on terminal encoding mismatches."""
    try:
        print(text)
    except UnicodeEncodeError:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout.buffer.write((text + "\n").encode("ascii", "backslashreplace"))
        else:
            print(text.encode("ascii", "backslashreplace").decode("ascii"))


def _resolved_commit_message() -> str:
    """Resolve commit message for interactive and non-interactive runs."""
    env_msg = os.environ.get("SYNC_COMMIT_MESSAGE", "").strip()
    if env_msg:
        return env_msg

    if len(sys.argv) > 1:
        arg_msg = " ".join(sys.argv[1:]).strip()
        if arg_msg:
            return arg_msg

    if sys.stdin is not None and sys.stdin.isatty():
        try:
            msg = input(f"Enter commit message (default: '{DEFAULT_COMMIT_MESSAGE}'): ").strip()
            return msg or DEFAULT_COMMIT_MESSAGE
        except EOFError:
            return DEFAULT_COMMIT_MESSAGE

    return DEFAULT_COMMIT_MESSAGE


def _ensure_paramiko() -> None:
    """Ensure paramiko is importable in the current interpreter."""
    try:
        import paramiko  # noqa: F401
        return
    except ImportError:
        pass

    print("Installing paramiko for SSH connection...")
    if not run_cmd([sys.executable, "-m", "ensurepip", "--upgrade"]):
        print("WARNING: ensurepip failed; attempting pip install anyway.")
    run_cmd([sys.executable, "-m", "pip", "install", "paramiko"])
    import paramiko  # noqa: F401


def local_sync():
    """Logic for local Windows machine: Push to GitHub -> Trigger VPS pull."""
    print("--- Local Sync: Pushing to GitHub ---")

    # 1. Git Push
    msg = _resolved_commit_message()
    if not run_cmd("git add .", shell=True):
        return

    if not run_cmd(["git", "commit", "-m", msg]):
        print("Nothing to commit, proceeding to push...")
    if not run_cmd("git push origin main", shell=True):
        return

    # 2. Trigger Remote Pull via SSH
    print("\n--- Triggering VPS to Pull Changes ---")
    _ensure_paramiko()
    import paramiko

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        password = get_vps_password(IP, USER)
        ssh.connect(IP, username=USER, password=password)
        # Execute the pull_and_deploy.sh script on the VPS
        cmd = f"bash {REPO_DIR}/pull_and_deploy.sh"
        print(f"Executing remote: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)

        for line in stdout:
            safe_print(f"REMOTE: {line.strip()}")
        for line in stderr:
            safe_print(f"REMOTE ERR: {line.strip()}")

        safe_print(f"\nSync complete. Live at http://{IP}:7860 or https://neurons.fyi/")
    except Exception as e:
        print(f"Failed to connect to VPS: {e}")
    finally:
        ssh.close()

def remote_sync():
    """Logic for the VPS: Pull from GitHub and restart."""
    print("--- Remote Sync: Pulling from GitHub ---")
    # Just run the existing bash script
    script_path = os.path.expanduser(f"{REPO_DIR}/pull_and_deploy.sh")
    run_cmd(["bash", script_path])

if __name__ == "__main__":
    if platform.system() == "Windows":
        local_sync()
    else:
        remote_sync()
