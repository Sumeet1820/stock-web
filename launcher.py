"""
StockPro Launcher — EXE entry point
Starts Flask server and opens browser automatically
"""
import sys
import os
import threading
import time
import webbrowser

# Fix paths for PyInstaller bundled app
if getattr(sys, 'frozen', False):
    # Running as EXE
    BASE_DIR = sys._MEIPASS
    # Also set working dir to where EXE is located (for user data files)
    os.chdir(os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

PORT = 5000

def open_browser():
    """Open browser after server starts"""
    time.sleep(2.5)
    webbrowser.open(f'http://127.0.0.1:{PORT}')

def main():
    print("=" * 50)
    print("  StockPro - Stock Analyzer Pro")
    print("=" * 50)
    print(f"\n  Starting server on http://127.0.0.1:{PORT}")
    print("  Browser will open automatically...")
    print("\n  Press Ctrl+C to stop\n")

    # Open browser in background thread
    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    # Start Flask app
    try:
        from app import app
        app.run(
            debug=False,
            host='127.0.0.1',
            port=PORT,
            use_reloader=False,
            threaded=True,
        )
    except KeyboardInterrupt:
        print("\n  StockPro stopped.")
    except Exception as e:
        print(f"\n  Error: {e}")
        input("\n  Press Enter to exit...")

if __name__ == '__main__':
    main()
