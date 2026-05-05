
import socket
import threading
import json
import time

HOST = "0.0.0.0"
PORT = 5555

clients = {}
next_id = 1
lock = threading.Lock()


def client_loop(conn, addr, player_id):
    print(f"[+] Spieler {player_id} verbunden: {addr[0]}:{addr[1]}")
    buffer = ""

    while True:
        try:
            chunk = conn.recv(8192)

            if not chunk:
                break

            buffer += chunk.decode("utf-8", errors="ignore")

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)

                if not line.strip():
                    continue

                try:
                    state = json.loads(line)
                except Exception:
                    continue

                with lock:
                    if conn not in clients:
                        break

                    clients[conn]["state"] = state
                    clients[conn]["last"] = time.time()

                    dead = []
                    for c, data in clients.items():
                        if time.time() - data["last"] > 10:
                            dead.append(c)

                    for c in dead:
                        try:
                            c.close()
                        except Exception:
                            pass
                        clients.pop(c, None)

                    players = []
                    for c, data in clients.items():
                        if c == conn:
                            continue

                        other_state = dict(data["state"])
                        other_state["id"] = data["id"]
                        players.append(other_state)

                response = {
                    "your_id": player_id,
                    "players": players,
                    "server_time": time.time(),
                }

                try:
                    conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
                except Exception:
                    break

        except Exception:
            break

    print(f"[-] Spieler {player_id} getrennt: {addr[0]}:{addr[1]}")

    with lock:
        clients.pop(conn, None)

    try:
        conn.close()
    except Exception:
        pass


def main():
    global next_id

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(8)

    print("==============================================")
    print(" BlockStrike TCP Server läuft")
    print(f" Port: {PORT}")
    print(" Host-IP herausfinden:")
    print("   Mac:     ipconfig getifaddr en0")
    print("   Windows: ipconfig")
    print(" Dann im Spiel JOIN GAME nutzen.")
    print("==============================================")

    while True:
        conn, addr = server.accept()

        with lock:
            player_id = next_id
            next_id += 1
            clients[conn] = {
                "id": player_id,
                "addr": addr,
                "state": {},
                "last": time.time(),
            }

        threading.Thread(target=client_loop, args=(conn, addr, player_id), daemon=True).start()


if __name__ == "__main__":
    main()
