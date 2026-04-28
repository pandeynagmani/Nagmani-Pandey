"""
SANT Digital Solution - Maa Kamala Public School ERP
Main entry point for the application.
"""
import socket
import webbrowser
import threading

from app import create_app

app = create_app()


def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def open_browser(port):
    """Open the default browser after a short delay."""
    import time
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{port}")


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 5000

    local_ip = get_local_ip()

    print("=" * 60)
    print("  SANT Digital Solution - School ERP")
    print("  Maa Kamala Public School | Rokdi, Karchhana, Prayagraj")
    print("=" * 60)
    print(f"  Server running at:")
    print(f"    Local:   http://127.0.0.1:{port}")
    print(f"    Network: http://{local_ip}:{port}")
    print()
    print("  Default Login:")
    print("    Username: principal")
    print("    Password: admin123")
    print()
    print("  Other devices on the same Wi-Fi can connect using")
    print(f"  the Network URL: http://{local_ip}:{port}")
    print("=" * 60)

    # Open browser automatically
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    app.run(host=host, port=port, debug=False)
