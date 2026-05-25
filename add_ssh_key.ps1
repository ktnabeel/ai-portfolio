# add_ssh_key.ps1 - Helper to add your public key to the VPS for passwordless login

$IP = "43.131.49.3"
$USER = "ubuntu"
$KEY_PATH = "..\tencent_vps_key\tencent_ssh_key.txt"

if (Test-Path $KEY_PATH) {
    $pubKey = Get-Content $KEY_PATH
    Write-Host "Adding public key to VPS..." -ForegroundColor Yellow
    # Note: This will prompt for the password: xl6DJn;^:w3kCf?@
    ssh ${USER}@${IP} "mkdir -p ~/.ssh && echo '$pubKey' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && chmod 700 ~/.ssh"
    Write-Host "Public key added successfully. Future logins may not require a password if your private key is configured." -ForegroundColor Green
} else {
    Write-Host "Public key file not found at $KEY_PATH. Please ensure the path is correct relative to this project." -ForegroundColor Red
}
