# deploy_vps.ps1 - Deployment script for Windows (run locally)

$IP = "43.131.49.3"
$USER = "ubuntu"
$REMOTE_DIR = "~/ai-portfolio"

Write-Host "--- Starting Deployment to $IP ---" -ForegroundColor Cyan

# 1. Prepare files (clean up local environment if needed)
Write-Host "[1/3] Uploading project files..." -ForegroundColor Yellow
# Using scp to copy the current directory. 
# We use -r for recursive and we'll ignore some common heavy folders manually by not including them if we were using a more complex tool, 
# but for simplicity with scp we just copy.
# Note: This will prompt for the password: xl6DJn;^:w3kCf?@
scp -r . ${USER}@${IP}:${REMOTE_DIR}

# 2. Run remote setup
Write-Host "[2/3] Running remote setup and starting app..." -ForegroundColor Yellow
# This will also prompt for the password.
ssh ${USER}@${IP} "bash ${REMOTE_DIR}/remote_setup.sh"

# 3. Done
Write-Host "[3/3] Deployment process initiated." -ForegroundColor Green
Write-Host "The application is being set up on the VPS."
Write-Host "Access it at: http://$($IP):7860" -ForegroundColor Cyan
Write-Host "Password for VPS: xl6DJn;^:w3kCf?@"
