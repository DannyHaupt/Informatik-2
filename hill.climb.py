"""
Hill Climb Style – Better Deluxe Edition
========================================
Eine deutlich schönere, besser steuerbare Pygame-Version im Stil eines Hill-Climb-Racers.

Wichtig:
- Das Fahrzeug fährt jetzt mit Gas sauber nach RECHTS.
- Die Kamera folgt ruhiger.
- Das Auto ist deutlich detaillierter gezeichnet.
- Terrain, Himmel, Münzen, Sprit, Garage und HUD sind optisch mehr Arcade/Cartoon.
- Alles bleibt in einer Datei, damit du es direkt in VS Code starten kannst.

Installation:
    python3 -m pip install pygame

Start:
    python3 hill_climb_racing_like_pygame.py

Steuerung im Spiel:
    D / Pfeil rechts       Gas nach rechts
    A / Pfeil links        Bremse / Rückwärts
    Leertaste              Luftkontrolle / Handbremse
    R                      Neustart
    Enter nach Crash       Zur Garage
    ESC                    Zurück ins Menü

Menü:
    Pfeiltasten / WASD     Auswahl ändern
    Enter                  Auswählen / Kaufen
    ESC                    Zurück
"""

import pygame
import math
import random
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

pygame.init()
pygame.display.set_caption("Hill Climb Style – Better Deluxe")

# ============================================================
# BASIS
# ============================================================

WIDTH, HEIGHT = 1280, 720
FPS = 60
SAVE_FILE = "hill_climb_better_save.json"
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
CLOCK = pygame.time.Clock()
Vec2 = pygame.math.Vector2

# Farben im cartoonigen Stil
WHITE = (250, 250, 245)
BLACK = (12, 14, 20)
INK = (32, 35, 42)
DARK = (20, 26, 42)
DARK_BLUE = (30, 50, 88)
PANEL = (35, 45, 70)
PANEL_2 = (45, 58, 88)
GREY = (120, 130, 145)
LIGHT = (220, 230, 240)
YELLOW = (255, 214, 56)
YELLOW_DARK = (205, 140, 25)
ORANGE = (255, 135, 45)
RED = (235, 64, 54)
GREEN = (72, 215, 95)
GREEN_DARK = (38, 135, 60)
BLUE = (75, 150, 245)
CYAN = (90, 220, 255)
BROWN = (120, 78, 42)
DIRT = (128, 84, 47)
DIRT_DARK = (82, 52, 32)
GRASS = (72, 205, 85)
GRASS_DARK = (40, 140, 55)

FONT_SMALL = pygame.font.SysFont("arial", 18, bold=True)
FONT = pygame.font.SysFont("arial", 26, bold=True)
FONT_BIG = pygame.font.SysFont("arial", 46, bold=True)
FONT_HUGE = pygame.font.SysFont("arial", 74, bold=True)

# ============================================================
# HELFER
# ============================================================

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(t):
    t = clamp(t, 0, 1)
    return t * t * (3 - 2 * t)


def draw_text(surface, text, font, color, x, y, center=False, shadow=True):
    text = str(text)
    if shadow:
        img_s = font.render(text, True, (0, 0, 0))
        rect_s = img_s.get_rect()
        if center:
            rect_s.center = (x + 3, y + 3)
        else:
            rect_s.topleft = (x + 3, y + 3)
        surface.blit(img_s, rect_s)
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)
    return rect


def money(n):
    return f"{int(n):,}".replace(",", ".")


def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
    except Exception:
        pass
    return json.loads(json.dumps(default))


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print("Save error:", e)


def rotate_point(point: Vec2, angle: float):
    c, s = math.cos(angle), math.sin(angle)
    return Vec2(point.x * c - point.y * s, point.x * s + point.y * c)


def draw_rot_poly(surface, points, origin, angle, color, outline=INK, width=3):
    pts = []
    for p in points:
        rp = rotate_point(Vec2(p), angle) + origin
        pts.append((rp.x, rp.y))
    pygame.draw.polygon(surface, color, pts)
    if outline and width:
        pygame.draw.polygon(surface, outline, pts, width)
    return pts


def draw_rot_rect(surface, center, size, angle, color, outline=INK, width=3, radius_hint=False):
    w, h = size
    points = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    return draw_rot_poly(surface, points, Vec2(center), angle, color, outline, width)

# ============================================================
# DATEN
# ============================================================

@dataclass
class VehicleDef:
    key: str
    name: str
    price: int
    main: Tuple[int, int, int]
    second: Tuple[int, int, int]
    body_w: float
    body_h: float
    wheel_r: float
    wheel_base: float
    mass: float
    engine: float
    brake: float
    grip: float
    suspension: float
    fuel: float
    desc: str


VEHICLES: Dict[str, VehicleDef] = {
    "jeep": VehicleDef("jeep", "Hill Jeep", 0, (72, 188, 76), (42, 122, 48), 108, 40, 20, 84, 1.0, 1280, 900, 1.03, 0.92, 100, "Solider Allrounder. Gut für den Anfang."),
    "buggy": VehicleDef("buggy", "Desert Buggy", 14000, (255, 182, 56), (205, 92, 36), 118, 34, 22, 94, 0.82, 1460, 760, 1.08, 1.05, 86, "Leicht, schnell, sehr sprunghaft."),
    "truck": VehicleDef("truck", "Monster Truck", 36000, (70, 150, 245), (32, 82, 170), 132, 48, 29, 106, 1.35, 1580, 980, 1.00, 0.95, 130, "Stabil, stark und gut auf grobem Boden."),
    "rally": VehicleDef("rally", "Rally Car", 70000, (235, 58, 70), (140, 28, 42), 124, 34, 20, 96, 0.78, 1720, 860, 1.16, 0.82, 78, "Schnell, aber nicht sehr fehlerverzeihend."),
}

@dataclass
class LevelDef:
    key: str
    name: str
    price: int
    seed: int
    hill: float
    rough: float
    sky1: Tuple[int, int, int]
    sky2: Tuple[int, int, int]
    dirt: Tuple[int, int, int]
    dirt_dark: Tuple[int, int, int]
    grass: Tuple[int, int, int]
    gravity: float
    fuel_gap: int
    coin_mult: float
    desc: str


LEVELS: Dict[str, LevelDef] = {
    "country": LevelDef("country", "Countryside", 0, 7, 0.82, 0.48, (70, 150, 238), (175, 226, 255), (130, 82, 42), (80, 50, 30), (72, 210, 82), 760, 850, 1.0, "Grüne Hügel, ideal zum Lernen."),
    "desert": LevelDef("desert", "Desert", 22000, 37, 0.60, 0.35, (236, 130, 70), (255, 212, 120), (158, 108, 55), (100, 70, 42), (225, 174, 76), 760, 1050, 1.25, "Weite Dünen und lange Sprünge."),
    "snow": LevelDef("snow", "Snow", 42000, 88, 0.95, 0.42, (90, 135, 190), (215, 240, 255), (175, 185, 195), (120, 130, 145), (235, 245, 250), 760, 780, 1.45, "Rutschig und kalt. Mehr Gefühl nötig."),
    "moon": LevelDef("moon", "Moon", 65000, 133, 1.20, 0.38, (8, 9, 28), (54, 60, 88), (98, 98, 108), (58, 58, 70), (150, 150, 160), 300, 1300, 1.65, "Wenig Schwerkraft, große Flugphasen."),
}

DEFAULT_SAVE = {
    "coins": 5000,
    "selected_vehicle": "jeep",
    "selected_level": "country",
    "owned_vehicles": ["jeep"],
    "owned_levels": ["country"],
    "best": {},
    "upgrades": {
        "jeep": {"engine": 1, "tires": 1, "suspension": 1, "fuel": 1},
        "buggy": {"engine": 1, "tires": 1, "suspension": 1, "fuel": 1},
        "truck": {"engine": 1, "tires": 1, "suspension": 1, "fuel": 1},
        "rally": {"engine": 1, "tires": 1, "suspension": 1, "fuel": 1},
    },
}

# ============================================================
# SAVEGAME
# ============================================================

class SaveGame:
    def __init__(self):
        self.data = load_json(SAVE_FILE, DEFAULT_SAVE)
        self.fix()

    def fix(self):
        for k, v in DEFAULT_SAVE.items():
            self.data.setdefault(k, json.loads(json.dumps(v)))
        for vk in VEHICLES:
            self.data["upgrades"].setdefault(vk, {"engine": 1, "tires": 1, "suspension": 1, "fuel": 1})
        if self.data["selected_vehicle"] not in VEHICLES:
            self.data["selected_vehicle"] = "jeep"
        if self.data["selected_level"] not in LEVELS:
            self.data["selected_level"] = "country"
        self.save()

    def save(self):
        save_json(SAVE_FILE, self.data)

    @property
    def coins(self):
        return int(self.data.get("coins", 0))

    def add_coins(self, amount):
        self.data["coins"] = self.coins + int(amount)
        self.save()

    def spend(self, amount):
        amount = int(amount)
        if self.coins >= amount:
            self.data["coins"] = self.coins - amount
            self.save()
            return True
        return False

    def upgrade_cost(self, vehicle, kind):
        lvl = self.data["upgrades"][vehicle][kind]
        return int(750 + (lvl ** 2.15) * 950 + VEHICLES[vehicle].price * 0.035)

    def buy_upgrade(self, vehicle, kind):
        lvl = self.data["upgrades"][vehicle][kind]
        if lvl >= 12:
            return False
        cost = self.upgrade_cost(vehicle, kind)
        if self.spend(cost):
            self.data["upgrades"][vehicle][kind] += 1
            self.save()
            return True
        return False

    def select_or_buy_vehicle(self, key):
        if key in self.data["owned_vehicles"]:
            self.data["selected_vehicle"] = key
            self.save()
            return True
        if self.spend(VEHICLES[key].price):
            self.data["owned_vehicles"].append(key)
            self.data["selected_vehicle"] = key
            self.save()
            return True
        return False

    def select_or_buy_level(self, key):
        if key in self.data["owned_levels"]:
            self.data["selected_level"] = key
            self.save()
            return True
        if self.spend(LEVELS[key].price):
            self.data["owned_levels"].append(key)
            self.data["selected_level"] = key
            self.save()
            return True
        return False

    def record_best(self, level, dist):
        old = self.data["best"].get(level, 0)
        if dist > old:
            self.data["best"][level] = int(dist)
            self.save()

# ============================================================
# TERRAIN
# ============================================================

class Terrain:
    def __init__(self, level: LevelDef):
        self.level = level
        self.step = 24
        self.points: List[Tuple[float, float]] = []
        # sehr lange Strecke, damit es kein Ende bei ~3-4k m gibt
        self.generate(180000)

    def generate(self, length):
        rng = random.Random(self.level.seed)
        y = HEIGHT * 0.65
        vel = 0
        count = int(length // self.step) + 12
        for i in range(count):
            x = i * self.step
            long_wave = math.sin(i * 0.035 + 0.7) * 115 * self.level.hill
            mid_wave = math.sin(i * 0.092 + 2.2) * 55 * self.level.hill
            small = math.sin(i * 0.21) * 18 * self.level.rough
            noise = rng.uniform(-1, 1) * 20 * self.level.rough
            target = HEIGHT * 0.65 + long_wave + mid_wave + small + noise
            vel += (target - y) * 0.030
            vel *= 0.86
            y += vel
            y = clamp(y, HEIGHT * 0.29, HEIGHT * 0.88)
            if i < 10:
                y = lerp(HEIGHT * 0.66, y, i / 10)
            self.points.append((x, y))

    def height_at(self, x):
        if x <= 0:
            return self.points[0][1]
        i = int(x // self.step)
        if i >= len(self.points) - 1:
            return self.points[-1][1]
        x1, y1 = self.points[i]
        x2, y2 = self.points[i + 1]
        t = (x - x1) / (x2 - x1)
        return lerp(y1, y2, smoothstep(t))

    def slope_at(self, x):
        return math.atan2(self.height_at(x + 16) - self.height_at(x - 16), 32)

    def normal_at(self, x):
        dy = self.height_at(x + 12) - self.height_at(x - 12)
        tangent = Vec2(24, dy)
        if tangent.length_squared() == 0:
            return Vec2(0, -1)
        tangent = tangent.normalize()
        n = Vec2(-tangent.y, tangent.x)
        if n.y > 0:
            n = -n
        return n.normalize()

    def draw(self, surface, camera_x):
        start = max(0, int(camera_x // self.step) - 4)
        end = min(len(self.points), int((camera_x + WIDTH) // self.step) + 6)
        pts = []
        for i in range(start, end):
            x, y = self.points[i]
            pts.append((x - camera_x, y))
        if len(pts) < 2:
            return

        ground_poly = pts + [(pts[-1][0], HEIGHT + 100), (pts[0][0], HEIGHT + 100)]
        pygame.draw.polygon(surface, self.level.dirt, ground_poly)

        # dunkle Erdschicht als zweite Kontur
        lower = [(x, y + 52 + 10 * math.sin((x + camera_x) * 0.016)) for x, y in pts]
        earth_poly = lower + [(lower[-1][0], HEIGHT + 100), (lower[0][0], HEIGHT + 100)]
        pygame.draw.polygon(surface, self.level.dirt_dark, earth_poly)

        # Gras oben, dick und cartoonig
        pygame.draw.lines(surface, GRASS_DARK if self.level.key != "snow" else (185, 205, 220), False, [(x, y + 6) for x, y in pts], 12)
        pygame.draw.lines(surface, self.level.grass, False, pts, 8)
        pygame.draw.lines(surface, (245, 255, 245) if self.level.key == "snow" else (120, 245, 120), False, [(x, y - 2) for x, y in pts], 2)

        # kleine Steine/Details deterministisch nach x
        for x_screen, y in pts[::5]:
            world_x = int(x_screen + camera_x)
            if world_x % 7 == 0:
                pygame.draw.circle(surface, self.level.dirt_dark, (int(x_screen), int(y + 36)), 3)

# ============================================================
# PICKUPS UND PARTIKEL
# ============================================================

class Particle:
    def __init__(self, pos, vel, color, life, size):
        self.pos = Vec2(pos)
        self.vel = Vec2(vel)
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size

    def update(self, dt):
        self.life -= dt
        self.pos += self.vel * dt
        self.vel.y += 360 * dt
        self.vel *= 0.985

    def draw(self, surf, cam):
        if self.life <= 0:
            return
        t = self.life / self.max_life
        r = max(1, int(self.size * t))
        pygame.draw.circle(surf, self.color, (int(self.pos.x - cam), int(self.pos.y)), r)

class Coin:
    def __init__(self, x, y, value):
        self.x, self.y = x, y
        self.value = value
        self.collected = False
        self.t = random.random() * 10

    def update(self, dt):
        self.t += dt * 6

    def draw(self, surf, cam):
        if self.collected:
            return
        sx = self.x - cam
        if sx < -80 or sx > WIDTH + 80:
            return
        bob = math.sin(self.t) * 4
        scale = 0.72 + abs(math.cos(self.t)) * 0.28
        rx = max(5, int(16 * scale))
        pygame.draw.ellipse(surf, YELLOW_DARK, (sx - rx, self.y + bob - 17, rx * 2, 34))
        pygame.draw.ellipse(surf, YELLOW, (sx - rx + 3, self.y + bob - 14, rx * 2 - 6, 28))
        pygame.draw.ellipse(surf, WHITE, (sx - rx + 6, self.y + bob - 10, max(4, rx - 4), 7))
        draw_text(surf, str(self.value), FONT_SMALL, (110, 75, 0), sx, self.y + bob - 1, center=True, shadow=False)

class FuelCan:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.collected = False
        self.t = 0

    def update(self, dt):
        self.t += dt

    def draw(self, surf, cam):
        if self.collected:
            return
        sx = self.x - cam
        if sx < -80 or sx > WIDTH + 80:
            return
        bob = math.sin(self.t * 4) * 3
        rect = pygame.Rect(sx - 17, self.y - 25 + bob, 34, 46)
        pygame.draw.rect(surf, RED, rect, border_radius=6)
        pygame.draw.rect(surf, INK, rect, 3, border_radius=6)
        pygame.draw.rect(surf, (255, 150, 140), (sx - 8, self.y - 19 + bob, 14, 8), border_radius=3)
        pygame.draw.rect(surf, INK, (sx + 7, self.y - 15 + bob, 12, 10), 3, border_radius=3)
        draw_text(surf, "F", FONT, WHITE, sx, self.y + 4 + bob, center=True)

# ============================================================
# FAHRZEUG
# ============================================================

class Vehicle:
    def __init__(self, definition: VehicleDef, upgrades: Dict[str, int], level: LevelDef):
        self.d = definition
        self.up = upgrades
        self.level = level
        self.reset()

    def reset(self):
        self.pos = Vec2(180, 270)
        self.vel = Vec2(0, 0)
        self.angle = 0.0
        self.ang_vel = 0.0
        self.fuel = self.max_fuel()
        self.damage = 0.0
        self.dead = False
        self.flip_timer = 0.0
        self.distance = 0.0
        self.run_coins = 0
        self.grounded = False
        self.wheel_spin = 0.0
        self.was_air = False
        self.driver_bounce = 0.0

    def max_fuel(self):
        return self.d.fuel * (1 + 0.13 * (self.up.get("fuel", 1) - 1))

    def engine(self):
        return self.d.engine * (1 + 0.12 * (self.up.get("engine", 1) - 1))

    def grip(self):
        return self.d.grip * (1 + 0.045 * (self.up.get("tires", 1) - 1))

    def suspension(self):
        return self.d.suspension * (1 + 0.065 * (self.up.get("suspension", 1) - 1))

    def wheel_world(self):
        forward = Vec2(math.cos(self.angle), math.sin(self.angle))
        down = Vec2(-math.sin(self.angle), math.cos(self.angle))
        rear = self.pos - forward * (self.d.wheel_base / 2) + down * (self.d.body_h * 0.47)
        front = self.pos + forward * (self.d.wheel_base / 2) + down * (self.d.body_h * 0.47)
        return rear, front

    def update(self, dt, terrain: Terrain, keys, particles: List[Particle]):
        if self.dead:
            self.vel.y += self.level.gravity * dt
            self.pos += self.vel * dt
            self.ang_vel *= 0.985
            self.angle += self.ang_vel * dt
            return

        gas = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        brake = keys[pygame.K_LEFT] or keys[pygame.K_a]
        hand = keys[pygame.K_SPACE]

        # Schwerkraft
        self.vel.y += self.level.gravity * dt

        rear, front = self.wheel_world()
        contacts = []
        for name, wp in [("rear", rear), ("front", front)]:
            gy = terrain.height_at(wp.x)
            penetration = wp.y + self.d.wheel_r - gy
            if penetration > 0:
                n = terrain.normal_at(wp.x)
                contacts.append((name, wp, penetration, n))

        self.grounded = len(contacts) > 0

        # RICHTUNGSFIX – endgültig:
        # In diesem Spiel ist RECHTS immer positive x-Richtung.
        # Gas darf deshalb niemals netto nach links beschleunigen.
        # Die Fahrzeugnase wird nur für Neigung/Luftkontrolle benutzt, nicht um die Fahrtrichtung umzudrehen.
        forward = Vec2(math.cos(self.angle), math.sin(self.angle))
        right = Vec2(1, 0)

        if self.fuel > 0:
            if gas:
                power = self.engine() / self.d.mass

                # 1) Hauptantrieb hart nach rechts, damit D/Pfeil rechts IMMER rechts bedeutet.
                self.vel.x += power * 1.45 * dt

                # 2) Kleiner Anteil entlang der Wagenneigung, aber nur wenn er nach rechts zeigt.
                if forward.x > 0:
                    self.vel += forward * power * 0.34 * dt

                # 3) Falls das Auto vorher rückwärts gerutscht ist, wird das aktiv abgebaut.
                if self.vel.x < 0:
                    self.vel.x *= 0.78

                # 4) Arcade-Luftkontrolle: Gas hebt vorne leicht an, wie beim Vorbild.
                self.ang_vel -= 0.78 * dt
                self.fuel -= dt * (6.2 + abs(self.vel.x) * 0.014)

            if brake:
                brake_power = self.d.brake / self.d.mass
                self.vel.x -= brake_power * 0.82 * dt
                self.ang_vel += 0.70 * dt
                self.fuel -= dt * 1.7

        self.fuel = clamp(self.fuel, 0, self.max_fuel())

        # Kontaktphysik
        for name, wp, penetration, normal in contacts:
            spring = 1120 * self.suspension()
            push = normal * penetration * spring * dt / self.d.mass
            self.vel += push

            # vertikales Eindringen abfedern
            if self.vel.y > 0:
                self.vel.y *= 0.90

            tangent = Vec2(normal.y, -normal.x)
            if tangent.x < 0:
                tangent *= -1

            tangent_speed = self.vel.dot(tangent)
            friction = -tangent_speed * 0.055 * self.grip()
            self.vel += tangent * friction

            if gas and self.fuel > 0:
                # Hinterradantrieb: Vortrieb entlang Bodentangente, aber niemals nach links.
                drive = tangent * (self.engine() * 0.58 / self.d.mass) * dt
                if drive.x < 0:
                    drive.x = abs(drive.x)
                self.vel += drive
                self.vel.x += (self.engine() * 0.18 / self.d.mass) * dt
                self.wheel_spin += dt * 24
                if random.random() < 0.70 and abs(self.vel.x) > 25:
                    particles.append(Particle(wp, (-self.vel.x * 0.22 + random.uniform(-65, 25), random.uniform(-90, -20)), self.level.dirt_dark, 0.42, random.randint(3, 7)))

            if hand:
                self.vel.x *= 0.982

        # Winkel dem Boden annähern, aber nicht komplett festkleben
        if self.grounded:
            ground_angle = terrain.slope_at(self.pos.x)
            diff = (ground_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
            self.ang_vel += diff * 1.9 * dt * self.suspension()
            self.driver_bounce = max(self.driver_bounce, min(9, abs(self.vel.y) * 0.012))
        else:
            # Luftkontrolle fühlt sich ähnlich arcade-mäßig an
            if gas:
                self.ang_vel -= 0.95 * dt
            if brake or hand:
                self.ang_vel += 0.85 * dt

        # Bewegung begrenzen
        # Beim Gasgeben wird Rückwärtsrollen extra stark verhindert.
        if gas and self.vel.x < 0:
            self.vel.x *= 0.55
        self.vel.x = clamp(self.vel.x, -180, 720)
        self.vel.y = clamp(self.vel.y, -850, 900)
        self.vel *= 0.999
        self.pos += self.vel * dt
        self.angle += self.ang_vel * dt
        self.ang_vel *= 0.955
        self.wheel_spin += self.vel.x * dt * 0.055
        self.driver_bounce *= 0.90

        # Body-Kollision gegen Boden
        ground_body = terrain.height_at(self.pos.x)
        bottom = self.pos.y + self.d.body_h * 0.55
        if bottom > ground_body - 3:
            impact = abs(self.vel.y)
            self.pos.y = ground_body - self.d.body_h * 0.55 - 3
            self.vel.y *= -0.10
            if impact > 330:
                dmg = (impact - 410) * 0.026
                self.damage += dmg
                for _ in range(14):
                    particles.append(Particle(self.pos, (random.uniform(-190, 190), random.uniform(-220, -30)), random.choice([ORANGE, RED, YELLOW, GREY]), 0.62, random.randint(3, 7)))

        # Auto darf am Anfang nicht hinter die Startlinie fallen
        if self.pos.x < 80:
            self.pos.x = 80
            self.vel.x = max(0, self.vel.x)

        # Überschlag / Tod
        up = Vec2(-math.sin(self.angle), math.cos(self.angle))
        if self.grounded and up.y < -0.35:
            self.flip_timer += dt
        else:
            self.flip_timer = max(0, self.flip_timer - dt * 2.5)

        if self.flip_timer > 1.0:
            self.damage = 100
        if self.damage >= 100:
            self.crash(particles)

        self.distance = max(self.distance, self.pos.x / 10)

    def crash(self, particles):
        if self.dead:
            return
        self.dead = True
        for _ in range(55):
            particles.append(Particle(self.pos, (random.uniform(-320, 320), random.uniform(-320, 80)), random.choice([RED, ORANGE, YELLOW, GREY, INK]), 1.2, random.randint(3, 8)))

    def draw_wheel(self, surf, center, cam, radius):
        x, y = center.x - cam, center.y
        pygame.draw.circle(surf, INK, (int(x), int(y)), int(radius + 4))
        pygame.draw.circle(surf, (28, 31, 36), (int(x), int(y)), int(radius))
        pygame.draw.circle(surf, (70, 75, 85), (int(x), int(y)), int(radius * 0.58))
        pygame.draw.circle(surf, LIGHT, (int(x), int(y)), int(radius * 0.30))
        # Reifenprofil
        for i in range(10):
            a = self.wheel_spin + i * math.tau / 10
            p1 = Vec2(math.cos(a), math.sin(a)) * (radius * 0.70)
            p2 = Vec2(math.cos(a), math.sin(a)) * (radius * 1.02)
            pygame.draw.line(surf, BLACK, (x + p1.x, y + p1.y), (x + p2.x, y + p2.y), 3)
        # Felgenspeichen
        for i in range(5):
            a = -self.wheel_spin * 0.8 + i * math.tau / 5
            p = Vec2(math.cos(a), math.sin(a)) * radius * 0.52
            pygame.draw.line(surf, LIGHT, (x, y), (x + p.x, y + p.y), 2)

    def local_to_screen(self, local, cam):
        return rotate_point(Vec2(local), self.angle) + Vec2(self.pos.x - cam, self.pos.y)

    def draw(self, surf, cam):
        # Fahrzeug-Rendering komplett überarbeitet:
        # Jedes Auto hat jetzt eine andere Silhouette, andere Details und einen eigenen Charakter.
        rear, front = self.wheel_world()

        # Federbeine hinter der Karosserie
        for wp, lx in [(rear, -self.d.wheel_base / 2), (front, self.d.wheel_base / 2)]:
            top = self.local_to_screen((lx, self.d.body_h * 0.11), cam)
            pygame.draw.line(surf, INK, (top.x, top.y), (wp.x - cam, wp.y), 7)
            pygame.draw.line(surf, LIGHT, (top.x, top.y), (wp.x - cam, wp.y), 3)

        self.draw_wheel(surf, rear, cam, self.d.wheel_r)
        self.draw_wheel(surf, front, cam, self.d.wheel_r)

        origin = Vec2(self.pos.x - cam, self.pos.y)
        w, h = self.d.body_w, self.d.body_h

        def col_plus(col, add):
            return tuple(clamp(c + add, 0, 255) for c in col)

        def draw_shadow(points, off=(5, 6)):
            draw_rot_poly(surf, points, origin + Vec2(off), self.angle, (0, 0, 0), None, 0)

        def draw_lamp(local, color, r=7):
            p = self.local_to_screen(local, cam)
            pygame.draw.circle(surf, color, (int(p.x), int(p.y)), r)
            pygame.draw.circle(surf, INK, (int(p.x), int(p.y)), r, 2)

        # ----------------------------------------------------
        # 1) HILL JEEP: kompakter grüner Klassiker
        # ----------------------------------------------------
        if self.d.key == "jeep":
            chassis = [(-w*.57, h*.14), (w*.56, h*.14), (w*.50, h*.43), (-w*.51, h*.43)]
            draw_rot_poly(surf, chassis, origin, self.angle, self.d.second, INK, 5)

            body = [(-w*.62, h*.12), (-w*.54, -h*.26), (-w*.17, -h*.47), (w*.30, -h*.46), (w*.56, -h*.12), (w*.63, h*.28), (-w*.58, h*.34)]
            draw_shadow(body)
            draw_rot_poly(surf, body, origin, self.angle, self.d.main, INK, 5)

            hood = [(-w*.55, -h*.03), (-w*.30, -h*.25), (-w*.04, -h*.28), (-w*.10, h*.05)]
            draw_rot_poly(surf, hood, origin, self.angle, col_plus(self.d.main, 38), None, 0)

            window = [(-w*.08, -h*.39), (w*.26, -h*.38), (w*.38, -h*.08), (-w*.02, -h*.07)]
            draw_rot_poly(surf, window, origin, self.angle, (112, 218, 248), INK, 4)
            shine = [(-w*.02, -h*.33), (w*.11, -h*.32), (w*.03, -h*.14), (-w*.10, -h*.14)]
            draw_rot_poly(surf, shine, origin, self.angle, (232, 255, 255), None, 0)

            # Fahrer
            head = self.local_to_screen((w*.15, -h*.49 - self.driver_bounce), cam)
            helmet = self.local_to_screen((w*.12, -h*.56 - self.driver_bounce), cam)
            pygame.draw.circle(surf, (244, 185, 126), (int(head.x), int(head.y)), 11)
            pygame.draw.circle(surf, INK, (int(head.x), int(head.y)), 11, 3)
            pygame.draw.circle(surf, self.d.second, (int(helmet.x), int(helmet.y)), 12)
            pygame.draw.circle(surf, INK, (int(helmet.x), int(helmet.y)), 12, 3)

            # Ersatzrad hinten
            spare = self.local_to_screen((-w*.55, -h*.12), cam)
            pygame.draw.circle(surf, INK, (int(spare.x), int(spare.y)), 15)
            pygame.draw.circle(surf, (45, 48, 55), (int(spare.x), int(spare.y)), 11)
            pygame.draw.circle(surf, LIGHT, (int(spare.x), int(spare.y)), 5)

            draw_lamp((w*.60, -h*.02), YELLOW, 7)
            draw_lamp((-w*.60, h*.02), RED, 6)

        # ----------------------------------------------------
        # 2) DESERT BUGGY: offener Käfig, sportlich, sandig
        # ----------------------------------------------------
        elif self.d.key == "buggy":
            chassis = [(-w*.58, h*.18), (w*.58, h*.18), (w*.46, h*.42), (-w*.50, h*.42)]
            draw_rot_poly(surf, chassis, origin, self.angle, self.d.second, INK, 5)

            base = [(-w*.60, h*.10), (-w*.42, -h*.18), (-w*.05, -h*.28), (w*.43, -h*.20), (w*.60, h*.13), (w*.52, h*.32), (-w*.56, h*.33)]
            draw_shadow(base)
            draw_rot_poly(surf, base, origin, self.angle, self.d.main, INK, 5)

            # Überrollkäfig statt Dach
            cage_points = [(-w*.23, -h*.16), (-w*.05, -h*.55), (w*.28, -h*.50), (w*.43, -h*.18)]
            screen_pts = []
            for p in cage_points:
                sp = self.local_to_screen(p, cam)
                screen_pts.append(sp)
            for a, b in [(0,1), (1,2), (2,3), (0,3), (1,3)]:
                pygame.draw.line(surf, INK, (screen_pts[a].x, screen_pts[a].y), (screen_pts[b].x, screen_pts[b].y), 7)
                pygame.draw.line(surf, LIGHT, (screen_pts[a].x, screen_pts[a].y), (screen_pts[b].x, screen_pts[b].y), 3)

            # Sitz und Fahrer sichtbar
            seat = [(-w*.06, -h*.10), (w*.16, -h*.12), (w*.10, h*.17), (-w*.12, h*.13)]
            draw_rot_poly(surf, seat, origin, self.angle, (55, 45, 38), INK, 3)
            head = self.local_to_screen((w*.10, -h*.43 - self.driver_bounce), cam)
            helmet = self.local_to_screen((w*.08, -h*.50 - self.driver_bounce), cam)
            pygame.draw.circle(surf, (244, 185, 126), (int(head.x), int(head.y)), 10)
            pygame.draw.circle(surf, INK, (int(head.x), int(head.y)), 10, 3)
            pygame.draw.circle(surf, ORANGE, (int(helmet.x), int(helmet.y)), 12)
            pygame.draw.circle(surf, INK, (int(helmet.x), int(helmet.y)), 12, 3)

            # Front-Nase und Flagge
            nose = [(w*.18, -h*.14), (w*.62, -h*.02), (w*.48, h*.12), (w*.14, h*.04)]
            draw_rot_poly(surf, nose, origin, self.angle, col_plus(self.d.main, 35), INK, 3)
            mast_a = self.local_to_screen((-w*.42, -h*.18), cam)
            mast_b = self.local_to_screen((-w*.42, -h*.68), cam)
            pygame.draw.line(surf, INK, (mast_a.x, mast_a.y), (mast_b.x, mast_b.y), 4)
            flag = [(-w*.42, -h*.68), (-w*.20, -h*.60), (-w*.42, -h*.52)]
            draw_rot_poly(surf, flag, origin, self.angle, RED, INK, 2)

            draw_lamp((w*.58, -h*.06), YELLOW, 6)
            draw_lamp((-w*.59, h*.03), RED, 6)

        # ----------------------------------------------------
        # 3) MONSTER TRUCK: groß, hoch, bullig
        # ----------------------------------------------------
        elif self.d.key == "truck":
            # dicke Achsen
            rear_s = Vec2(rear.x - cam, rear.y)
            front_s = Vec2(front.x - cam, front.y)
            pygame.draw.line(surf, INK, (rear_s.x, rear_s.y), (front_s.x, front_s.y), 9)
            pygame.draw.line(surf, LIGHT, (rear_s.x, rear_s.y), (front_s.x, front_s.y), 3)

            chassis = [(-w*.58, h*.20), (w*.58, h*.20), (w*.52, h*.48), (-w*.53, h*.48)]
            draw_rot_poly(surf, chassis, origin, self.angle, self.d.second, INK, 5)

            cabin = [(-w*.52, h*.04), (-w*.48, -h*.30), (-w*.14, -h*.52), (w*.18, -h*.50), (w*.38, -h*.16), (w*.54, -h*.07), (w*.62, h*.22), (-w*.55, h*.29)]
            draw_shadow(cabin, (6, 7))
            draw_rot_poly(surf, cabin, origin, self.angle, self.d.main, INK, 6)

            # Ladefläche/Seitenteil
            bed = [(-w*.58, -h*.05), (-w*.22, -h*.18), (-w*.18, h*.18), (-w*.60, h*.24)]
            draw_rot_poly(surf, bed, origin, self.angle, col_plus(self.d.second, 20), INK, 4)
            stripe = [(-w*.45, h*.02), (w*.45, h*.02), (w*.49, h*.13), (-w*.50, h*.15)]
            draw_rot_poly(surf, stripe, origin, self.angle, (235, 245, 255), None, 0)

            window = [(-w*.06, -h*.39), (w*.18, -h*.38), (w*.31, -h*.14), (w*.02, -h*.10)]
            draw_rot_poly(surf, window, origin, self.angle, (120, 215, 247), INK, 4)
            # Auspuffrohre
            for lx in [-w*.35, -w*.29]:
                a = self.local_to_screen((lx, -h*.35), cam)
                b = self.local_to_screen((lx, -h*.75), cam)
                pygame.draw.line(surf, INK, (a.x, a.y), (b.x, b.y), 7)
                pygame.draw.line(surf, GREY, (a.x, a.y), (b.x, b.y), 4)

            head = self.local_to_screen((w*.13, -h*.47 - self.driver_bounce), cam)
            pygame.draw.circle(surf, (244, 185, 126), (int(head.x), int(head.y)), 10)
            pygame.draw.circle(surf, INK, (int(head.x), int(head.y)), 10, 3)

            draw_lamp((w*.61, -h*.03), YELLOW, 8)
            draw_lamp((-w*.60, h*.04), RED, 7)

        # ----------------------------------------------------
        # 4) RALLY CAR: flach, schnell, Spoiler, Rally-Streifen
        # ----------------------------------------------------
        elif self.d.key == "rally":
            chassis = [(-w*.58, h*.17), (w*.60, h*.17), (w*.54, h*.37), (-w*.55, h*.37)]
            draw_rot_poly(surf, chassis, origin, self.angle, self.d.second, INK, 5)

            body = [(-w*.63, h*.12), (-w*.48, -h*.12), (-w*.18, -h*.40), (w*.20, -h*.42), (w*.54, -h*.15), (w*.64, h*.12), (w*.52, h*.29), (-w*.57, h*.30)]
            draw_shadow(body)
            draw_rot_poly(surf, body, origin, self.angle, self.d.main, INK, 5)

            # flache Scheiben
            windshield = [(-w*.17, -h*.34), (w*.18, -h*.34), (w*.34, -h*.10), (-w*.05, -h*.09)]
            draw_rot_poly(surf, windshield, origin, self.angle, (105, 210, 250), INK, 4)

            # Rally-Streifen
            stripe1 = [(-w*.52, -h*.03), (w*.53, -h*.08), (w*.57, h*.03), (-w*.55, h*.10)]
            stripe2 = [(-w*.50, h*.10), (w*.47, h*.04), (w*.50, h*.11), (-w*.52, h*.19)]
            draw_rot_poly(surf, stripe1, origin, self.angle, WHITE, None, 0)
            draw_rot_poly(surf, stripe2, origin, self.angle, YELLOW, None, 0)

            # Spoiler hinten
            s1 = self.local_to_screen((-w*.60, -h*.18), cam)
            s2 = self.local_to_screen((-w*.78, -h*.30), cam)
            s3 = self.local_to_screen((-w*.78, -h*.18), cam)
            pygame.draw.line(surf, INK, (s1.x, s1.y), (s2.x, s2.y), 5)
            spoiler = [(-w*.84, -h*.37), (-w*.54, -h*.34), (-w*.55, -h*.23), (-w*.86, -h*.25)]
            draw_rot_poly(surf, spoiler, origin, self.angle, self.d.second, INK, 4)

            # Nummer auf Tür
            door = self.local_to_screen((w*.02, h*.05), cam)
            pygame.draw.circle(surf, WHITE, (int(door.x), int(door.y)), 15)
            pygame.draw.circle(surf, INK, (int(door.x), int(door.y)), 15, 2)
            draw_text(surf, "7", FONT_SMALL, INK, door.x, door.y, center=True, shadow=False)

            head = self.local_to_screen((w*.12, -h*.45 - self.driver_bounce), cam)
            pygame.draw.circle(surf, (244, 185, 126), (int(head.x), int(head.y)), 9)
            pygame.draw.circle(surf, INK, (int(head.x), int(head.y)), 9, 3)

            draw_lamp((w*.62, -h*.03), YELLOW, 6)
            draw_lamp((-w*.62, h*.05), RED, 6)

        # Falls später ein neues Auto dazukommt: Fallback-Design
        else:
            chassis = [(-w * 0.55, h * 0.13), (w * 0.55, h * 0.13), (w * 0.48, h * 0.44), (-w * 0.50, h * 0.43)]
            draw_rot_poly(surf, chassis, origin, self.angle, self.d.second, INK, 4)
            body = [(-w * 0.60, h * 0.10), (-w * 0.49, -h * 0.36), (-w * 0.10, -h * 0.60), (w * 0.35, -h * 0.55), (w * 0.60, -h * 0.12), (w * 0.64, h * 0.30), (-w * 0.58, h * 0.34)]
            draw_shadow(body)
            draw_rot_poly(surf, body, origin, self.angle, self.d.main, INK, 5)
            window = [(-w * 0.14, -h * 0.45), (w * 0.27, -h * 0.42), (w * 0.43, -h * 0.08), (w * 0.00, -h * 0.08)]
            draw_rot_poly(surf, window, origin, self.angle, (112, 214, 246), INK, 4)

        if self.dead:
            draw_text(surf, "CRASH!", FONT_BIG, RED, origin.x, origin.y - 88, center=True)

# ============================================================
# WELT
# ============================================================

class World:
    def __init__(self, save: SaveGame):
        self.save = save
        self.level_key = save.data["selected_level"]
        self.vehicle_key = save.data["selected_vehicle"]
        self.level = LEVELS[self.level_key]
        self.vehicle_def = VEHICLES[self.vehicle_key]
        self.terrain = Terrain(self.level)
        self.vehicle = Vehicle(self.vehicle_def, save.data["upgrades"][self.vehicle_key], self.level)
        self.camera_x = 0
        self.camera_y = 0
        self.particles: List[Particle] = []
        self.coins: List[Coin] = []
        self.fuels: List[FuelCan] = []
        self.finished = False
        self.message = ""
        self.message_timer = 0
        self.make_pickups()

    def make_pickups(self):
        rng = random.Random(self.level.seed + 999)
        x = 430
        while x < 180000:
            if rng.random() < 0.78:
                y = self.terrain.height_at(x) - rng.choice([76, 96, 118, 142])
                value = rng.choice([5, 5, 5, 10, 10, 25, 50])
                self.coins.append(Coin(x, y, value))
            x += rng.randint(110, 210)
        for x in range(720, 180000, self.level.fuel_gap):
            self.fuels.append(FuelCan(x, self.terrain.height_at(x) - 52))

    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.vehicle.update(dt, self.terrain, keys, self.particles)

        # steigende Schwierigkeit mit Distanz
        if self.vehicle.distance > 1000 and not self.vehicle.dead:
            extra = 0.9 + (self.vehicle.distance - 1000) / 2500
            self.vehicle.fuel = max(0, self.vehicle.fuel - extra * dt)
        if self.vehicle.distance > 1800 and abs(self.vehicle.vel.y) > 260 and not self.vehicle.grounded:
            self.vehicle.ang_vel += math.sin(self.vehicle.distance * 0.04) * 0.018

        # Kamera: Auto bleibt links im Bild, Strecke läuft nach rechts wie beim Original
        target_x = self.vehicle.pos.x - WIDTH * 0.26
        self.camera_x = lerp(self.camera_x, target_x, 0.085)
        self.camera_x = max(0, self.camera_x)

        for coin in self.coins:
            coin.update(dt)
            if not coin.collected and (Vec2(coin.x, coin.y) - self.vehicle.pos).length() < 58:
                coin.collected = True
                gained = int(coin.value * self.level.coin_mult)
                self.vehicle.run_coins += gained
                for _ in range(12):
                    self.particles.append(Particle((coin.x, coin.y), (random.uniform(-90, 90), random.uniform(-190, -40)), YELLOW, 0.65, random.randint(3, 6)))

        for fuel in self.fuels:
            fuel.update(dt)
            if not fuel.collected and (Vec2(fuel.x, fuel.y) - self.vehicle.pos).length() < 68:
                fuel.collected = True
                self.vehicle.fuel = self.vehicle.max_fuel()
                self.message = "FUEL FULL!"
                self.message_timer = 1.35
                for _ in range(22):
                    self.particles.append(Particle((fuel.x, fuel.y), (random.uniform(-120, 120), random.uniform(-210, -50)), RED, 0.75, random.randint(3, 7)))

        if self.vehicle.fuel <= 0 and abs(self.vehicle.vel.x) < 8 and self.vehicle.grounded:
            self.vehicle.crash(self.particles)
            self.message = "OUT OF FUEL!"
            self.message_timer = 2.0

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        self.message_timer = max(0, self.message_timer - dt)

    def finish(self):
        if self.finished:
            return
        self.finished = True
        reward = self.vehicle.run_coins + int(self.vehicle.distance * 0.22)
        self.save.add_coins(reward)
        self.save.record_best(self.level_key, self.vehicle.distance)

    def draw_background(self, surf):
        # Himmelverlauf
        for y in range(0, HEIGHT, 2):
            t = y / HEIGHT
            c = tuple(int(lerp(self.level.sky1[i], self.level.sky2[i], t)) for i in range(3))
            pygame.draw.rect(surf, c, (0, y, WIDTH, 2))

        # Sonne/Mond
        if self.level.key == "moon":
            pygame.draw.circle(surf, (225, 225, 235), (1060, 112), 46)
            pygame.draw.circle(surf, (170, 172, 185), (1044, 102), 8)
            pygame.draw.circle(surf, (170, 172, 185), (1070, 128), 12)
            # Sterne
            rng = random.Random(3)
            for _ in range(80):
                x = rng.randint(0, WIDTH)
                y = rng.randint(20, 320)
                pygame.draw.circle(surf, (230, 235, 255), (x, y), rng.choice([1, 1, 2]))
        else:
            pygame.draw.circle(surf, (255, 231, 115), (1060, 108), 54)
            pygame.draw.circle(surf, (255, 245, 165), (1060, 108), 35)

        # Parallax-Berge/Wolken
        for layer, base_y, amp, col in [
            (0.12, 430, 70, (75, 105, 135)),
            (0.22, 480, 95, (55, 82, 112)),
        ]:
            pts = []
            offset = (self.camera_x * layer) % 180
            for i in range(-2, 12):
                x = i * 180 - offset
                y = base_y + math.sin(i * 1.7 + self.level.seed) * amp
                pts.append((x, y))
            pygame.draw.polygon(surf, col, pts + [(WIDTH + 250, HEIGHT), (-250, HEIGHT)])

        # Wolken nur bei Erde
        if self.level.key != "moon":
            for i in range(6):
                x = (i * 270 - self.camera_x * 0.06) % (WIDTH + 300) - 150
                y = 90 + (i % 3) * 54
                self.draw_cloud(surf, x, y, 0.85 + (i % 2) * 0.25)

    def draw_cloud(self, surf, x, y, s):
        col = (245, 250, 255)
        pygame.draw.circle(surf, col, (int(x), int(y)), int(26 * s))
        pygame.draw.circle(surf, col, (int(x + 30 * s), int(y - 10 * s)), int(33 * s))
        pygame.draw.circle(surf, col, (int(x + 65 * s), int(y)), int(25 * s))
        pygame.draw.rect(surf, col, (int(x), int(y - 2 * s), int(65 * s), int(25 * s)), border_radius=int(12 * s))

    def draw_hud(self, surf):
        # obere HUD-Leiste
        pygame.draw.rect(surf, (20, 24, 34), (0, 0, WIDTH, 82))
        pygame.draw.rect(surf, (255, 255, 255), (0, 78, WIDTH, 3))

        draw_text(surf, f"{int(self.vehicle.distance)} m", FONT_BIG, WHITE, 32, 15)
        draw_text(surf, f"$ {money(self.vehicle.run_coins)}", FONT, YELLOW, 250, 23)
        draw_text(surf, f"Bank: $ {money(self.save.coins)}", FONT, YELLOW, 450, 23)
        draw_text(surf, f"{self.level.name}  |  {self.vehicle_def.name}", FONT, CYAN, 760, 23)

        # Fuel-Bar links unten
        x, y, w, h = 32, HEIGHT - 54, 300, 25
        frac = self.vehicle.fuel / self.vehicle.max_fuel()
        pygame.draw.rect(surf, INK, (x - 4, y - 4, w + 8, h + 8), border_radius=15)
        pygame.draw.rect(surf, (70, 25, 25), (x, y, w, h), border_radius=12)
        pygame.draw.rect(surf, GREEN if frac > 0.25 else RED, (x, y, int(w * frac), h), border_radius=12)
        draw_text(surf, "FUEL", FONT_SMALL, WHITE, x + 122, y + 2, center=False)

        # Damage-Bar
        dx = 380
        dfrac = clamp(self.vehicle.damage / 100, 0, 1)
        pygame.draw.rect(surf, INK, (dx - 4, y - 4, 228, h + 8), border_radius=15)
        pygame.draw.rect(surf, (55, 45, 35), (dx, y, 220, h), border_radius=12)
        pygame.draw.rect(surf, ORANGE, (dx, y, int(220 * dfrac), h), border_radius=12)
        draw_text(surf, "DAMAGE", FONT_SMALL, WHITE, dx + 68, y + 2, center=False)

        if self.message_timer > 0:
            draw_text(surf, self.message, FONT_BIG, WHITE, WIDTH // 2, 120, center=True)

        if self.vehicle.dead:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 145))
            surf.blit(overlay, (0, 0))
            reward = self.vehicle.run_coins + int(self.vehicle.distance * 0.22)
            draw_text(surf, "RUN BEENDET", FONT_HUGE, RED, WIDTH // 2, HEIGHT // 2 - 110, center=True)
            draw_text(surf, f"Distanz: {int(self.vehicle.distance)} m", FONT_BIG, WHITE, WIDTH // 2, HEIGHT // 2 - 30, center=True)
            draw_text(surf, f"Belohnung: $ {money(reward)}", FONT_BIG, YELLOW, WIDTH // 2, HEIGHT // 2 + 35, center=True)
            draw_text(surf, "ENTER = Garage     R = Neustart     ESC = Menü", FONT, LIGHT, WIDTH // 2, HEIGHT // 2 + 100, center=True)

    def draw(self, surf):
        self.draw_background(surf)
        for coin in self.coins:
            coin.draw(surf, self.camera_x)
        for fuel in self.fuels:
            fuel.draw(surf, self.camera_x)
        self.terrain.draw(surf, self.camera_x)
        for p in self.particles:
            p.draw(surf, self.camera_x)
        self.vehicle.draw(surf, self.camera_x)
        self.draw_hud(surf)

# ============================================================
# MENÜS
# ============================================================

class MainMenu:
    def __init__(self, save: SaveGame):
        self.save = save
        self.items = ["FAHREN", "GARAGE", "LEVEL", "UPGRADES", "SAVE RESET", "BEENDEN"]
        self.index = 0
        self.t = 0

    def event(self, e):
        if e.type != pygame.KEYDOWN:
            return None
        if e.key in [pygame.K_UP, pygame.K_w]:
            self.index = (self.index - 1) % len(self.items)
        elif e.key in [pygame.K_DOWN, pygame.K_s]:
            self.index = (self.index + 1) % len(self.items)
        elif e.key == pygame.K_RETURN:
            return self.items[self.index]
        return None

    def draw(self, surf):
        self.t += 1 / FPS
        # Hintergrund im Spielstil
        for y in range(0, HEIGHT, 2):
            c = tuple(int(lerp((65, 145, 235)[i], (170, 225, 255)[i], y / HEIGHT)) for i in range(3))
            pygame.draw.rect(surf, c, (0, y, WIDTH, 2))
        pygame.draw.circle(surf, (255, 225, 105), (1030, 120), 58)
        for i in range(5):
            x = (i * 310 - self.t * 18) % (WIDTH + 250) - 120
            y = 115 + (i % 2) * 80
            pygame.draw.circle(surf, WHITE, (int(x), y), 28)
            pygame.draw.circle(surf, WHITE, (int(x + 35), y - 14), 36)
            pygame.draw.circle(surf, WHITE, (int(x + 75), y), 27)
        pygame.draw.polygon(surf, (62, 122, 76), [(0, 520), (180, 450), (360, 530), (560, 430), (760, 530), (980, 440), (1280, 520), (1280, 720), (0, 720)])
        pygame.draw.polygon(surf, DIRT, [(0, 585), (1280, 585), (1280, 720), (0, 720)])
        pygame.draw.line(surf, GRASS, (0, 585), (1280, 585), 9)

        draw_text(surf, "HILL CLIMB", FONT_HUGE, WHITE, WIDTH // 2, 88, center=True)
        draw_text(surf, "STYLE", FONT_HUGE, YELLOW, WIDTH // 2, 158, center=True)
        draw_text(surf, f"$ {money(self.save.coins)}", FONT_BIG, YELLOW, WIDTH // 2, 235, center=True)

        start_y = 310
        for i, item in enumerate(self.items):
            selected = i == self.index
            rect = pygame.Rect(WIDTH // 2 - 210, start_y + i * 55, 420, 42)
            pygame.draw.rect(surf, ORANGE if selected else PANEL, rect, border_radius=18)
            pygame.draw.rect(surf, INK, rect, 3, border_radius=18)
            draw_text(surf, item, FONT, WHITE if selected else LIGHT, rect.centerx, rect.centery, center=True)

        draw_text(surf, "Pfeile/WASD + Enter", FONT_SMALL, INK, WIDTH // 2, HEIGHT - 38, center=True, shadow=False)

class Shop:
    def __init__(self, save: SaveGame, mode: str):
        self.save = save
        self.mode = mode
        if mode == "vehicles":
            self.keys = list(VEHICLES.keys())
        elif mode == "levels":
            self.keys = list(LEVELS.keys())
        else:
            self.keys = ["engine", "tires", "suspension", "fuel"]
        self.index = 0
        self.msg = ""
        self.msg_time = 0

    def event(self, e):
        if e.type != pygame.KEYDOWN:
            return None
        if e.key == pygame.K_ESCAPE:
            return "BACK"
        if e.key in [pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w]:
            self.index = (self.index - 1) % len(self.keys)
        elif e.key in [pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s]:
            self.index = (self.index + 1) % len(self.keys)
        elif e.key == pygame.K_RETURN:
            self.activate()
        return None

    def activate(self):
        key = self.keys[self.index]
        if self.mode == "vehicles":
            ok = self.save.select_or_buy_vehicle(key)
            self.msg = "Ausgewählt!" if ok else "Nicht genug Münzen!"
        elif self.mode == "levels":
            ok = self.save.select_or_buy_level(key)
            self.msg = "Ausgewählt!" if ok else "Nicht genug Münzen!"
        else:
            vehicle = self.save.data["selected_vehicle"]
            ok = self.save.buy_upgrade(vehicle, key)
            self.msg = "Upgrade gekauft!" if ok else "Nicht genug Münzen oder MAX!"
        self.msg_time = 1.2

    def draw_vehicle_preview(self, surf, rect, v: VehicleDef):
        # Kleine Garage-Vorschau passend zum echten Ingame-Design.
        base_x, base_y = rect.centerx, rect.y + 168
        wr = int(v.wheel_r * 0.78)
        wheel_dx = 48 if v.key != "truck" else 55
        wheel_y = base_y + (32 if v.key != "truck" else 38)

        for dx in [-wheel_dx, wheel_dx]:
            pygame.draw.circle(surf, INK, (base_x + dx, wheel_y), wr + 5)
            pygame.draw.circle(surf, (35, 38, 45), (base_x + dx, wheel_y), wr)
            pygame.draw.circle(surf, GREY, (base_x + dx, wheel_y), max(5, wr // 2))
            pygame.draw.circle(surf, LIGHT, (base_x + dx, wheel_y), max(3, wr // 4))

        def poly(points, color, outline=INK, width=4):
            pts = [(base_x + x, base_y + y) for x, y in points]
            pygame.draw.polygon(surf, color, pts)
            if outline:
                pygame.draw.polygon(surf, outline, pts, width)

        if v.key == "jeep":
            poly([(-66, 16), (-55, -22), (-18, -43), (35, -41), (62, -9), (67, 26), (-62, 31)], v.main)
            poly([(-8, -35), (30, -34), (42, -7), (-2, -6)], CYAN, INK, 3)
            pygame.draw.circle(surf, INK, (base_x - 62, base_y - 13), 16)
            pygame.draw.circle(surf, (45, 48, 55), (base_x - 62, base_y - 13), 11)
            pygame.draw.circle(surf, YELLOW, (base_x + 65, base_y - 4), 6)

        elif v.key == "buggy":
            poly([(-68, 14), (-46, -16), (-5, -26), (48, -18), (68, 13), (56, 31), (-62, 31)], v.main)
            # Käfig
            cage = [(base_x - 28, base_y - 15), (base_x - 4, base_y - 52), (base_x + 34, base_y - 47), (base_x + 52, base_y - 16)]
            for a, b in [(0,1), (1,2), (2,3), (0,3), (1,3)]:
                pygame.draw.line(surf, INK, cage[a], cage[b], 6)
                pygame.draw.line(surf, LIGHT, cage[a], cage[b], 2)
            pygame.draw.circle(surf, ORANGE, (base_x + 10, base_y - 45), 12)
            pygame.draw.polygon(surf, RED, [(base_x - 55, base_y - 70), (base_x - 28, base_y - 60), (base_x - 55, base_y - 50)])
            pygame.draw.line(surf, INK, (base_x - 55, base_y - 18), (base_x - 55, base_y - 70), 3)

        elif v.key == "truck":
            pygame.draw.line(surf, INK, (base_x - wheel_dx, wheel_y), (base_x + wheel_dx, wheel_y), 8)
            poly([(-74, 8), (-64, -28), (-22, -52), (28, -48), (52, -18), (70, -7), (76, 28), (-70, 34)], v.main, INK, 5)
            poly([(-72, -8), (-30, -18), (-25, 18), (-74, 24)], v.second, INK, 3)
            poly([(-3, -38), (25, -36), (39, -13), (4, -10)], CYAN, INK, 3)
            pygame.draw.line(surf, GREY, (base_x - 40, base_y - 34), (base_x - 40, base_y - 78), 5)
            pygame.draw.line(surf, GREY, (base_x - 32, base_y - 34), (base_x - 32, base_y - 78), 5)
            pygame.draw.circle(surf, YELLOW, (base_x + 73, base_y - 4), 7)

        elif v.key == "rally":
            poly([(-75, 16), (-56, -12), (-22, -40), (28, -40), (62, -13), (76, 13), (62, 30), (-66, 31)], v.main)
            poly([(-20, -34), (24, -34), (42, -9), (-6, -8)], CYAN, INK, 3)
            poly([(-66, -1), (61, -7), (65, 5), (-70, 12)], WHITE, None, 0)
            poly([(-62, 12), (52, 5), (56, 14), (-66, 21)], YELLOW, None, 0)
            poly([(-94, -37), (-58, -34), (-60, -23), (-96, -25)], v.second, INK, 3)
            pygame.draw.circle(surf, WHITE, (base_x + 5, base_y + 4), 15)
            pygame.draw.circle(surf, INK, (base_x + 5, base_y + 4), 15, 2)
            draw_text(surf, "7", FONT_SMALL, INK, base_x + 5, base_y + 4, center=True, shadow=False)
            pygame.draw.circle(surf, YELLOW, (base_x + 74, base_y - 2), 6)

        else:
            poly([(-62, 15), (-50, -22), (-10, -37), (38, -31), (62, 8), (58, 28), (-58, 30)], v.main)
            poly([(-4, -28), (33, -24), (44, -3), (2, -4)], CYAN, INK, 2)

    def draw(self, surf):
        surf.fill((45, 72, 108))
        pygame.draw.rect(surf, (31, 38, 58), (0, 0, WIDTH, 100))
        title = {"vehicles": "GARAGE", "levels": "LEVEL AUSWAHL", "upgrades": "UPGRADES"}[self.mode]
        draw_text(surf, title, FONT_HUGE, WHITE, WIDTH // 2, 54, center=True)
        draw_text(surf, f"$ {money(self.save.coins)}", FONT_BIG, YELLOW, WIDTH - 170, 52, center=True)

        if self.msg_time > 0:
            self.msg_time -= 1 / FPS
            draw_text(surf, self.msg, FONT, YELLOW, WIDTH // 2, 122, center=True)

        card_w, gap = 270, 34
        total = len(self.keys) * card_w + (len(self.keys) - 1) * gap
        start_x = WIDTH // 2 - total // 2

        for i, key in enumerate(self.keys):
            rect = pygame.Rect(start_x + i * (card_w + gap), 175, card_w, 405)
            selected = i == self.index
            pygame.draw.rect(surf, ORANGE if selected else PANEL, rect, border_radius=24)
            pygame.draw.rect(surf, INK, rect, 5 if selected else 3, border_radius=24)

            if self.mode == "vehicles":
                v = VEHICLES[key]
                owned = key in self.save.data["owned_vehicles"]
                draw_text(surf, v.name, FONT, WHITE, rect.centerx, rect.y + 34, center=True)
                self.draw_vehicle_preview(surf, rect, v)
                draw_text(surf, v.desc, FONT_SMALL, WHITE, rect.x + 18, rect.y + 240, shadow=False)
                draw_text(surf, f"Motor {int(v.engine)}", FONT_SMALL, LIGHT, rect.x + 18, rect.y + 282, shadow=False)
                draw_text(surf, f"Tank {int(v.fuel)}", FONT_SMALL, LIGHT, rect.x + 18, rect.y + 310, shadow=False)
                bottom = "BESITZT" if owned else f"KAUFEN $ {money(v.price)}"
                if self.save.data["selected_vehicle"] == key:
                    bottom = "AKTIV"
                draw_text(surf, bottom, FONT, GREEN if owned else YELLOW, rect.centerx, rect.bottom - 38, center=True)

            elif self.mode == "levels":
                l = LEVELS[key]
                owned = key in self.save.data["owned_levels"]
                draw_text(surf, l.name, FONT, WHITE, rect.centerx, rect.y + 34, center=True)
                # Mini Landschaft
                pygame.draw.rect(surf, l.sky2, (rect.x + 25, rect.y + 85, rect.w - 50, 110), border_radius=14)
                pts = []
                for k in range(9):
                    x = rect.x + 25 + k * ((rect.w - 50) / 8)
                    y = rect.y + 155 + math.sin(k * 1.3 + l.seed) * 25 * l.hill
                    pts.append((x, y))
                pygame.draw.polygon(surf, l.dirt, pts + [(rect.right - 25, rect.y + 195), (rect.x + 25, rect.y + 195)])
                pygame.draw.lines(surf, l.grass, False, pts, 5)
                draw_text(surf, l.desc, FONT_SMALL, WHITE, rect.x + 18, rect.y + 235, shadow=False)
                best = self.save.data["best"].get(key, 0)
                draw_text(surf, f"Best: {int(best)} m", FONT_SMALL, LIGHT, rect.x + 18, rect.y + 300, shadow=False)
                bottom = "BESITZT" if owned else f"KAUFEN $ {money(l.price)}"
                if self.save.data["selected_level"] == key:
                    bottom = "AKTIV"
                draw_text(surf, bottom, FONT, GREEN if owned else YELLOW, rect.centerx, rect.bottom - 38, center=True)

            else:
                vehicle = self.save.data["selected_vehicle"]
                names = {"engine": "MOTOR", "tires": "REIFEN", "suspension": "FEDERUNG", "fuel": "TANK"}
                desc = {
                    "engine": "Mehr Kraft am Berg und bessere Beschleunigung.",
                    "tires": "Mehr Grip. Weniger Durchdrehen am Hang.",
                    "suspension": "Stabilere Landungen und weniger Schaden.",
                    "fuel": "Mehr Reichweite pro Run.",
                }
                lvl = self.save.data["upgrades"][vehicle][key]
                cost = self.save.upgrade_cost(vehicle, key)
                draw_text(surf, names[key], FONT, WHITE, rect.centerx, rect.y + 42, center=True)
                draw_text(surf, desc[key], FONT_SMALL, WHITE, rect.x + 18, rect.y + 110, shadow=False)
                # Icon
                icon_y = rect.y + 205
                if key == "engine":
                    pygame.draw.rect(surf, GREY, (rect.centerx - 45, icon_y - 25, 90, 50), border_radius=8)
                    pygame.draw.rect(surf, INK, (rect.centerx - 45, icon_y - 25, 90, 50), 3, border_radius=8)
                    pygame.draw.circle(surf, ORANGE, (rect.centerx + 48, icon_y), 9)
                elif key == "tires":
                    pygame.draw.circle(surf, INK, (rect.centerx, icon_y), 45)
                    pygame.draw.circle(surf, GREY, (rect.centerx, icon_y), 25)
                elif key == "suspension":
                    pygame.draw.line(surf, INK, (rect.centerx - 42, icon_y + 35), (rect.centerx + 42, icon_y - 35), 9)
                    pygame.draw.line(surf, LIGHT, (rect.centerx - 42, icon_y + 35), (rect.centerx + 42, icon_y - 35), 3)
                else:
                    pygame.draw.rect(surf, RED, (rect.centerx - 32, icon_y - 42, 64, 84), border_radius=10)
                    pygame.draw.rect(surf, INK, (rect.centerx - 32, icon_y - 42, 64, 84), 4, border_radius=10)

                # Levelbar
                bx, by = rect.x + 34, rect.y + 292
                pygame.draw.rect(surf, INK, (bx - 3, by - 3, 208, 24), border_radius=12)
                pygame.draw.rect(surf, DARK, (bx, by, 202, 18), border_radius=9)
                pygame.draw.rect(surf, GREEN, (bx, by, int(202 * lvl / 12), 18), border_radius=9)
                draw_text(surf, f"LVL {lvl}/12", FONT_SMALL, WHITE, rect.centerx, by + 36, center=True)
                bottom = "MAX" if lvl >= 12 else f"KAUFEN $ {money(cost)}"
                draw_text(surf, bottom, FONT, YELLOW if lvl < 12 else GREEN, rect.centerx, rect.bottom - 38, center=True)

        draw_text(surf, "Pfeile/WASD wechseln  |  Enter kaufen/auswählen  |  ESC zurück", FONT_SMALL, WHITE, WIDTH // 2, HEIGHT - 40, center=True)

# ============================================================
# APP
# ============================================================

class App:
    def __init__(self):
        self.save = SaveGame()
        self.state = "menu"
        self.menu = MainMenu(self.save)
        self.shop: Optional[Shop] = None
        self.world: Optional[World] = None

    def start_game(self):
        self.world = World(self.save)
        self.state = "game"

    def reset_save(self):
        self.save.data = json.loads(json.dumps(DEFAULT_SAVE))
        self.save.save()
        self.menu = MainMenu(self.save)

    def run(self):
        running = True
        while running:
            dt = CLOCK.tick(FPS) / 1000
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False

                elif self.state == "menu":
                    action = self.menu.event(e)
                    if action == "FAHREN":
                        self.start_game()
                    elif action == "GARAGE":
                        self.shop = Shop(self.save, "vehicles")
                        self.state = "shop"
                    elif action == "LEVEL":
                        self.shop = Shop(self.save, "levels")
                        self.state = "shop"
                    elif action == "UPGRADES":
                        self.shop = Shop(self.save, "upgrades")
                        self.state = "shop"
                    elif action == "SAVE RESET":
                        self.reset_save()
                    elif action == "BEENDEN":
                        running = False

                elif self.state == "shop":
                    result = self.shop.event(e)
                    if result == "BACK":
                        self.menu = MainMenu(self.save)
                        self.state = "menu"

                elif self.state == "game":
                    if e.type == pygame.KEYDOWN:
                        if e.key == pygame.K_ESCAPE:
                            if self.world:
                                self.world.finish()
                            self.menu = MainMenu(self.save)
                            self.state = "menu"
                        elif e.key == pygame.K_r:
                            if self.world:
                                self.world.finish()
                            self.start_game()
                        elif e.key == pygame.K_RETURN:
                            if self.world and self.world.vehicle.dead:
                                self.world.finish()
                                self.shop = Shop(self.save, "upgrades")
                                self.state = "shop"

            if self.state == "game" and self.world:
                self.world.update(dt)

            if self.state == "menu":
                self.menu.draw(SCREEN)
            elif self.state == "shop" and self.shop:
                self.shop.draw(SCREEN)
            elif self.state == "game" and self.world:
                self.world.draw(SCREEN)

            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    App().run()
