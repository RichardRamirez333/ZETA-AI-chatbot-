import sys
import threading
import time
import webview

def start_flask():
    from app import create_app
    app = create_app()
    app.run(debug=False, host="127.0.0.1", port=3000)

if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()
    time.sleep(2)
    webview.create_window(
        title="ZETA",
        url="http://127.0.0.1:3000",
        width=1280,
        height=800,
        min_size=(900, 600),
        resizable=True,
        fullscreen=False,
    )
    webview.start(debug=False, http_server=False)
    sys.exit(0)