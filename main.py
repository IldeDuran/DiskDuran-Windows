"""DiskDuran – Windows native launcher using pywebview."""

import sys, os, threading, time, socket

def get_base_path():
    if getattr(sys, '_MEIPASS', None):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def start_server(port):
    base = get_base_path()
    os.environ["PORT"] = str(port)
    os.environ["DISKDURAN_BASE"] = base
    sys.path.insert(0, base)
    os.chdir(base)
    import uvicorn
    from server import app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

def wait_for_server(port, timeout=10):
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1)
            return True
        except:
            time.sleep(0.2)
    return False

def main():
    import webview

    port = find_free_port()
    server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
    server_thread.start()

    wait_for_server(port)

    window = webview.create_window(
        "DiskDuran",
        f"http://127.0.0.1:{port}",
        width=1100,
        height=750,
        min_size=(800, 600),
        background_color="#f5f5f7",
    )
    webview.start()

if __name__ == "__main__":
    main()
