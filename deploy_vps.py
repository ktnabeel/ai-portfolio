import os
import sys
import subprocess

def deploy():
    ip = "43.131.49.3"
    user = "ubuntu"
    password = "xl6DJn;^:w3kCf?@"
    
    print("Checking for paramiko...")
    try:
        import paramiko
        from scp import SCPClient
    except ImportError:
        print("Installing paramiko and scp...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "scp"])
        import paramiko
        from scp import SCPClient

    print(f"--- Starting Python Deployment to {ip} ---")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"[1/3] Connecting to {ip}...")
        ssh.connect(ip, username=user, password=password)
        
        sftp = ssh.open_sftp()
        
        print("[2/3] Uploading project files...")
        
        def mkdir_p(remote_directory):
            """Emulates mkdir -p using SFTP."""
            dirs_to_create = []
            curr = remote_directory
            while curr not in ('', '/', '.'):
                try:
                    sftp.stat(curr)
                    break
                except FileNotFoundError:
                    dirs_to_create.append(curr)
                    curr = os.path.dirname(curr).replace("\\", "/")
            
            while dirs_to_create:
                d = dirs_to_create.pop()
                print(f"  Creating remote dir: {d}")
                sftp.mkdir(d)

        # Ensure base dir exists
        mkdir_p("ai-portfolio")
        
        # Helper to fix line endings for Linux
        def fix_line_endings(local_path):
            with open(local_path, 'rb') as f:
                content = f.read()
            return content.replace(b'\r\n', b'\n')

        with SCPClient(ssh.get_transport()) as scp:
            for root, dirs, files in os.walk("."):
                rel_path = os.path.relpath(root, ".")
                if rel_path == ".":
                    rel_path = ""
                
                # Skip common heavy/unnecessary dirs
                parts = rel_path.split(os.sep)
                if any(p.startswith("__") for p in parts): continue
                if any(x in parts for x in ["dist", "node_modules", ".git", ".venv", ".pytest_cache", "__pycache__"]):
                    continue
                # Skip hidden folders except explicitly allowed ones
                if any(p.startswith(".") and p not in [".claude", ".vercel", ""] for p in parts):
                    continue

                remote_dir = os.path.join("ai-portfolio", rel_path).replace("\\", "/")
                if rel_path:
                    mkdir_p(remote_dir)
                
                for file in files:
                    if file.endswith((".pyc", ".pyo", ".log")): continue
                    # Don't upload the deployment scripts themselves to the remote root
                    if file in ["deploy_vps.py", "deploy_vps.ps1", "add_ssh_key.ps1"]: continue
                        
                    local_file = os.path.join(root, file)
                    remote_file = os.path.join(remote_dir, file).replace("\\", "/")
                    
                    try:
                        if file.endswith(".sh"):
                            # Fix line endings for shell scripts
                            fixed_content = fix_line_endings(local_file)
                            with sftp.file(remote_file, 'wb') as f:
                                f.write(fixed_content)
                            sftp.chmod(remote_file, 0o755)
                        else:
                            scp.put(local_file, remote_file)
                    except Exception as upload_err:
                        print(f"  Failed to upload {local_file}: {upload_err}")
        
        print("[3/3] Running remote setup...")
        # Force bash and disable carriage return issues
        stdin, stdout, stderr = ssh.exec_command("bash ~/ai-portfolio/remote_setup.sh")
        
        # Print output in real-time
        for line in stdout:
            print(f"REMOTE: {line.strip()}")
        for line in stderr:
            print(f"REMOTE ERROR: {line.strip()}")
        
        print(f"\nDeployment Complete! Access at http://{ip}:7860")
        
    except Exception as e:
        print(f"Critical Error: {e}")
    finally:
        if 'sftp' in locals(): sftp.close()
        ssh.close()

if __name__ == "__main__":
    deploy()
