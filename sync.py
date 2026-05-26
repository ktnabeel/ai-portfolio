import os
import sys
import subprocess
import platform

from secure_ssh import get_vps_password

# Configuration - Update these if needed
IP = "43.131.49.3"
USER = "ubuntu"
REPO_DIR = "~/ai-portfolio"


def run_cmd(cmd, shell=False):
    """Run a shell command and print output."""
    print(f"> {cmd}")
    try:
        subprocess.check_call(cmd, shell=shell)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return False

def local_sync():
    """Logic for local Windows machine: Push to GitHub -> Trigger VPS pull."""
    print("--- Local Sync: Pushing to GitHub ---")
    
    # 1. Git Push
    msg = input("Enter commit message (default: 'Minor update'): ") or "Minor update"
    if not run_cmd(f'git add .', shell=True): return
    if not run_cmd(f'git commit -m "{msg}"', shell=True):
        print("Nothing to commit, proceeding to push...")
    if not run_cmd(f'git push origin main', shell=True): return

    # 2. Trigger Remote Pull via SSH
    print("\n--- Triggering VPS to Pull Changes ---")
    try:
        import paramiko
    except ImportError:
        print("Installing paramiko for SSH connection...")
        run_cmd([sys.executable, "-m", "pip", "install", "paramiko"])
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
            print(f"REMOTE: {line.strip()}")
        for line in stderr:
            print(f"REMOTE ERR: {line.strip()}")
            
        print(f"\n✅ Sync Complete! Live at http://{IP}:7860")
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
