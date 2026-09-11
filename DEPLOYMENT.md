# 🚀 Radhe Multi-Userbot Hosting & Deployment Guide

This guide explains how to deploy and run the **Radhe Multi-Userbot AutoChat Bot** 24/7 on **Railway**, **Linux VPS**, **Docker**, and **Render**.

---

## 🚂 Option 1: Railway Hosting (Recommended Cloud)

Railway automatically detects [`railway.json`](file:///f:/OPGIRLCHATBOT/railway.json) and [`nixpacks.toml`](file:///f:/OPGIRLCHATBOT/nixpacks.toml).

### Steps:
1. Go to [Railway.app](https://railway.app) and sign in with GitHub.
2. Click **New Project** ➔ **Deploy from GitHub Repo** ➔ Select your repository.
3. Go to project **Variables** tab and add the following environment variables:
   - `BOT_TOKEN`: Your main Telegram bot token from [@BotFather](https://t.me/BotFather)
   - `API_ID`: Your Telegram API ID from [my.telegram.org](https://my.telegram.org)
   - `API_HASH`: Your Telegram API Hash from [my.telegram.org](https://my.telegram.org)
   - `OWNER_ID`: Your numeric Telegram user ID (e.g. `8327313039`)
   - `MONGO_URL`: Your MongoDB connection URL
   - `OWNER_USERNAME`: Your Telegram username (without `@`)
   - `USERBOT_AUTOCHAT_DEFAULT`: `true`
   - `PORT`: `5000`
4. Railway will automatically build and deploy the bot with health check enabled on `/`.

---

## 🖥 Option 2: Linux VPS Hosting (Ubuntu / Debian)

### Method A: One-Click Automated Setup (`setup.sh`)

1. Connect to your VPS via SSH:
   ```bash
   ssh root@YOUR_VPS_IP
   ```

2. Clone your repository:
   ```bash
   git clone https://github.com/THEMOHMAYA/AyushChatBot.git
   cd AyushChatBot
   ```

3. Run the automated setup script:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

4. Configure your `.env` file:
   ```bash
   nano .env
   ```
   *(Fill in your `BOT_TOKEN`, `API_ID`, `API_HASH`, `OWNER_ID`, and `MONGO_URL`, then press `Ctrl+O`, `Enter`, `Ctrl+X` to save)*.

5. **Run in Background with Tmux**:
   ```bash
   tmux new -s radhe
   source venv/bin/activate
   python3 -m Radhe
   ```
   *(Press `Ctrl+B` then `D` to detach and leave it running 24/7 in background)*.

---

### Method B: 24/7 Background Systemd Service (Auto-Start on Reboot)

1. Copy the service file to systemd directory:
   ```bash
   sudo cp radhebot.service /etc/systemd/system/radhebot.service
   ```

2. Adjust the path if your repository is not in `/root/AyushChatBot`:
   ```bash
   sudo nano /etc/systemd/system/radhebot.service
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable radhebot
   sudo systemctl start radhebot
   ```

4. **Service Management Commands**:
   - Check bot status: `sudo systemctl status radhebot`
   - View live logs: `sudo journalctl -u radhebot -f`
   - Restart bot: `sudo systemctl restart radhebot`
   - Stop bot: `sudo systemctl stop radhebot`

---

## 🐳 Option 3: Docker & Docker Compose (VPS / Cloud)

1. Ensure Docker is installed on your server:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
   ```

2. Put your credentials in `.env`:
   ```bash
   cp sample.env .env
   nano .env
   ```

3. Start container in background:
   ```bash
   docker compose up -d --build
   ```

4. Check container logs:
   ```bash
   docker compose logs -f
   ```

---

## 🌐 Option 4: Render.com Hosting

1. Push your code to GitHub.
2. Go to [Render Dashboard](https://dashboard.render.com) ➔ **New Web Service**.
3. Connect your repository.
4. Render automatically picks up [`render.yaml`](file:///f:/OPGIRLCHATBOT/render.yaml).
5. In **Environment Variables**, add:
   `BOT_TOKEN`, `API_ID`, `API_HASH`, `OWNER_ID`, `MONGO_URL`, `OWNER_USERNAME`.
6. Click **Deploy**.
