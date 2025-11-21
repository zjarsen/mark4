# Webhook Server Deployment Guide
## Setting up telepay.swee.live

This guide will help you deploy the payment webhook server to handle automatic payment notifications.

---

## 📚 Table of Contents

1. [Understanding Webhooks](#understanding-webhooks)
2. [Server Requirements](#server-requirements)
3. [Installation Steps](#installation-steps)
4. [Testing](#testing)
5. [Troubleshooting](#troubleshooting)

---

## 🎓 Understanding Webhooks

### What is a Webhook?

A webhook is like a "reverse API call" - instead of you repeatedly asking "Is payment done?", the payment provider **automatically notifies your server** when payment completes.

### Why Do We Need It?

Without webhook:
```
User pays → ❌ Credits don't update automatically
User has to manually check or wait for scheduled check
```

With webhook:
```
User pays → ⚡ Payment provider notifies your server
         → 🤖 Server adds credits automatically
         → ✅ User sees balance updated immediately
```

### The Two URLs

1. **PAYMENT_NOTIFY_URL** (异步通知 - Async Notification)
   - URL: `https://telepay.swee.live/payment/callback`
   - Purpose: Server-to-server notification (payment provider → your server)
   - This is where the **actual processing happens**
   - Your server MUST respond with exactly `"OK"` (uppercase)

2. **PAYMENT_CALLBACK_URL** (同步跳转 - Sync Return)
   - URL: `https://telepay.swee.live/payment/return`
   - Purpose: User redirect after payment (payment page → browser redirect)
   - Just shows a friendly "Payment processing..." message
   - Credits are already added via the notify URL

---

## 🖥️ Server Requirements

Your server (`telepay.swee.live`) needs:

- [ ] Python 3.8+ installed
- [ ] Public IP address with domain pointing to it
- [ ] Port 80 (HTTP) and 443 (HTTPS) open
- [ ] SSL certificate (Let's Encrypt is free)
- [ ] Web server (nginx or Apache) for reverse proxy
- [ ] Access to upload files and run Python scripts

---

## 🚀 Installation Steps

### Step 1: Connect to Your Server

```bash
# SSH into your server
ssh user@telepay.swee.live

# Or if you have a different SSH config
ssh -i /path/to/key.pem user@your-server-ip
```

### Step 2: Upload Project Files

**Option A: Using Git** (recommended)
```bash
# On your server
cd /var/www/
git clone https://github.com/your-repo/mark4.git
cd mark4
```

**Option B: Using SCP** (from your local machine)
```bash
# From your local machine
scp -r /Users/andychoo/mark4/ user@telepay.swee.live:/var/www/mark4/
```

**Option C: Manual Upload**
- Use FileZilla, WinSCP, or similar FTP/SFTP client
- Upload the entire `mark4` folder to `/var/www/mark4/`

### Step 3: Install Dependencies on Server

```bash
# On your server
cd /var/www/mark4

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 4: Configure Environment

Make sure `.env` file is uploaded with correct settings:

```bash
# Check .env exists
cat .env | grep PAYMENT_

# Should show:
# PAYMENT_GATEWAY_URL=http://tykt.bikaiqianl-0aigongjingzhansiquanjiian-0.top
# PAYMENT_MERCHANT_ID=251158926
# PAYMENT_SECRET_KEY=bry27m7mf8lzsecy434l99mbcydz96sl
# PAYMENT_NOTIFY_URL=https://telepay.swee.live/payment/callback
# PAYMENT_CALLBACK_URL=https://telepay.swee.live/payment/return
```

### Step 5: Test Webhook Server Locally on Server

```bash
# On your server, test if webhook server starts
cd /var/www/mark4
source venv/bin/activate
python payment_webhook.py 8080

# You should see:
# Starting payment webhook server on port 8080
# Callback URL: http://localhost:8080/payment/callback
# Return URL: http://localhost:8080/payment/return
```

Press `Ctrl+C` to stop for now.

### Step 6: Set Up SSL Certificate (HTTPS)

**Using Let's Encrypt (Free & Recommended)**

```bash
# Install certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate for your domain
sudo certbot --nginx -d telepay.swee.live

# Follow prompts:
# - Enter email address
# - Agree to terms
# - Choose to redirect HTTP to HTTPS (recommended: Yes)
```

This will automatically:
- Create SSL certificate
- Configure nginx for HTTPS
- Set up auto-renewal

### Step 7: Configure Nginx Reverse Proxy

Create nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/telepay
```

Paste this configuration:

```nginx
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name telepay.swee.live;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name telepay.swee.live;

    # SSL certificates (certbot creates these)
    ssl_certificate /etc/letsencrypt/live/telepay.swee.live/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/telepay.swee.live/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Logs
    access_log /var/log/nginx/telepay.access.log;
    error_log /var/log/nginx/telepay.error.log;

    # Payment webhook endpoints
    location /payment/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout settings (important for webhook processing)
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
    }

    # Root location (optional - can serve a landing page)
    location / {
        return 200 "Payment Webhook Server - OK";
        add_header Content-Type text/plain;
    }
}
```

Enable the site:

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/telepay /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# If test passes, reload nginx
sudo systemctl reload nginx
```

### Step 8: Create Systemd Service (Auto-Start)

This makes the webhook server start automatically on boot and restart if it crashes.

```bash
sudo nano /etc/systemd/system/payment-webhook.service
```

Paste this configuration:

```ini
[Unit]
Description=Payment Webhook Server for Telegram Bot
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/mark4
Environment="PATH=/var/www/mark4/venv/bin"

# Run the webhook server
ExecStart=/var/www/mark4/venv/bin/python /var/www/mark4/payment_webhook.py 8080

# Restart on failure
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/var/log/payment-webhook.log
StandardError=append:/var/log/payment-webhook-error.log

[Install]
WantedBy=multi-user.target
```

Start the service:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start the service
sudo systemctl start payment-webhook

# Enable auto-start on boot
sudo systemctl enable payment-webhook

# Check status
sudo systemctl status payment-webhook

# Should show: Active: active (running)
```

### Step 9: Verify Deployment

**Test Health Check:**
```bash
curl https://telepay.swee.live/health

# Should return:
# {"status":"healthy","service":"payment_webhook"}
```

**Test Callback Endpoint:**
```bash
curl -X POST https://telepay.swee.live/payment/callback \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "test=data"

# Should return: FAIL (because it's not a valid payment callback)
# But this confirms the endpoint is accessible
```

**Check Logs:**
```bash
# View webhook server logs
sudo tail -f /var/log/payment-webhook.log

# View nginx logs
sudo tail -f /var/log/nginx/telepay.access.log
```

---

## 🔧 Register Webhook with Payment Provider

Now that your webhook server is running, register it with the payment provider:

### Step 1: Login to Payment Dashboard

```
URL: http://tykt.bikaiqianl-0aigongjingzhansiquanjiian-0.top/user.html
Username: sweedotlive 8078
Password: 123456
```

### Step 2: Find Webhook Settings

Look for these sections (names may vary):
- **API Settings** (API设置)
- **Callback Settings** (回调设置)
- **Notification URLs** (通知地址)
- **Webhook Configuration** (Webhook配置)

### Step 3: Register Your URLs

Enter these URLs:

**Notify URL / Async Callback** (异步通知地址):
```
https://telepay.swee.live/payment/callback
```

**Return URL / Sync Callback** (同步返回地址):
```
https://telepay.swee.live/payment/return
```

### Step 4: Test Connection (if available)

Some providers have a "Test Webhook" button. Click it to verify they can reach your server.

### Step 5: Save Settings

Make sure to **save** the configuration in the dashboard.

---

## 🧪 Testing

### Test 1: Health Check

```bash
curl https://telepay.swee.live/health
```

Expected response:
```json
{"status":"healthy","service":"payment_webhook"}
```

✅ If this works, your server is accessible from the internet.

### Test 2: End-to-End Payment Test

1. **Start your Telegram bot** (can run on your local machine or server):
   ```bash
   cd /Users/andychoo/mark4
   source venv/bin/activate
   python telegram_bot.py
   ```

2. **Open Telegram and test**:
   - Send `/start` to your bot
   - Select **5. 💳 充值积分**
   - Choose **¥10 = 30积分**
   - Click **前往支付**

3. **Complete payment**:
   - Payment page should open
   - Complete payment with test amount (if supported)
   - Or use real payment for ¥10

4. **Watch the logs** on your server:
   ```bash
   sudo tail -f /var/log/payment-webhook.log
   ```

   You should see:
   ```
   2025-11-21 15:30:45 - payment_webhook - INFO - Received payment callback: 1732174245170480
   2025-11-21 15:30:45 - payment_webhook - INFO - Successfully processed payment callback: pay_1732174245170480
   ```

5. **Verify credits added**:
   - In Telegram, select **4. 💰 查看积分余额**
   - Balance should show 30 credits

✅ If credits appear, the entire system is working!

---

## 🔍 Troubleshooting

### Problem: Health check fails

**Symptom**: `curl: (7) Failed to connect to telepay.swee.live`

**Solutions**:
1. Check DNS is pointing to your server:
   ```bash
   nslookup telepay.swee.live
   # Should return your server's IP
   ```

2. Check nginx is running:
   ```bash
   sudo systemctl status nginx
   ```

3. Check firewall allows HTTPS:
   ```bash
   sudo ufw status
   # Port 443 should be allowed
   ```

### Problem: Webhook server not running

**Symptom**: Nginx shows 502 Bad Gateway

**Solutions**:
1. Check webhook service status:
   ```bash
   sudo systemctl status payment-webhook
   ```

2. If not running, check logs:
   ```bash
   sudo journalctl -u payment-webhook -n 50
   ```

3. Common issues:
   - Python path wrong in systemd service
   - .env file missing or has wrong permissions
   - Port 8080 already in use

4. Try running manually to see errors:
   ```bash
   cd /var/www/mark4
   source venv/bin/activate
   python payment_webhook.py 8080
   ```

### Problem: Callback received but credits not added

**Symptom**: Logs show "Invalid callback signature"

**Solutions**:
1. Verify `PAYMENT_SECRET_KEY` in `.env` is correct
2. Check provider hasn't changed the secret key
3. Enable debug logging:
   ```bash
   # In .env
   LOG_LEVEL=DEBUG
   ```
   Then restart:
   ```bash
   sudo systemctl restart payment-webhook
   ```

### Problem: Payment completes but no callback received

**Symptom**: Payment works, user redirected, but no logs on webhook server

**Solutions**:
1. Check callback URLs registered correctly in provider dashboard
2. Verify provider's callback IPs are not blocked:
   ```bash
   # Allow provider's IPs in firewall
   sudo ufw allow from 8.217.105.159 to any port 443
   sudo ufw allow from 8.217.108.100 to any port 443
   sudo ufw allow from 8.217.109.125 to any port 443
   ```

3. Check nginx access logs:
   ```bash
   sudo tail -f /var/log/nginx/telepay.access.log
   ```
   If no POST requests to `/payment/callback`, provider isn't sending callbacks

---

## 📊 Monitoring

### View Real-Time Logs

```bash
# Webhook server logs
sudo tail -f /var/log/payment-webhook.log

# Nginx access logs
sudo tail -f /var/log/nginx/telepay.access.log

# System logs
sudo journalctl -u payment-webhook -f
```

### Important Log Patterns

✅ **Successful callback**:
```
INFO - Received payment callback: 1732174245170480
INFO - Successfully processed payment callback: pay_1732174245170480
```

❌ **Failed signature**:
```
ERROR - Invalid callback signature! Received: ABC..., Calculated: XYZ...
```

⚠️ **Database error**:
```
ERROR - Failed to credit user 170480 for payment pay_xxx
```

---

## 🎯 Quick Reference

### Useful Commands

```bash
# Restart webhook server
sudo systemctl restart payment-webhook

# View webhook status
sudo systemctl status payment-webhook

# View recent logs
sudo journalctl -u payment-webhook -n 100

# Test webhook endpoint
curl https://telepay.swee.live/health

# Watch logs live
sudo tail -f /var/log/payment-webhook.log

# Restart nginx
sudo systemctl restart nginx

# Test nginx config
sudo nginx -t
```

### File Locations

```
Webhook server code:     /var/www/mark4/payment_webhook.py
Environment config:      /var/www/mark4/.env
Systemd service:         /etc/systemd/system/payment-webhook.service
Nginx config:            /etc/nginx/sites-available/telepay
SSL certificates:        /etc/letsencrypt/live/telepay.swee.live/
Webhook logs:            /var/log/payment-webhook.log
Nginx logs:              /var/log/nginx/telepay.access.log
```

---

## ✅ Deployment Checklist

- [ ] Server accessible via SSH
- [ ] Python 3.8+ installed
- [ ] Project files uploaded to `/var/www/mark4/`
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with payment credentials
- [ ] SSL certificate obtained (Let's Encrypt)
- [ ] Nginx configured and running
- [ ] Systemd service created and running
- [ ] Health check passes: `curl https://telepay.swee.live/health`
- [ ] Webhook URLs registered in payment provider dashboard
- [ ] Test payment completed successfully
- [ ] Credits added to test user account

---

## 🎉 Success Indicators

You'll know everything is working when:

1. ✅ `curl https://telepay.swee.live/health` returns `{"status":"healthy"}`
2. ✅ User completes payment and credits appear automatically
3. ✅ Webhook logs show successful callback processing
4. ✅ Transaction history in Telegram shows the top-up

---

## 📞 Need Help?

If you get stuck:

1. Check the logs first (they usually tell you what's wrong)
2. Verify each step was completed
3. Test each component individually (nginx → webhook server → payment)
4. Check firewall and DNS settings

The most common issues are:
- Firewall blocking port 443
- Wrong file permissions (should be readable by www-data)
- .env file not uploaded or has wrong values
- Webhook URLs not registered with payment provider

Good luck with your deployment! 🚀