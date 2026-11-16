name: Auto Post Baduy Reels 3x Daily

on:
  schedule:
    - cron: "0 0 * * *"
    - cron: "0 5 * * *"
    - cron: "30 12 * * *"
  workflow_dispatch:

jobs:
  publish-reel:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install requests anthropic google-api-python-client google-auth

      - name: Run Auto-Post Script
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          CLAUDE_MODEL: "claude-haiku-4-5"
          FB_PAGE_ID: ${{ secrets.FB_PAGE_ID }}
          FB_PAGE_ACCESS_TOKEN: ${{ secrets.FB_PAGE_ACCESS_TOKEN }}
          GDRIVE_QUEUE_FOLDER_ID: ${{ secrets.GDRIVE_QUEUE_FOLDER_ID }}
          GDRIVE_DONE_FOLDER_ID: ${{ secrets.GDRIVE_DONE_FOLDER_ID }}
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
        run: python fb_reels_autopost.py
