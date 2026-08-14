# SSP Sniper 🎯 (Devvit Edition)

A fully modern lead generation system built on **Reddit's Developer Platform (Devvit)**. It intercepts high-intent, high-ticket development clients on Reddit in real-time. It utilizes a Regex pre-filter to cut down noise and relies on an LLM (Groq) to qualify business leads based on strict budget and technical criteria. High-quality leads are then sent via webhook to your local terminal, where they are formatted cleanly and exported to a CSV.

## Architecture

Because Reddit's old `prefs/apps` (PRAW/Python) scripts are being phased out in favor of the new platform, SSP Sniper is now split into two components:
1. **The Devvit App (`devvit-ssp-sniper/`):** A TypeScript application that runs natively on Reddit's servers. It listens for `PostSubmit` events, runs the Regex, pings Groq, and sends a webhook.
2. **The Local Receiver (`local_receiver.py`):** A lightweight Python server running on your machine that receives the webhook from Reddit, prints the colored Rich table, and appends the lead to `qualified_leads.csv`.

## Prerequisites
- Node.js (v18+) and npm
- Python 3.9+ (with the `rich` package installed: `pip install rich`)
- A Groq API Key (`llama-3.3-70b-versatile` is used by default).
- The Devvit CLI: `npm install -g @devvit/cli`
- [ngrok](https://ngrok.com/) (or a similar tool) to expose your local receiver to the internet.

## Installation & Setup

### 1. Start the Local Receiver
Run the Python receiver in your terminal:
```bash
python local_receiver.py
```
It will start listening on port 8080.

### 2. Expose with ngrok
In a separate terminal, expose port 8080 to the internet so Reddit can reach it:
```bash
ngrok http 8080
```
*Copy the `Forwarding` URL (e.g., `https://1234-abcd.ngrok-free.app`).*

### 3. Deploy to Reddit
Navigate to the Devvit app folder:
```bash
cd devvit-ssp-sniper
```
Login to Devvit and upload your app:
```bash
devvit login
devvit upload
```
Install the app to your target subreddit (or a test sandbox subreddit):
```bash
devvit install <your-subreddit>
```

### 4. Configure App Settings
Once installed, you must configure your API keys in the Devvit settings. You can do this via the Reddit UI (Mod Tools -> Devvit Apps -> Settings) or via the CLI:
```bash
devvit settings set groq_api_key "YOUR_GROQ_KEY"
devvit settings set export_webhook_url "YOUR_NGROK_URL"
```

## How It Works
1. **Real-time Trigger:** Devvit natively detects when a new post is submitted to the subreddit.
2. **Regex Filter:** Checks Title + Body for technical pain points or hiring signals directly on Reddit's edge.
3. **LLM Qualification:** Pings Groq Cloud API with a strict system prompt to determine B2B legitimacy and budget.
4. **Handoff:** Sends a POST request to your `export_webhook_url`. Your `local_receiver.py` catches it, prints a clean formatted table in the terminal using `rich`, and appends the lead data to `qualified_leads.csv`.
