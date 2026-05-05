
import pygame
import socket
import threading
import json
import time
import math
import random
import sys

# ============================================================
# BLOCKSTRIKE 3D ARENA - 3 Modes
#
# Installation:
#   pip install pygame
#
# Start:
#   python blockstrike_lan_arena.py
#
# Ablauf:
#   Spieler 1: HOST GAME wählen, Port z.B. 5555
#   Spieler 2: JOIN GAME wählen, IP vom Host + Port eingeben
#
# Steuerung:
#   WASD        bewegen
#   Maus        zielen/umsehen
#   Linksklick  schießen
#   R           nachladen
#   1/2/3/4     Waffen wechseln
#   ESC         zurück/Pause
#
# Hinweis:
#   In Schul-/DHBW-/Uni-WLANs kann Client-Isolation aktiv sein.
#   Dann kann Join trotz richtiger IP nicht funktionieren.
# ============================================================

pygame.init()
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
except Exception:
    pass

WIDTH, HEIGHT = 1400, 820
WIN = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED)
pygame.display.set_caption("BlockStrike LAN Arena")
CLOCK = pygame.time.Clock()
FPS = 90

WHITE = (240, 245, 255)
BLACK = (5, 6, 12)
DARK = (13, 16, 27)
PANEL = (22, 27, 43)
GREY = (110, 120, 140)
RED = (255, 70, 85)
GREEN = (80, 255, 145)
BLUE = (80, 160, 255)
CYAN = (65, 225, 255)
YELLOW = (255, 225, 95)
ORANGE = (255, 145, 55)
PURPLE = (185, 105, 255)

FONT_TINY = pygame.font.SysFont("consolas", 14)
FONT_SMALL = pygame.font.SysFont("consolas", 18)
FONT = pygame.font.SysFont("consolas", 24)
FONT_MED = pygame.font.SysFont("consolas", 36, bold=True)
FONT_BIG = pygame.font.SysFont("consolas", 68, bold=True)
FONT_HUGE = pygame.font.SysFont("consolas", 92, bold=True)

TILE = 72
MAP = [
    "########################",
    "#..........#...........#",
    "#..####....#..####.....#",
    "#..#.............#.....#",
    "#..#...##....##..#.....#",
    "#......##....##........#",
    "###..................###",
    "#....#.......#........##",
    "#....#..###..#.........#",
    "#.......#.#............#",
    "#..###..###.....###....#",
    "#......................#",
    "#....##.......##.......#",
    "#....##.......##.......#",
    "#..........#...........#",
    "#..####....#....###....#",
    "#.....#.........#......#",
    "#.....#..##..#.........#",
    "#........##..#..##.....#",
    "#...###..........#.....#",
    "#......................#",
    "########################",
]
MAP_W = len(MAP[0])
MAP_H = len(MAP)

def clamp(v, a, b):
    return max(a, min(b, v))

def dist(a, b, c, d):
    return math.hypot(c - a, d - b)

def angle_diff(a, b):
    return (a - b + math.pi) % (math.tau) - math.pi

def is_wall(x, y):
    mx = int(x // TILE)
    my = int(y // TILE)
    if mx < 0 or my < 0 or mx >= MAP_W or my >= MAP_H:
        return True
    return MAP[my][mx] == "#"

def line_of_sight(x1, y1, x2, y2):
    d = dist(x1, y1, x2, y2)
    steps = max(1, int(d / 18))
    for i in range(1, steps + 1):
        t = i / steps
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        if is_wall(x, y):
            return False
    return True

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def draw_text(surf, text, font, color, center=None, topleft=None, shadow=True):
    img = font.render(str(text), True, color)
    rect = img.get_rect()
    if center:
        rect.center = center
    if topleft:
        rect.topleft = topleft
    if shadow:
        sh = font.render(str(text), True, BLACK)
        surf.blit(sh, rect.move(3, 3))
    surf.blit(img, rect)
    return rect

class Button:
    def __init__(self, rect, text, color, action):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.action = action

    def draw(self, surf):
        mouse = pygame.mouse.get_pos()
        hover = self.rect.collidepoint(mouse)
        pygame.draw.rect(surf, self.color if hover else PANEL, self.rect, border_radius=16)
        pygame.draw.rect(surf, WHITE if hover else self.color, self.rect, 3, border_radius=16)
        draw_text(surf, self.text, FONT_MED, BLACK if hover else self.color, center=self.rect.center, shadow=False)

class InputBox:
    def __init__(self, rect, text=""):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.active = False
            else:
                ch = event.unicode
                allowed = "0123456789."
                if ch in allowed and len(self.text) < 32:
                    self.text += ch

    def draw(self, surf, label):
        draw_text(surf, label, FONT_SMALL, WHITE, topleft=(self.rect.x, self.rect.y - 28))
        pygame.draw.rect(surf, (9, 12, 22), self.rect, border_radius=10)
        pygame.draw.rect(surf, CYAN if self.active else GREY, self.rect, 2, border_radius=10)
        draw_text(surf, self.text, FONT, WHITE, topleft=(self.rect.x + 12, self.rect.y + 10), shadow=False)


class LanServer:
    """
    Stabilerer TCP-Server.
    Vorteil gegenüber UDP:
    - Der Join-Client baut eine echte Verbindung auf.
    - Wenn die Verbindung klappt, steht im Spiel deutlich connected.
    - Weniger Probleme mit dauerhaftem "connecting...".
    """
    def __init__(self, port):
        self.host = "0.0.0.0"
        self.port = int(port)
        self.sock = None
        self.running = False
        self.clients = {}
        self.next_id = 1
        self.thread = None
        self.lock = threading.Lock()
        self.error = ""

    def start(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.listen(8)
            self.running = True

            self.thread = threading.Thread(target=self.accept_loop, daemon=True)
            self.thread.start()
            return True

        except Exception as e:
            self.error = str(e)
            return False

    def stop(self):
        self.running = False

        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass

        with self.lock:
            for client in list(self.clients.values()):
                try:
                    client["conn"].close()
                except Exception:
                    pass
            self.clients.clear()

    def accept_loop(self):
        while self.running:
            try:
                conn, addr = self.sock.accept()
                conn.settimeout(0.5)

                with self.lock:
                    player_id = self.next_id
                    self.next_id += 1
                    self.clients[conn] = {
                        "id": player_id,
                        "addr": addr,
                        "state": {},
                        "last": time.time(),
                        "conn": conn,
                    }

                threading.Thread(target=self.client_loop, args=(conn,), daemon=True).start()

            except Exception:
                if not self.running:
                    break

    def client_loop(self, conn):
        buffer = ""

        while self.running:
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
                        message = json.loads(line)
                    except Exception:
                        continue

                    with self.lock:
                        if conn not in self.clients:
                            break

                        self.clients[conn]["state"] = message
                        self.clients[conn]["last"] = time.time()
                        my_id = self.clients[conn]["id"]

                        # tote Clients entfernen
                        dead = []
                        for c, data in self.clients.items():
                            if time.time() - data["last"] > 8:
                                dead.append(c)

                        for c in dead:
                            try:
                                c.close()
                            except Exception:
                                pass
                            self.clients.pop(c, None)

                        players = []
                        for c, data in self.clients.items():
                            if c == conn:
                                continue

                            state = dict(data["state"])
                            state["id"] = data["id"]
                            players.append(state)

                    response = {
                        "your_id": my_id,
                        "players": players,
                        "server_time": time.time(),
                    }

                    try:
                        conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
                    except Exception:
                        break

            except socket.timeout:
                continue
            except Exception:
                break

        with self.lock:
            self.clients.pop(conn, None)

        try:
            conn.close()
        except Exception:
            pass


class LanClient:
    """
    TCP-Client.
    send(...) sendet den lokalen Spielerstatus.
    Ein Hintergrundthread liest dauerhaft Antworten vom Server.
    """
    def __init__(self, ip, port):
        self.server = (ip, int(port))
        self.sock = None
        self.your_id = None
        self.remote_players = []
        self.last_recv = 0
        self.connected = False
        self.connecting = True
        self.error = ""
        self.lock = threading.Lock()
        self.recv_buffer = ""

        self.thread = threading.Thread(target=self.connect_and_read_loop, daemon=True)
        self.thread.start()

    def connect_and_read_loop(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect(self.server)
            self.sock.settimeout(0.5)

            self.connected = True
            self.connecting = False
            self.last_recv = time.time()

        except Exception as e:
            self.error = f"Verbindung fehlgeschlagen: {e}"
            self.connected = False
            self.connecting = False
            return

        while self.connected:
            try:
                chunk = self.sock.recv(8192)

                if not chunk:
                    self.connected = False
                    self.error = "Server hat die Verbindung geschlossen."
                    break

                self.recv_buffer += chunk.decode("utf-8", errors="ignore")

                while "\n" in self.recv_buffer:
                    line, self.recv_buffer = self.recv_buffer.split("\n", 1)

                    if not line.strip():
                        continue

                    try:
                        message = json.loads(line)
                    except Exception:
                        continue

                    with self.lock:
                        self.your_id = message.get("your_id")
                        self.remote_players = message.get("players", [])
                        self.last_recv = time.time()

            except socket.timeout:
                continue
            except Exception as e:
                self.connected = False
                self.error = f"Empfangsfehler: {e}"
                break

    def send(self, state):
        if not self.connected or not self.sock:
            return

        try:
            self.sock.sendall((json.dumps(state) + "\n").encode("utf-8"))
        except Exception as e:
            self.connected = False
            self.error = f"Sendefehler: {e}"

    def receive(self):
        # Wird vom Spiel weiterhin aufgerufen.
        # Bei TCP läuft der Empfang aber im Hintergrundthread.
        return

class Weapon:
    def __init__(self, name, damage, fire_rate, mag, reserve, spread, reload_time, color, pellets=1, auto=True):
        self.name = name
        self.damage = damage
        self.fire_rate = fire_rate
        self.mag_size = mag
        self.ammo = mag
        self.reserve = reserve
        self.spread = spread
        self.reload_time = reload_time
        self.color = color
        self.pellets = pellets
        self.auto = auto
        self.cooldown = 0
        self.reloading = False
        self.reload_timer = 0
        self.kick = 0

    def update(self, dt):
        self.cooldown = max(0, self.cooldown - dt)
        self.kick *= 0.82
        if self.reloading:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                need = self.mag_size - self.ammo
                take = min(need, self.reserve)
                self.ammo += take
                self.reserve -= take
                self.reloading = False

    def reload(self):
        if not self.reloading and self.ammo < self.mag_size and self.reserve > 0:
            self.reloading = True
            self.reload_timer = self.reload_time

    def can_fire(self):
        return self.cooldown <= 0 and not self.reloading and self.ammo > 0

    def fire(self):
        self.ammo -= 1
        self.cooldown = 1 / self.fire_rate
        self.kick = 1

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.angle = 0
        self.hp = 100
        self.armor = 35
        self.score = 0
        self.kills = 0
        self.speed = 300
        self.radius = 20
        self.weapon_index = 0
        self.weapons = [
            Weapon("KR-9 SMG", 16, 13.5, 34, 170, 0.030, 1.30, CYAN, pellets=1, auto=True),
            Weapon("VOLT RIFLE", 34, 5.5, 24, 120, 0.014, 1.55, ORANGE, pellets=1, auto=True),
            Weapon("BLOCK SHOTGUN", 11, 1.35, 7, 42, 0.090, 1.75, YELLOW, pellets=8, auto=False),
            Weapon("RAIL SCOUT", 74, 1.8, 6, 42, 0.004, 1.85, PURPLE, pellets=1, auto=False),
        ]
        self.damage_flash = 0
        self.hitmarker = 0
        self.shake = 0

    @property
    def weapon(self):
        return self.weapons[self.weapon_index]

    def move(self, dx, dy):
        nx = self.x + dx
        if not is_wall(nx + math.copysign(self.radius, dx if dx else 1), self.y):
            self.x = nx
        ny = self.y + dy
        if not is_wall(self.x, ny + math.copysign(self.radius, dy if dy else 1)):
            self.y = ny

    def damage(self, amount):
        if self.armor > 0:
            block = min(self.armor, amount * 0.45)
            self.armor -= block
            amount -= block * 0.7
        self.hp -= amount
        self.damage_flash = 1
        self.shake = max(self.shake, 0.8)

class Particle:
    def __init__(self, x, y, vx, vy, life, color):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.92
        self.vy *= 0.92
        self.life -= dt



class Pickup:
    def __init__(self, x, y, kind):
        self.x = x
        self.y = y
        self.kind = kind
        self.t = random.random() * 100

    @property
    def color(self):
        return {
            "health": GREEN,
            "armor": BLUE,
            "ammo": YELLOW,
        }.get(self.kind, WHITE)

    @property
    def label(self):
        return {
            "health": "+",
            "armor": "S",
            "ammo": "A",
        }.get(self.kind, "?")

    @property
    def name(self):
        return {
            "health": "Health",
            "armor": "Shield",
            "ammo": "Ammo",
        }.get(self.kind, "Pickup")

    def apply(self, player):
        if self.kind == "health":
            player.hp = min(100, player.hp + 38)

        elif self.kind == "armor":
            player.armor = min(100, player.armor + 35)

        elif self.kind == "ammo":
            for weapon in player.weapons:
                weapon.reserve += int(weapon.mag_size * 1.15)


class Bot:
    TYPES = [
        ("Runner", RED, 70, 170, 8),
        ("Striker", ORANGE, 95, 135, 13),
        ("Tank", PURPLE, 165, 85, 20),
        ("Blaster", BLUE, 90, 95, 11),
    ]

    def __init__(self, x, y, level=1):
        name, color, hp, speed, damage = random.choices(self.TYPES, weights=[4, 3, 2, 2])[0]
        self.name = name
        self.x = x
        self.y = y
        self.angle = random.random() * math.tau
        self.hp = hp + level * 8
        self.max_hp = self.hp
        self.speed = speed + level * 2
        self.damage_amt = damage + level * 0.8
        self.radius = 21
        self.color = color
        self.attack_cd = random.uniform(0.2, 1.0)
        self.wander_angle = random.random() * math.tau
        self.wander_timer = random.uniform(0.5, 1.5)
        self.dead = False

    def move(self, dx, dy):
        nx = self.x + dx
        if not is_wall(nx + math.copysign(self.radius, dx if dx else 1), self.y):
            self.x = nx
        else:
            self.wander_angle += random.uniform(0.4, 1.0)

        ny = self.y + dy
        if not is_wall(self.x, ny + math.copysign(self.radius, dy if dy else 1)):
            self.y = ny
        else:
            self.wander_angle += random.uniform(0.4, 1.0)

    def update(self, dt, game):
        if self.dead:
            return

        player = game.player
        d = dist(self.x, self.y, player.x, player.y)
        can_see = d < 900 and line_of_sight(self.x, self.y, player.x, player.y)
        self.attack_cd = max(0, self.attack_cd - dt)

        if can_see:
            self.angle = math.atan2(player.y - self.y, player.x - self.x)

            if d > 72:
                move_mul = 0.75 if self.name == "Blaster" and d < 360 else 1.0
                self.move(math.cos(self.angle) * self.speed * move_mul * dt, math.sin(self.angle) * self.speed * move_mul * dt)
            else:
                side = self.angle + math.pi / 2
                self.move(math.cos(side) * self.speed * 0.35 * dt, math.sin(side) * self.speed * 0.35 * dt)

            if d < 78 and self.attack_cd <= 0:
                player.damage(self.damage_amt)
                game.spawn_sparks(player.x, player.y, RED, 18)
                self.attack_cd = random.uniform(0.55, 0.95)

            if self.name == "Blaster" and 170 < d < 520 and self.attack_cd <= 0:
                if random.random() < 0.75:
                    player.damage(self.damage_amt * 0.75)
                    game.enemy_beam(self.x, self.y, player.x, player.y, self.color)
                    game.spawn_sparks(player.x, player.y, RED, 12)
                self.attack_cd = random.uniform(0.9, 1.35)
        else:
            self.wander_timer -= dt
            if self.wander_timer <= 0:
                self.wander_timer = random.uniform(0.5, 1.7)
                self.wander_angle = random.random() * math.tau

            self.angle = self.wander_angle
            self.move(math.cos(self.wander_angle) * self.speed * 0.28 * dt, math.sin(self.wander_angle) * self.speed * 0.28 * dt)

    def hit(self, amount, game):
        self.hp -= amount
        game.spawn_sparks(self.x, self.y, self.color, 18)

        if self.hp <= 0 and not self.dead:
            self.dead = True
            game.player.score += 110
            game.player.kills += 1
            game.spawn_sparks(self.x, self.y, self.color, 36)

            # Manchmal droppt ein Bot ein Item
            if random.random() < 0.32:
                kind = random.choices(["health", "armor", "ammo"], weights=[3, 3, 4])[0]
                game.pickups.append(Pickup(self.x, self.y, kind))


class Game:
    def __init__(self, mode="offline", network=None, server=None):
        self.mode = mode
        self.network = network
        self.server = server
        self.player = Player(2.5 * TILE, 2.5 * TILE)
        self.bots = []
        self.pickups = []
        self.wave = 1
        self.remote_shots_seen = set()
        self.last_shoot_id = 0
        self.last_net_send = 0
        self.state = "play"
        self.particles = []
        self.message = "LAN ARENA"
        self.message_timer = 2
        self.mouse_locked = False
        self.lock_mouse(True)

        if self.mode == "offline":
            self.message = "SINGLEPLAYER BOTS"
            self.message_timer = 2.0
            self.spawn_bot_wave()
        else:
            self.message = "MULTIPLAYER PVP"
            self.message_timer = 2.0

    def lock_mouse(self, val):
        self.mouse_locked = val
        pygame.mouse.set_visible(not val)
        pygame.event.set_grab(val)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.cleanup()
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEMOTION and self.state == "play":
                self.player.angle += event.rel[0] * 0.0027
                self.player.angle %= math.tau
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.cleanup()
                    return "menu"
                if event.key == pygame.K_r:
                    self.player.weapon.reload()
                if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
                    self.player.weapon_index = int(event.unicode) - 1
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.shoot()
                if event.button == 4:
                    self.player.weapon_index = (self.player.weapon_index - 1) % len(self.player.weapons)
                if event.button == 5:
                    self.player.weapon_index = (self.player.weapon_index + 1) % len(self.player.weapons)
        return None

    def cleanup(self):
        self.lock_mouse(False)
        if self.server:
            self.server.stop()

    def update(self, dt):
        keys = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pressed()

        p = self.player
        for w in p.weapons:
            w.update(dt)

        speed = p.speed * (1.35 if keys[pygame.K_LSHIFT] else 1.0)
        dx = dy = 0
        ca = math.cos(p.angle)
        sa = math.sin(p.angle)
        if keys[pygame.K_w]:
            dx += ca * speed * dt
            dy += sa * speed * dt
        if keys[pygame.K_s]:
            dx -= ca * speed * 0.8 * dt
            dy -= sa * speed * 0.8 * dt
        if keys[pygame.K_a]:
            dx += sa * speed * dt
            dy -= ca * speed * dt
        if keys[pygame.K_d]:
            dx -= sa * speed * dt
            dy += ca * speed * dt
        p.move(dx, dy)

        if mouse[0] and self.player.weapon.auto:
            self.shoot()

        p.damage_flash = max(0, p.damage_flash - dt * 2.5)
        p.hitmarker = max(0, p.hitmarker - dt * 5)
        p.shake = max(0, p.shake - dt * 6)

        for part in self.particles:
            part.update(dt)
        self.particles = [x for x in self.particles if x.life > 0]

        if self.mode == "offline":
            for bot in self.bots:
                bot.update(dt, self)

            self.bots = [bot for bot in self.bots if not bot.dead]

            if not self.bots:
                self.wave += 1
                self.spawn_bot_wave()

            for pickup in self.pickups[:]:
                pickup.t += dt

                if dist(pickup.x, pickup.y, self.player.x, self.player.y) < 48:
                    pickup.apply(self.player)
                    self.spawn_sparks(pickup.x, pickup.y, pickup.color, 22)
                    self.message = f"PICKUP: {pickup.name}"
                    self.message_timer = 0.9
                    self.pickups.remove(pickup)

        if self.mode == "multiplayer" and self.network:
            self.network.receive()
            self.send_state()
            self.handle_remote_shots()

        if p.hp <= 0:
            p.hp = 100
            p.armor = 35
            p.x, p.y = self.find_spawn()
            self.message = "RESPAWN"
            self.message_timer = 1.2

        self.message_timer = max(0, self.message_timer - dt)

    def random_empty_position(self, far_from_player=True):
        for _ in range(500):
            mx = random.randint(1, MAP_W - 2)
            my = random.randint(1, MAP_H - 2)

            if MAP[my][mx] != "#":
                x = (mx + 0.5) * TILE
                y = (my + 0.5) * TILE

                if not far_from_player or dist(x, y, self.player.x, self.player.y) > 380:
                    return x, y

        return 2.5 * TILE, 2.5 * TILE

    def spawn_bot_wave(self):
        amount = 5 + self.wave * 2

        for _ in range(amount):
            x, y = self.random_empty_position(True)
            self.bots.append(Bot(x, y, self.wave))

        # Neue Items pro Welle auf dem Boden verteilen
        pickup_amount = 4 + self.wave // 2
        for _ in range(pickup_amount):
            x, y = self.random_empty_position(True)
            kind = random.choices(["health", "armor", "ammo"], weights=[3, 3, 4])[0]
            self.pickups.append(Pickup(x, y, kind))

        self.message = f"WAVE {self.wave}"
        self.message_timer = 2.0

    def enemy_beam(self, x1, y1, x2, y2, color):
        self.spawn_sparks(x2, y2, color, 8)

    def find_spawn(self):
        spots = [(2.5, 2.5), (20.5, 19.5), (2.5, 19.5), (20.5, 2.5)]
        sx, sy = random.choice(spots)
        return sx * TILE, sy * TILE

    def send_state(self):
        now = time.time()
        if now - self.last_net_send < 1 / 30:
            return
        self.last_net_send = now
        p = self.player
        self.network.send({
            "x": p.x,
            "y": p.y,
            "angle": p.angle,
            "hp": int(p.hp),
            "armor": int(p.armor),
            "weapon": p.weapon_index,
            "score": p.score,
            "kills": p.kills,
            "shoot_id": self.last_shoot_id,
            "shoot_angle": getattr(self, "last_shoot_angle", p.angle),
            "shoot_time": getattr(self, "last_shoot_time", 0),
        })

    def handle_remote_shots(self):
        for rp in self.network.remote_players:
            sid = rp.get("shoot_id", 0)
            rid = rp.get("id", 0)
            if not sid:
                continue
            key = (rid, sid)
            if key in self.remote_shots_seen:
                continue
            self.remote_shots_seen.add(key)
            if time.time() - rp.get("shoot_time", 0) > 0.8:
                continue

            sx = rp.get("x", 0)
            sy = rp.get("y", 0)
            ang = rp.get("shoot_angle", rp.get("angle", 0))
            d = dist(sx, sy, self.player.x, self.player.y)
            if d > 1500:
                continue
            target_ang = math.atan2(self.player.y - sy, self.player.x - sx)
            diff = abs(angle_diff(target_ang, ang))
            hit_width = math.atan2(42, max(d, 1))
            if diff < hit_width and line_of_sight(sx, sy, self.player.x, self.player.y):
                damages = [16, 34, 11, 74]
                self.player.damage(damages[rp.get("weapon", 0) % 4])
                self.spawn_sparks(self.player.x, self.player.y, RED, 22)

    def shoot(self):
        p = self.player
        w = p.weapon

        if w.ammo <= 0:
            w.reload()
            return

        if not w.can_fire():
            return

        w.fire()
        p.shake = max(p.shake, 0.25)

        any_hit = False
        first_end_x = p.x + math.cos(p.angle) * 1500
        first_end_y = p.y + math.sin(p.angle) * 1500

        for pellet in range(w.pellets):
            shot_angle = p.angle + random.uniform(-w.spread, w.spread)

            if pellet == 0:
                self.last_shoot_id += 1
                self.last_shoot_angle = shot_angle
                self.last_shoot_time = time.time()

            hit, end_x, end_y = self.trace_shot(shot_angle, w.damage)
            any_hit = any_hit or hit

            if pellet == 0:
                first_end_x, first_end_y = end_x, end_y

        if any_hit:
            p.hitmarker = 1

        self.spawn_sparks(p.x + math.cos(p.angle) * 35, p.y + math.sin(p.angle) * 35, w.color, 10)

    def trace_shot(self, shot_angle, damage):
        p = self.player
        end_x = p.x + math.cos(shot_angle) * 1500
        end_y = p.y + math.sin(shot_angle) * 1500

        for step in range(50, 1500, 25):
            x = p.x + math.cos(shot_angle) * step
            y = p.y + math.sin(shot_angle) * step
            if is_wall(x, y):
                end_x, end_y = x, y
                self.spawn_sparks(x, y, GREY, 12)
                break

        hit = False

        if self.mode == "offline":
            best_bot = None
            best_score = 999999

            for bot in self.bots:
                if bot.dead:
                    continue

                d = dist(p.x, p.y, bot.x, bot.y)
                if d > 1500:
                    continue

                target_ang = math.atan2(bot.y - p.y, bot.x - p.x)
                diff = abs(angle_diff(target_ang, shot_angle))
                hit_width = math.atan2(48, max(d, 1))

                if diff < hit_width and line_of_sight(p.x, p.y, bot.x, bot.y):
                    score = d + diff * 1300
                    if score < best_score:
                        best_score = score
                        best_bot = bot

            if best_bot:
                p.score += damage
                best_bot.hit(damage, self)
                hit = True

        if self.mode == "multiplayer" and self.network:
            for rp in self.network.remote_players:
                sx = rp.get("x", 0)
                sy = rp.get("y", 0)
                d = dist(p.x, p.y, sx, sy)
                if d > 1500:
                    continue
                target_ang = math.atan2(sy - p.y, sx - p.x)
                diff = abs(angle_diff(target_ang, shot_angle))
                hit_width = math.atan2(48, max(d, 1))
                if diff < hit_width and line_of_sight(p.x, p.y, sx, sy):
                    p.score += damage
                    self.spawn_sparks(sx, sy, RED, 28)
                    hit = True
                    break

        return hit, end_x, end_y

    def spawn_sparks(self, x, y, color, amount):
        for _ in range(amount):
            a = random.random() * math.tau
            sp = random.uniform(80, 340)
            self.particles.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp, random.uniform(0.2, 0.55), color))

    def cast_ray(self, angle):
        ca = math.cos(angle)
        sa = math.sin(angle)
        x = self.player.x
        y = self.player.y
        for d in range(1, 1600, 4):
            rx = x + ca * d
            ry = y + sa * d
            if is_wall(rx, ry):
                return d, rx, ry
        return 1600, x + ca * 1600, y + sa * 1600

    def render_3d(self, surf):
        half = WIDTH // 2
        horizon = HEIGHT // 2

        for y in range(0, horizon, 4):
            t = y / horizon
            pygame.draw.rect(surf, (int(13 + 20 * t), int(20 + 30 * t), int(45 + 75 * t)), (0, y, WIDTH, 4))
        for y in range(horizon, HEIGHT, 4):
            t = (y - horizon) / horizon
            pygame.draw.rect(surf, (int(30 + 20 * t), int(31 + 20 * t), int(42 + 16 * t)), (0, y, WIDTH, 4))

        fov = math.radians(74)
        rays = 420
        scale = WIDTH / rays
        ray_depths = []

        for r in range(rays):
            ang = self.player.angle - fov / 2 + fov * r / rays
            d, hx, hy = self.cast_ray(ang)
            corrected = d * math.cos(self.player.angle - ang)
            ray_depths.append(corrected)
            wall_h = min(HEIGHT * 1.8, 65000 / max(corrected, 1))
            shade = clamp(240 / (1 + corrected * corrected * 0.000004), 35, 220)
            color = (clamp(int(65 * shade / 120), 0, 255), clamp(int(85 * shade / 120), 0, 255), clamp(int(140 * shade / 120), 0, 255))
            x = int(r * scale)
            y = int(horizon - wall_h / 2)
            pygame.draw.rect(surf, tuple(int(clamp(c, 0, 255)) for c in color), (x, y, int(scale + 1), int(wall_h)))

        self.draw_remote_players_3d(surf, fov, rays, ray_depths)
        self.draw_particles_3d(surf, fov, rays, ray_depths)

    def project(self, x, y, z=0):
        dx = x - self.player.x
        dy = y - self.player.y
        d = math.hypot(dx, dy)
        if d < 4:
            return None
        ang = math.atan2(dy, dx)
        gamma = angle_diff(ang, self.player.angle)
        fov = math.radians(74)
        if abs(gamma) > fov * 0.62:
            return None
        dist_plane = WIDTH / (2 * math.tan(fov / 2))
        sx = WIDTH / 2 + math.tan(gamma) * dist_plane
        sy = HEIGHT / 2 - z * dist_plane / d
        return sx, sy, d, gamma

    def draw_pickup_3d(self, surf, pickup, sx, sy, distance):
        size = int(clamp(3000 / max(distance, 1), 18, 82))
        bob = math.sin(pickup.t * 4) * size * 0.12
        cx = int(sx)
        cy = int(HEIGHT / 2 + 40 - size * 0.35 + bob)

        glow = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*pickup.color, 65), (size * 3 // 2, size * 3 // 2), size)
        surf.blit(glow, (cx - size * 3 // 2, cy - size * 3 // 2))

        pygame.draw.circle(surf, tuple(max(0, c - 80) for c in pickup.color), (cx, cy), int(size * 0.62))
        pygame.draw.circle(surf, pickup.color, (cx, cy), int(size * 0.46))
        pygame.draw.circle(surf, WHITE, (cx, cy), int(size * 0.32), max(2, size // 14))

        label_img = FONT_SMALL.render(pickup.label, True, BLACK)
        surf.blit(label_img, label_img.get_rect(center=(cx, cy)))

        name_img = FONT_TINY.render(pickup.name, True, WHITE)
        surf.blit(name_img, name_img.get_rect(center=(cx, cy - int(size * 0.78))))


    def draw_remote_players_3d(self, surf, fov, rays, ray_depths):
        objs = []

        if self.mode == "offline":
            for bot in self.bots:
                pr = self.project(bot.x, bot.y, 0)
                if pr:
                    objs.append((pr[2], {"id": bot.name, "x": bot.x, "y": bot.y, "angle": bot.angle, "hp": bot.hp, "weapon": 0, "bot_color": bot.color}, pr))

        if self.mode == "offline":
            for pickup in self.pickups:
                pr = self.project(pickup.x, pickup.y, 0)
                if pr:
                    objs.append((pr[2], {"pickup": pickup}, pr))

        if self.mode == "multiplayer" and self.network:
            for rp in self.network.remote_players:
                pr = self.project(rp.get("x", 0), rp.get("y", 0), 0)
                if pr:
                    objs.append((pr[2], rp, pr))

        objs.sort(reverse=True, key=lambda x: x[0])

        for d, rp, pr in objs:
            sx, sy, distance, gamma = pr
            ray = int(clamp(sx / WIDTH * len(ray_depths), 0, len(ray_depths) - 1))
            if distance > ray_depths[ray] + 40:
                continue

            if "pickup" in rp:
                self.draw_pickup_3d(surf, rp["pickup"], sx, sy, distance)
                continue

            size = int(clamp(9800 / max(distance, 1), 70, 370))
            x = int(sx - size / 2)
            floor_y = int(HEIGHT / 2 + clamp(3100 / max(distance, 1), 18, 90))
            y = int(floor_y - size)
            colors = [CYAN, ORANGE, YELLOW, PURPLE]
            col = rp.get("bot_color", colors[rp.get("weapon", 0) % len(colors)])

            shadow = pygame.Surface((int(size * 1.2), int(size * 0.26)), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 130), shadow.get_rect())
            surf.blit(shadow, (int(x - size * 0.1), int(floor_y - size * 0.09)))

            pygame.draw.rect(surf, WHITE, (x - 3, y - 3, size + 6, int(size * 1.08)), 2, border_radius=max(8, size // 15))
            pygame.draw.rect(surf, (25, 27, 38), (x + int(size*.12), y + int(size*.77), int(size*.28), int(size*.22)), border_radius=6)
            pygame.draw.rect(surf, (25, 27, 38), (x + int(size*.60), y + int(size*.77), int(size*.28), int(size*.22)), border_radius=6)
            pygame.draw.rect(surf, tuple(max(0, c - 70) for c in col), (x + int(size*.07), y + int(size*.31), int(size*.86), int(size*.48)), border_radius=10)
            pygame.draw.rect(surf, col, (x + int(size*.16), y + int(size*.36), int(size*.68), int(size*.34)), border_radius=8)
            pygame.draw.rect(surf, WHITE, (x + int(size*.24), y + int(size*.05), int(size*.52), int(size*.30)), border_radius=10)
            pygame.draw.rect(surf, BLACK, (x + int(size*.32), y + int(size*.15), int(size*.12), int(size*.06)), border_radius=3)
            pygame.draw.rect(surf, BLACK, (x + int(size*.57), y + int(size*.15), int(size*.12), int(size*.06)), border_radius=3)

            hp = clamp(rp.get("hp", 100) / 100, 0, 1)
            bw = int(size * 0.9)
            bx = int(sx - bw/2)
            by = y - 18
            pygame.draw.rect(surf, BLACK, (bx, by, bw, 8), border_radius=4)
            pygame.draw.rect(surf, GREEN if hp > .4 else RED, (bx, by, int(bw * hp), 8), border_radius=4)

            draw_text(surf, f"PLAYER {rp.get('id', '?')}", FONT_TINY, WHITE, center=(int(sx), by - 12), shadow=True)

    def draw_particles_3d(self, surf, fov, rays, ray_depths):
        for part in self.particles:
            pr = self.project(part.x, part.y, 20)
            if not pr:
                continue
            sx, sy, d, _ = pr
            ray = int(clamp(sx / WIDTH * len(ray_depths), 0, len(ray_depths) - 1))
            if d > ray_depths[ray] + 40:
                continue
            alpha = clamp(part.life / part.max_life, 0, 1)
            size = int(clamp(2300 / max(d, 1), 2, 16))
            col = tuple(int(c * alpha) for c in part.color)
            pygame.draw.circle(surf, col, (int(sx), int(sy)), size)

    def draw_weapon(self, surf):
        w = self.player.weapon
        kick = w.kick * 35
        cx = WIDTH - 330
        cy = HEIGHT - 180 + kick
        pygame.draw.rect(surf, (185, 140, 100), (cx - 80, cy + 90, 250, 42), border_radius=18)
        pygame.draw.rect(surf, (20, 23, 33), (cx - 90, cy + 35, 330, 70), border_radius=13)
        pygame.draw.rect(surf, (45, 52, 72), (cx - 68, cy + 14, 220, 48), border_radius=10)
        pygame.draw.rect(surf, (15, 17, 24), (cx + 140, cy + 55, 120, 22), border_radius=6)
        pygame.draw.rect(surf, w.color, (cx - 55, cy + 25, 145, 8), border_radius=5)
        pygame.draw.circle(surf, w.color, (cx + 265, cy + 65), 8)

    def draw_hud(self, surf):
        p = self.player
        w = p.weapon
        panel = pygame.Surface((WIDTH, 118), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 175), (0, 0, WIDTH, 118))
        surf.blit(panel, (0, HEIGHT - 118))

        pygame.draw.rect(surf, (35, 38, 50), (25, HEIGHT - 95, 310, 28), border_radius=8)
        pygame.draw.rect(surf, GREEN if p.hp > 35 else RED, (25, HEIGHT - 95, int(310 * clamp(p.hp / 100, 0, 1)), 28), border_radius=8)
        draw_text(surf, f"HP {int(p.hp)}", FONT_SMALL, WHITE, topleft=(35, HEIGHT - 90), shadow=False)

        pygame.draw.rect(surf, (35, 38, 50), (25, HEIGHT - 58, 310, 22), border_radius=8)
        pygame.draw.rect(surf, BLUE, (25, HEIGHT - 58, int(310 * clamp(p.armor / 100, 0, 1)), 22), border_radius=8)
        draw_text(surf, f"ARMOR {int(p.armor)}", FONT_TINY, WHITE, topleft=(35, HEIGHT - 55), shadow=False)

        draw_text(surf, w.name, FONT_MED, w.color, topleft=(WIDTH - 340, HEIGHT - 100))
        draw_text(surf, f"{w.ammo:02d} / {w.reserve:03d}", FONT_MED, WHITE if w.ammo > 0 else RED, topleft=(WIDTH - 340, HEIGHT - 60))
        if w.reloading:
            pygame.draw.rect(surf, YELLOW, (WIDTH - 340, HEIGHT - 22, int(250 * (1 - w.reload_timer / w.reload_time)), 7), border_radius=4)

        for i, wep in enumerate(p.weapons):
            rect = pygame.Rect(390 + i*145, HEIGHT - 96, 125, 36)
            active = i == p.weapon_index
            pygame.draw.rect(surf, wep.color if active else PANEL, rect, border_radius=10)
            pygame.draw.rect(surf, WHITE if active else wep.color, rect, 2, border_radius=10)
            draw_text(surf, f"{i+1} {wep.name}", FONT_TINY, BLACK if active else WHITE, center=rect.center, shadow=False)

        if self.mode == "offline":
            draw_text(surf, f"SINGLEPLAYER BOTS | WAVE {self.wave} | KILLS {p.kills} | BOTS {len(self.bots)}", FONT_SMALL, CYAN, topleft=(390, HEIGHT - 48))
            draw_text(surf, f"Pickups: Leben + | Shield S | Ammo A   Aktiv: {len(self.pickups)}", FONT_SMALL, WHITE, topleft=(390, HEIGHT - 24))

        if self.mode == "multiplayer" and self.network:
            if self.network.connected:
                status = "connected" if time.time() - self.network.last_recv < 3 else "connected, waiting..."
            elif self.network.connecting:
                status = "connecting..."
            else:
                status = "failed"

            draw_text(surf, f"MULTIPLAYER PVP | TCP NET: {status} | deine ID: {self.network.your_id}", FONT_SMALL, CYAN, topleft=(390, HEIGHT - 48))
            extra = f"remote players: {len(self.network.remote_players)}"
            if self.network.error and not self.network.connected:
                extra = self.network.error[:70]
            draw_text(surf, extra, FONT_SMALL, WHITE, topleft=(390, HEIGHT - 24))

        if self.message_timer > 0:
            draw_text(surf, self.message, FONT_MED, WHITE, center=(WIDTH//2, 82))

        if p.hitmarker > 0:
            pygame.draw.line(surf, RED, (WIDTH//2-22, HEIGHT//2-22), (WIDTH//2-8, HEIGHT//2-8), 3)
            pygame.draw.line(surf, RED, (WIDTH//2+22, HEIGHT//2-22), (WIDTH//2+8, HEIGHT//2-8), 3)
            pygame.draw.line(surf, RED, (WIDTH//2-22, HEIGHT//2+22), (WIDTH//2-8, HEIGHT//2+8), 3)
            pygame.draw.line(surf, RED, (WIDTH//2+22, HEIGHT//2+22), (WIDTH//2+8, HEIGHT//2+8), 3)

        if p.damage_flash > 0:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 30, 45, int(90 * p.damage_flash)))
            surf.blit(overlay, (0, 0))

    def draw_crosshair(self, surf):
        w = self.player.weapon
        spread = 14 + int(w.spread * 360) + int(w.kick * 20)
        col = RED if self.player.hitmarker > 0 else WHITE
        cx, cy = WIDTH//2, HEIGHT//2
        pygame.draw.line(surf, col, (cx-spread-14, cy), (cx-spread, cy), 2)
        pygame.draw.line(surf, col, (cx+spread, cy), (cx+spread+14, cy), 2)
        pygame.draw.line(surf, col, (cx, cy-spread-14), (cx, cy-spread), 2)
        pygame.draw.line(surf, col, (cx, cy+spread), (cx, cy+spread+14), 2)
        pygame.draw.circle(surf, col, (cx, cy), 2)

    def draw_minimap(self, surf):
        scale = 7
        x0 = WIDTH - MAP_W*scale - 20
        y0 = 20
        mm = pygame.Surface((MAP_W*scale, MAP_H*scale), pygame.SRCALPHA)
        pygame.draw.rect(mm, (0,0,0,150), mm.get_rect(), border_radius=8)
        for y, row in enumerate(MAP):
            for x, ch in enumerate(row):
                if ch == "#":
                    pygame.draw.rect(mm, (95,110,155,200), (x*scale,y*scale,scale,scale))
        pygame.draw.circle(mm, CYAN, (int(self.player.x/TILE*scale), int(self.player.y/TILE*scale)), 4)
        pygame.draw.line(mm, CYAN, (int(self.player.x/TILE*scale), int(self.player.y/TILE*scale)), (int((self.player.x/TILE + math.cos(self.player.angle)*1.1)*scale), int((self.player.y/TILE + math.sin(self.player.angle)*1.1)*scale)), 2)
        if self.mode == "offline":
            for pickup in self.pickups:
                pygame.draw.circle(mm, pickup.color, (int(pickup.x/TILE*scale), int(pickup.y/TILE*scale)), 3)

            for bot in self.bots:
                pygame.draw.circle(mm, bot.color, (int(bot.x/TILE*scale), int(bot.y/TILE*scale)), 4)

        if self.mode == "multiplayer" and self.network:
            for rp in self.network.remote_players:
                pygame.draw.circle(mm, RED, (int(rp.get("x",0)/TILE*scale), int(rp.get("y",0)/TILE*scale)), 4)
        pygame.draw.rect(mm, CYAN, mm.get_rect(), 2, border_radius=8)
        surf.blit(mm, (x0, y0))

    def render(self):
        scene = pygame.Surface((WIDTH, HEIGHT))
        self.render_3d(scene)
        self.draw_weapon(scene)
        self.draw_crosshair(scene)
        self.draw_hud(scene)
        self.draw_minimap(scene)

        sx = int(random.uniform(-8,8) * self.player.shake)
        sy = int(random.uniform(-6,6) * self.player.shake)
        WIN.fill(BLACK)
        WIN.blit(scene, (sx, sy))
        pygame.display.flip()

    def run_frame(self, dt):
        result = self.handle_events()
        if result:
            return result
        self.update(dt)
        self.render()
        return None

class Lobby:
    def __init__(self):
        self.screen = "main"
        self.local_ip = get_local_ip()
        self.ip_box = InputBox((WIDTH//2 - 220, 315, 440, 52), self.local_ip)
        self.port_box = InputBox((WIDTH//2 - 220, 410, 440, 52), "5555")
        self.message = ""
        self.buttons = []

    def main_buttons(self):
        return [
            Button((WIDTH//2 - 270, 325, 540, 62), "1  SINGLEPLAYER BOTS", GREEN, "offline"),
            Button((WIDTH//2 - 270, 410, 540, 62), "2  HOST GAME", CYAN, "host"),
            Button((WIDTH//2 - 270, 495, 540, 62), "3  JOIN GAME", ORANGE, "join"),
            Button((WIDTH//2 - 270, 580, 540, 62), "QUIT", RED, "quit"),
        ]

    def sub_buttons(self):
        if self.screen == "host":
            return [
                Button((WIDTH//2 - 245, 515, 490, 58), "START HOST", CYAN, "start_host"),
                Button((WIDTH//2 - 245, 590, 490, 58), "BACK", GREY, "back"),
            ]
        if self.screen == "join":
            return [
                Button((WIDTH//2 - 245, 515, 490, 58), "CONNECT", ORANGE, "connect"),
                Button((WIDTH//2 - 245, 590, 490, 58), "BACK", GREY, "back"),
            ]
        return []

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.screen in ("host", "join"):
                self.ip_box.handle_event(event)
                self.port_box.handle_event(event)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.screen == "main":
                        pygame.quit()
                        sys.exit()
                    else:
                        self.screen = "main"

                if event.key == pygame.K_1 and self.screen == "main":
                    return Game(mode="offline", network=None, server=None)
                if event.key == pygame.K_2 and self.screen == "main":
                    self.screen = "host"
                    self.ip_box.text = self.local_ip
                    self.message = "Gib dem anderen Spieler deine IP und den Port."
                if event.key == pygame.K_3 and self.screen == "main":
                    self.screen = "join"
                    self.message = "Gib die IP vom Host und den Port ein."

                if event.key == pygame.K_RETURN and self.screen == "join":
                    return self.connect()
                if event.key == pygame.K_RETURN and self.screen == "host":
                    return self.start_host()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for b in self.buttons:
                    if b.rect.collidepoint(event.pos):
                        if b.action == "quit":
                            pygame.quit()
                            sys.exit()
                        if b.action == "offline":
                            return Game(mode="offline", network=None, server=None)
                        if b.action == "host":
                            self.screen = "host"
                            self.ip_box.text = self.local_ip
                            self.message = "Deine IP gibst du dem anderen Spieler."
                        if b.action == "join":
                            self.screen = "join"
                            self.message = "Gib die IP vom Host und den Port ein."
                        if b.action == "back":
                            self.screen = "main"
                        if b.action == "start_host":
                            return self.start_host()
                        if b.action == "connect":
                            return self.connect()
        return None

    def start_host(self):
        try:
            port = int(self.port_box.text)
        except Exception:
            self.message = "Port muss eine Zahl sein, z.B. 5555."
            return None

        server = LanServer(port)
        if not server.start():
            self.message = "Server konnte nicht starten: " + server.error
            return None

        client = LanClient("127.0.0.1", port)
        return Game(mode="multiplayer", network=client, server=server)

    def connect(self):
        ip = self.ip_box.text.strip()
        try:
            port = int(self.port_box.text)
        except Exception:
            self.message = "Port muss eine Zahl sein, z.B. 5555."
            return None
        client = LanClient(ip, port)
        return Game(mode="multiplayer", network=client, server=None)

    def draw_bg(self):
        WIN.fill((7, 9, 18))
        t = time.time()
        for i in range(120):
            x = int((i * 113 + t * 35 * (0.4 + (i % 5)*0.07)) % WIDTH)
            y = int((i * 57 + math.sin(t + i) * 12) % HEIGHT)
            col = [CYAN, BLUE, PURPLE, ORANGE][i % 4]
            pygame.draw.circle(WIN, tuple(int(c * 0.35) for c in col), (x, y), 2 + i % 3)

    def render(self):
        self.draw_bg()
        draw_text(WIN, "BLOCKSTRIKE", FONT_HUGE, CYAN, center=(WIDTH//2, 135))
        draw_text(WIN, "LAN ARENA", FONT_BIG, WHITE, center=(WIDTH//2, 220))

        if self.screen == "main":
            draw_text(WIN, "3 Modi: Singleplayer Bots | Host Game | Join Game", FONT, WHITE, center=(WIDTH//2, 300))
            draw_text(WIN, f"Deine lokale IP vermutlich: {self.local_ip}", FONT_SMALL, GREY, center=(WIDTH//2, 335))
            self.buttons = self.main_buttons()

        elif self.screen == "host":
            draw_text(WIN, "HOST: Du startest den Server. Der andere verbindet sich mit deiner IP.", FONT, WHITE, center=(WIDTH//2, 260))
            self.ip_box.draw(WIN, "Deine IP / Info für den anderen Spieler")
            self.port_box.draw(WIN, "Port")
            draw_text(WIN, f"Gib dem anderen diese Daten: {self.local_ip}:{self.port_box.text}", FONT_SMALL, YELLOW, center=(WIDTH//2, 485))
            self.buttons = self.sub_buttons()

        elif self.screen == "join":
            draw_text(WIN, "JOIN: Gib die IP vom Host und den Port ein.", FONT, WHITE, center=(WIDTH//2, 260))
            self.ip_box.draw(WIN, "Host-IP")
            self.port_box.draw(WIN, "Port")
            self.buttons = self.sub_buttons()

        for b in self.buttons:
            b.draw(WIN)

        help_lines = [
            "Singleplayer Bots startet keinen Server und braucht kein Netzwerk.",
            "Host/Join ist PvP über TCP gegen eingeloggte Spieler im gleichen Netzwerk.",
            "DHBW-/Uni-/Gast-WLANs blockieren Geräte oft. Dann Handy-Hotspot oder eigenes WLAN nutzen.",
            "Windows/Mac-Firewall: Python für eingehende TCP-Verbindungen erlauben.",
        ]
        for i, line in enumerate(help_lines):
            draw_text(WIN, line, FONT_SMALL, GREY, center=(WIDTH//2, HEIGHT - 105 + i * 25), shadow=False)

        if self.message:
            draw_text(WIN, self.message, FONT_SMALL, YELLOW, center=(WIDTH//2, 690))

        pygame.display.flip()

    def run_frame(self, dt):
        game = self.handle_events()
        if game:
            return game
        self.render()
        return None

def main():
    lobby = Lobby()
    current = lobby

    while True:
        dt = CLOCK.tick(FPS) / 1000
        result = current.run_frame(dt)

        if isinstance(result, Game):
            current = result
        elif result == "menu":
            lobby = Lobby()
            current = lobby

if __name__ == "__main__":
    main()
