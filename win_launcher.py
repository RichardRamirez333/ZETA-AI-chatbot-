import os, sys, subprocess, webbrowser, time, threading

def open_browser():
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:3000")

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    from app import create_app
    app = create_app()
    app.run(debug=False, host="0.0.0.0", port=3000)