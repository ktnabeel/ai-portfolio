#!/usr/bin/env bash
set -e

SITE_CONF="/etc/nginx/sites-available/neurons.fyi"
NGINX_CONF="/etc/nginx/nginx.conf"
BACKUP_SUFFIX=".$(date +%Y%m%d-%H%M%S).bak"

echo "[*] Backing up configs..."
cp "$SITE_CONF" "$SITE_CONF$BACKUP_SUFFIX"
cp "$NGINX_CONF" "$NGINX_CONF$BACKUP_SUFFIX"

echo "[*] Ensuring global rate-limit zones exist in nginx.conf..."

if ! grep -q "req_limit_per_ip" "$NGINX_CONF"; then
sudo sed -i '/http {/a \
    # Abusive rate limiting zones\n\
    limit_req_zone $binary_remote_addr zone=req_limit_per_ip:20m rate=5r/s;\n\
    limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:20m;\n' "$NGINX_CONF"
fi

echo "[*] Injecting abusive rate limiting into $SITE_CONF..."

sudo awk '
/server\s*{/ && !done {
    print;
    print "    # --- Abusive rate limiting ---";
    print "    limit_req zone=req_limit_per_ip burst=10 nodelay;";
    print "    limit_conn conn_limit_per_ip 10;";
    print "";
    print "    # Block empty user agents (common for bots)";
    print "    if ($http_user_agent = \"\") { return 403; }";
    print "";
    print "    # Map bad user agents (defined in http block)";
    done=1;
    next
}
{ print }
' "$SITE_CONF" | sudo tee "$SITE_CONF.tmp" >/dev/null

sudo mv "$SITE_CONF.tmp" "$SITE_CONF"

# Ensure map for bad UAs exists in nginx.conf (http block)
if ! grep -q "map \$http_user_agent \$block_ua" "$NGINX_CONF"; then
sudo sed -i '/http {/a \
    # Block abusive/bot user agents\n\
    map $http_user_agent $block_ua {\n\
        default 0;\n\
        ~*curl 1;\n\
        ~*wget 1;\n\
        ~*python 1;\n\
        ~*bot 1;\n\
    }\n' "$NGINX_CONF"
fi

# Attach UA blocking to server block if not present
if ! grep -q "if (\$block_ua)" "$SITE_CONF"; then
sudo sed -i '/server {/a \
    if ($block_ua) { return 403; }\n' "$SITE_CONF"
fi

echo "[*] Testing Nginx config..."
sudo nginx -t

echo "[*] Reloading Nginx..."
sudo systemctl reload nginx

echo "[✓] Abusive rate limiting applied to neurons.fyi"
echo "    - 5 req/sec per IP, burst 10"
echo "    - Max 10 concurrent connections per IP"
echo "    - Blocks empty UA + curl/wget/python/*bot"

chmod +x harden-nginx.sh
sudo ./harden-nginx.sh
