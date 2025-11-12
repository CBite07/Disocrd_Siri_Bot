#!/usr/bin/env python3
"""
Siri Discord Bot launcher script
A simple wrapper to run main.py (checks environment and runs the bot)
"""

import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR
SRC_DIR = PROJECT_ROOT / "src"

# Load environment variables
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)

# Load src/ to sys.path
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def check_requirements():
    """Check required environment and directories"""
    print("=" * 60)
    print("Siri Discord Bot - Environment Check")
    print("=" * 60)

    # Check .env file
    if not ENV_PATH.exists():
        print(f"\nERROR: .env file not found.")
        print(f"Required location: {ENV_PATH}")
        print("Please create the file based on .env.example\n")
        print("Required environment variable:")
        print("  - SIRI_BOT_TOKEN=your_discord_bot_token")
        return False

    # Check bot token
    import os

    bot_token = os.getenv("SIRI_BOT_TOKEN") or os.getenv("BOT_TOKEN")
    if not bot_token:
        print(f"\nERROR: SIRI_BOT_TOKEN is not set in the .env file.")
        print(f"File location: {ENV_PATH}")
        return False

    # Check data directory
    data_dir = SCRIPT_DIR / "data"
    if not data_dir.exists():
        print(f"\nCreating data directory: {data_dir}")
        data_dir.mkdir(parents=True, exist_ok=True)

    # Check assets directory (for TTS features)
    assets_dir = PROJECT_ROOT / "assets"
    if not assets_dir.exists():
        print(f"Creating assets directory: {assets_dir}")
        assets_dir.mkdir(parents=True, exist_ok=True)

    print("\nEnvironment check passed.\n")
    return True


def main():
    """Main execution function"""
    # Check requirements
    if not check_requirements():
        print("\nWARNING: Complete environment setup before running.")
        sys.exit(1)

    # Add src directory to sys.path
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))

    try:
        print("=" * 60)
        print("Starting Siri Discord Bot")
        print("=" * 60)
        print("\nPress Ctrl+C to safely exit.\n")

        # Run main.py's main() function
        from main import main as bot_main

        asyncio.run(bot_main())

    except KeyboardInterrupt:
        print("\nBot stopped by user.")
        print("Bot exited safely.")
    except ImportError as e:
        print(f"\nERROR: Module import failed: {e}")
        print("Please install required packages:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error occurred: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
