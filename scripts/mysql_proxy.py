import socket
import threading
import os

LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = int(os.getenv("MYSQL_PROXY_LISTEN_PORT", "13306"))
TARGET_HOST = os.getenv("MYSQL_PROXY_TARGET_HOST", "mysql")
TARGET_PORT = int(os.getenv("MYSQL_PROXY_TARGET_PORT", "3306"))


def pipe(src: socket.socket, dst: socket.socket):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except Exception:
            pass


def handle(client: socket.socket):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect((TARGET_HOST, TARGET_PORT))

    t1 = threading.Thread(target=pipe, args=(client, server), daemon=True)
    t2 = threading.Thread(target=pipe, args=(server, client), daemon=True)
    t1.start(); t2.start()
    t1.join(); t2.join()

    client.close()
    server.close()


def main():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((LISTEN_HOST, LISTEN_PORT))
    listener.listen(128)
    print(
        f'mysql-proxy listening on {LISTEN_HOST}:{LISTEN_PORT} -> {TARGET_HOST}:{TARGET_PORT}',
        flush=True,
    )

    while True:
        client, _ = listener.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()


if __name__ == '__main__':
    main()
