import pygame
import math
import random
import sys
from dataclasses import dataclass

# ============================================================
#  BLOCKSTRIKE ARENA - Local Shooter
#  Umfangreicher lokaler Krunker.io-inspirierter Shooter
#
#  Installation:
#      pip install pygame
#
#  Start:
#      python krunker_style_local_shooter.py
#
#  Steuerung:
#      WASD        bewegen
#      Maus        umsehen
#      Linksklick  schießen
#      Rechtsklick zielen
#      R           nachladen
#      Shift       sprinten
#      Leertaste   springen
#      1/2/3/4     Waffen wechseln
#      M           Minimap groß/klein
#      G           Granate
#      ESC         Pause
# ============================================================

pygame.init()
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
except Exception:
    pass

WIDTH, HEIGHT = 1600, 900
HALF_W, HALF_H = WIDTH // 2, HEIGHT // 2
FPS = 90
WIN = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED)
pygame.display.set_caption("BlockStrike Arena - Local Shooter")
CLOCK = pygame.time.Clock()

# ------------------------------------------------------------
# Farben / Fonts
# ------------------------------------------------------------
BLACK = (6, 7, 12)
WHITE = (240, 245, 255)
SOFT = (205, 215, 235)
GREY = (120, 130, 150)
DARK = (15, 17, 27)
RED = (255, 70, 85)
GREEN = (80, 255, 145)
BLUE = (80, 160, 255)
CYAN = (65, 225, 255)
YELLOW = (255, 225, 95)
ORANGE = (255, 145, 55)
PURPLE = (185, 105, 255)
PINK = (255, 80, 190)

FONT = pygame.font.SysFont("consolas", 22)
FONT_SMALL = pygame.font.SysFont("consolas", 15)
FONT_TINY = pygame.font.SysFont("consolas", 12)
FONT_MED = pygame.font.SysFont("consolas", 34, bold=True)
FONT_BIG = pygame.font.SysFont("consolas", 72, bold=True)
FONT_HUGE = pygame.font.SysFont("consolas", 96, bold=True)

# ------------------------------------------------------------
# Raycasting Qualität
# ------------------------------------------------------------
TILE = 96
MAP_W, MAP_H = 22, 22
FOV_NORMAL = math.radians(74)
FOV_AIM = math.radians(52)
NUM_RAYS_NORMAL = 520
MAX_DEPTH = 2300

# Höhere interne Ray-Auflösung als vorher: mehr Rays, glattere Wände.
# Das Spiel bleibt trotzdem in Pygame lauffähig, weil die Welt 2.5D ist.

WORLD_MAP = [
    "######################",
    "#..........#.........#",
    "#..####....#..####...#",
    "#..#.............#...#",
    "#..#...##....##..#...#",
    "#......##....##......#",
    "###................###",
    "#....#.......#......##",
    "#....#..###..#.......#",
    "#.......#C#..........#",
    "#..###..###.....###..#",
    "#....................#",
    "#....##.......##.....#",
    "#....##.......##.....#",
    "#..........#.........#",
    "#..####....#....###..#",
    "#.....#.........#....#",
    "#.....#..##..#.......#",
    "#........##..#..##...#",
    "#...###..........#...#",
    "#....................#",
    "######################",
]
WORLD_MAP = [(row + "#" * MAP_W)[:MAP_W] for row in WORLD_MAP[:MAP_H]]

FLOOR_DECALS = []
for _ in range(110):
    x = random.randint(1, MAP_W - 2) * TILE + random.randint(8, TILE - 8)
    y = random.randint(1, MAP_H - 2) * TILE + random.randint(8, TILE - 8)
    cx, cy = int(x // TILE), int(y // TILE)
    if WORLD_MAP[cy][cx] != "#":
        FLOOR_DECALS.append((x, y, random.choice([CYAN, BLUE, PURPLE, ORANGE]), random.randint(8, 24)))

# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------
def clamp(v, a, b):
    return max(a, min(b, v))


def lerp(a, b, t):
    return a + (b - a) * t


def dist2(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def angle_norm(a):
    return a % math.tau


def angle_diff(a, b):
    return (a - b + math.pi) % math.tau - math.pi


def cell_at(x, y):
    return int(x // TILE), int(y // TILE)


def is_wall_px(x, y):
    mx, my = cell_at(x, y)
    if mx < 0 or my < 0 or mx >= MAP_W or my >= MAP_H:
        return True
    return WORLD_MAP[my][mx] == "#"


def is_cover_px(x, y):
    mx, my = cell_at(x, y)
    if mx < 0 or my < 0 or mx >= MAP_W or my >= MAP_H:
        return True
    return WORLD_MAP[my][mx] in "#C"


def line_of_sight(x1, y1, x2, y2, step=18):
    d = dist2(x1, y1, x2, y2)
    steps = max(1, int(d / step))
    for i in range(1, steps + 1):
        t = i / steps
        if is_cover_px(lerp(x1, x2, t), lerp(y1, y2, t)):
            return False
    return True


def draw_text(surface, text, font, color, center=None, topleft=None, shadow=True):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = center
    if topleft:
        rect.topleft = topleft
    if shadow:
        sh = font.render(text, True, (0, 0, 0))
        surface.blit(sh, rect.move(3, 3))
    surface.blit(img, rect)
    return rect


def make_beep(freq=440, duration_ms=45, volume=0.08):
    try:
        import array
        sr = 22050
        n = int(sr * duration_ms / 1000)
        buf = array.array("h")
        amp = int(32767 * volume)
        for i in range(n):
            fade = 1 - i / max(1, n)
            buf.append(int(amp * fade * math.sin(math.tau * freq * i / sr)))
        return pygame.mixer.Sound(buffer=buf)
    except Exception:
        return None

SND_SHOOT = make_beep(160, 38, 0.13)
SND_HIT = make_beep(620, 45, 0.09)
SND_KILL = make_beep(900, 80, 0.11)
SND_RELOAD = make_beep(320, 65, 0.07)
SND_PICK = make_beep(540, 80, 0.08)
SND_HURT = make_beep(85, 90, 0.11)
SND_DASH = make_beep(260, 50, 0.06)


def play(sound):
    try:
        if sound:
            sound.play()
    except Exception:
        pass

# ------------------------------------------------------------
# Datenklassen
# ------------------------------------------------------------
@dataclass
class Particle:
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    life: float
    max_life: float
    color: tuple
    size: float
    glow: bool = False

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt
        self.vx *= 0.94
        self.vy *= 0.94
        self.vz -= 150 * dt
        self.life -= dt

    @property
    def alive(self):
        return self.life > 0 and self.z > -40


@dataclass
class FloatingText:
    x: float
    y: float
    z: float
    text: str
    color: tuple
    life: float
    max_life: float

    def update(self, dt):
        self.z += 45 * dt
        self.life -= dt

    @property
    def alive(self):
        return self.life > 0

# ------------------------------------------------------------
# Waffen
# ------------------------------------------------------------
class Weapon:
    def __init__(self, name, damage, fire_rate, mag, reserve, reload_time, spread, aim_spread, recoil, color, pellets=1, auto=True):
        self.name = name
        self.damage = damage
        self.fire_rate = fire_rate
        self.mag_size = mag
        self.ammo = mag
        self.reserve = reserve
        self.reload_time = reload_time
        self.spread = spread
        self.aim_spread = aim_spread
        self.recoil = recoil
        self.color = color
        self.pellets = pellets
        self.auto = auto
        self.cooldown = 0
        self.reloading = False
        self.reload_timer = 0
        self.kick = 0
        self.muzzle = 0

    def update(self, dt):
        self.cooldown = max(0, self.cooldown - dt)
        self.kick *= 0.82
        self.muzzle = max(0, self.muzzle - dt * 12)
        if self.reloading:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                need = self.mag_size - self.ammo
                take = min(need, self.reserve)
                self.ammo += take
                self.reserve -= take
                self.reloading = False

    def can_fire(self):
        return self.cooldown <= 0 and not self.reloading and self.ammo > 0

    def reload(self):
        if not self.reloading and self.ammo < self.mag_size and self.reserve > 0:
            self.reloading = True
            self.reload_timer = self.reload_time
            play(SND_RELOAD)

    def fire_event(self):
        self.ammo -= 1
        self.cooldown = 1 / self.fire_rate
        self.kick = 1
        self.muzzle = 1
        play(SND_SHOOT)

# ------------------------------------------------------------
# Player
# ------------------------------------------------------------
class Player:
    def __init__(self):
        self.x = 2.5 * TILE
        self.y = 2.5 * TILE
        self.angle = 0
        self.hp = 100
        self.max_hp = 100
        self.armor = 35
        self.score = 0
        self.kills = 0
        self.combo = 0
        self.combo_timer = 0
        self.damage_flash = 0
        self.hitmarker = 0
        self.headshot_marker = 0
        self.shake = 0
        self.speed = 300
        self.strafe_speed = 285
        self.dash_cd = 0
        self.dash_power = 0
        self.jump_z = 0
        self.jump_v = 0
        self.on_ground = True
        self.aiming = False
        self.minimap_big = False
        self.grenades = 3
        self.weapon_switch_flash = 0
        self.weapon_index = 0
        self.weapons = [
            Weapon("KR-9 SMG", 16, 13.5, 34, 170, 1.30, 0.030, 0.012, 0.020, CYAN, auto=True),
            Weapon("VOLT RIFLE", 34, 5.5, 24, 120, 1.55, 0.014, 0.004, 0.035, ORANGE, auto=True),
            Weapon("BLOCK SHOTGUN", 11, 1.35, 7, 42, 1.75, 0.090, 0.045, 0.070, YELLOW, pellets=8, auto=False),
            Weapon("RAIL SCOUT", 74, 1.8, 6, 42, 1.85, 0.004, 0.001, 0.075, PURPLE, auto=False),
        ]

    @property
    def weapon(self):
        return self.weapons[self.weapon_index]

    def switch_weapon(self, index):
        index %= len(self.weapons)
        if index != self.weapon_index:
            self.weapon_index = index
            self.weapon_switch_flash = 1.0
            self.shake = max(self.shake, 0.12)
            play(SND_PICK)

    def next_weapon(self):
        self.switch_weapon(self.weapon_index + 1)

    def prev_weapon(self):
        self.switch_weapon(self.weapon_index - 1)

    def damage(self, amount):
        if self.armor > 0:
            block = min(self.armor, amount * 0.48)
            self.armor -= block
            amount -= block * 0.7
        self.hp -= amount
        self.damage_flash = 1
        self.shake = max(self.shake, 1)
        play(SND_HURT)

    def update(self, dt, keys, mouse_buttons):
        # Nur die Rail Scout hat echtes Visier/Scope. Bei Shotgun/SMG/Rifle bleibt Rechtsklick ohne Scope.
        self.aiming = mouse_buttons[2] and self.weapon.name == "RAIL SCOUT"
        self.damage_flash = max(0, self.damage_flash - dt * 2.5)
        self.hitmarker = max(0, self.hitmarker - dt * 4.8)
        self.headshot_marker = max(0, self.headshot_marker - dt * 3.5)
        self.shake = max(0, self.shake - dt * 8)
        self.combo_timer = max(0, self.combo_timer - dt)
        self.weapon_switch_flash = max(0, self.weapon_switch_flash - dt * 3.5)
        if self.combo_timer <= 0:
            self.combo = 0
        self.dash_cd = max(0, self.dash_cd - dt)
        self.dash_power = max(0, self.dash_power - dt * 3)
        # Sprungphysik: echte vertikale Spielerhöhe für Kamera/Weapon-Bob
        if not self.on_ground or self.jump_z > 0:
            self.jump_v -= 900 * dt
            self.jump_z += self.jump_v * dt
            if self.jump_z <= 0:
                self.jump_z = 0
                self.jump_v = 0
                self.on_ground = True

        for w in self.weapons:
            w.update(dt)

        sprint = keys[pygame.K_LSHIFT] and keys[pygame.K_w] and not self.aiming
        speed_mul = 1.33 if sprint else 0.72 if self.aiming else 1.0
        if self.dash_power > 0:
            speed_mul += self.dash_power * 2.2

        cos_a, sin_a = math.cos(self.angle), math.sin(self.angle)
        dx = dy = 0
        if keys[pygame.K_w]:
            dx += cos_a * self.speed * speed_mul * dt
            dy += sin_a * self.speed * speed_mul * dt
        if keys[pygame.K_s]:
            dx -= cos_a * self.speed * 0.82 * speed_mul * dt
            dy -= sin_a * self.speed * 0.82 * speed_mul * dt
        if keys[pygame.K_a]:
            dx += sin_a * self.strafe_speed * speed_mul * dt
            dy -= cos_a * self.strafe_speed * speed_mul * dt
        if keys[pygame.K_d]:
            dx -= sin_a * self.strafe_speed * speed_mul * dt
            dy += cos_a * self.strafe_speed * speed_mul * dt

        self.move(dx, dy)

    def move(self, dx, dy):
        pad = 22
        nx = self.x + dx
        if not is_wall_px(nx + math.copysign(pad, dx if dx else 1), self.y):
            self.x = nx
        ny = self.y + dy
        if not is_wall_px(self.x, ny + math.copysign(pad, dy if dy else 1)):
            self.y = ny

    def jump(self):
        if self.on_ground:
            self.on_ground = False
            self.jump_v = 455
            self.jump_z = 2
            self.shake = max(self.shake, 0.16)
            play(SND_DASH)

    def dash(self):
        if self.dash_cd <= 0:
            self.dash_power = 1
            self.dash_cd = 1.25
            self.shake = max(self.shake, 0.45)
            play(SND_DASH)

# ------------------------------------------------------------
# Gegner
# ------------------------------------------------------------
class Enemy:
    PRESETS = [
        {"name": "Runner", "hp": 62, "speed": 118, "damage": 9, "color": RED, "size": 48, "range": 60, "shoot": False},
        {"name": "Tank", "hp": 160, "speed": 68, "damage": 19, "color": PURPLE, "size": 60, "range": 70, "shoot": False},
        {"name": "Striker", "hp": 92, "speed": 96, "damage": 13, "color": ORANGE, "size": 52, "range": 65, "shoot": False},
        {"name": "Blaster", "hp": 84, "speed": 78, "damage": 10, "color": BLUE, "size": 50, "range": 620, "shoot": True},
    ]

    def __init__(self, x, y, level=1):
        preset = random.choices(self.PRESETS, weights=[4, 2, 3, 2 + level * 0.2])[0]
        self.name = preset["name"]
        self.x = x
        self.y = y
        self.z = 0
        self.hp = preset["hp"] + level * 8
        self.max_hp = self.hp
        # Gegner skalieren nur leicht mit dem Level, damit sie nicht hektisch werden.
        self.speed = preset["speed"] + level * 1.15
        self.damage_amt = preset["damage"] + level * 0.9
        self.color = preset["color"]
        self.size = preset["size"]
        self.attack_range = preset["range"]
        self.shooter = preset["shoot"]
        self.attack_cd = random.uniform(0.3, 1.2)
        self.wander_angle = random.random() * math.tau
        self.wander_timer = random.uniform(0.4, 1.6)
        self.stun = 0
        self.dead = False
        self.death_timer = 0.45
        self.flash = 0
        self.phase = random.random() * 10

    def update(self, dt, game):
        p = game.player
        self.flash = max(0, self.flash - dt * 5)
        if self.dead:
            self.death_timer -= dt
            return
        self.attack_cd = max(0, self.attack_cd - dt)
        self.stun = max(0, self.stun - dt)

        d = dist2(self.x, self.y, p.x, p.y)
        see = d < 1000 and line_of_sight(self.x, self.y, p.x, p.y)
        if self.stun <= 0:
            if see:
                angle = math.atan2(p.y - self.y, p.x - self.x)
                if self.shooter and d < 660:
                    # Schützen laufen nicht mehr wild seitlich herum.
                    # Sie halten ruhiger Abstand und sind dadurch viel besser treffbar.
                    ideal = 455
                    if d < ideal - 70:
                        angle += math.pi
                        move_mul = 0.52
                    elif d > ideal + 95:
                        move_mul = 0.48
                    else:
                        move_mul = 0.08
                        angle += math.pi / 2
                    self.try_move(math.cos(angle) * self.speed * move_mul * dt, math.sin(angle) * self.speed * move_mul * dt)
                else:
                    # Kein wildes Schwirren mehr: Gegner laufen direkter und langsamer auf dich zu.
                    self.try_move(math.cos(angle) * self.speed * 0.72 * dt, math.sin(angle) * self.speed * 0.72 * dt)
            else:
                self.wander_timer -= dt
                if self.wander_timer <= 0:
                    self.wander_timer = random.uniform(0.5, 1.7)
                    self.wander_angle = random.random() * math.tau
                # Im Leerlauf nur leicht bewegen, damit sie nicht nervös herumzappeln.
                self.try_move(math.cos(self.wander_angle) * self.speed * 0.16 * dt, math.sin(self.wander_angle) * self.speed * 0.16 * dt)

        if see and self.attack_cd <= 0:
            if self.shooter and d < 690:
                game.enemy_projectiles.append(EnemyProjectile(self.x, self.y, 38, math.atan2(p.y - self.y, p.x - self.x), self.damage_amt, self.color))
                self.attack_cd = random.uniform(0.85, 1.35)
                for _ in range(8):
                    game.spawn_particle(self.x, self.y, 30, self.color, 0.28, 100)
            elif d < self.attack_range:
                p.damage(self.damage_amt)
                self.attack_cd = random.uniform(0.58, 0.9)
                for _ in range(16):
                    game.spawn_particle(p.x, p.y, 20, RED, 0.35, 180)

    def try_move(self, dx, dy):
        # Größerer Kollisionspuffer: Gegner kleben optisch nicht mehr so in Wänden.
        radius = max(24, self.size * 0.38)
        nx = self.x + dx
        if not (is_wall_px(nx - radius, self.y) or is_wall_px(nx + radius, self.y) or is_wall_px(nx, self.y - radius) or is_wall_px(nx, self.y + radius)):
            self.x = nx
        else:
            self.wander_angle += random.uniform(0.5, 1.0)
        ny = self.y + dy
        if not (is_wall_px(self.x - radius, ny) or is_wall_px(self.x + radius, ny) or is_wall_px(self.x, ny - radius) or is_wall_px(self.x, ny + radius)):
            self.y = ny
        else:
            self.wander_angle += random.uniform(0.5, 1.0)

    def hit(self, dmg, headshot, game):
        self.hp -= dmg
        self.flash = 1
        self.stun = 0.11
        game.texts.append(FloatingText(self.x, self.y, 75, str(int(dmg)) + (" HS" if headshot else ""), YELLOW if headshot else WHITE, 0.7, 0.7))
        for _ in range(14 if not headshot else 24):
            game.spawn_particle(self.x, self.y, random.uniform(20, 70), self.color, random.uniform(0.25, 0.7), random.uniform(120, 340), glow=headshot)
        if self.hp <= 0 and not self.dead:
            self.dead = True
            self.death_timer = 0.42
            game.player.score += 110 + game.player.combo * 15
            game.player.kills += 1
            game.player.combo += 1
            game.player.combo_timer = 3.2
            game.player.armor = min(100, game.player.armor + random.randint(3, 9))
            play(SND_KILL)
            for _ in range(34):
                game.spawn_particle(self.x, self.y, random.uniform(10, 90), self.color, random.uniform(0.45, 1.0), random.uniform(180, 520), glow=True)
            if random.random() < 0.33:
                game.spawn_pickup_at(self.x, self.y)

class EnemyProjectile:
    def __init__(self, x, y, z, angle, damage, color):
        self.x = x
        self.y = y
        self.z = z
        self.angle = angle
        self.speed = 440
        self.damage = damage
        self.color = color
        self.life = 2.0

    def update(self, dt, game):
        self.x += math.cos(self.angle) * self.speed * dt
        self.y += math.sin(self.angle) * self.speed * dt
        self.life -= dt
        if is_wall_px(self.x, self.y):
            self.life = 0
            for _ in range(8):
                game.spawn_particle(self.x, self.y, self.z, self.color, 0.25, 120)
        if dist2(self.x, self.y, game.player.x, game.player.y) < 30:
            self.life = 0
            game.player.damage(self.damage)

# ------------------------------------------------------------
# Pickups
# ------------------------------------------------------------
class Grenade:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.z = 55
        self.vx = math.cos(angle) * 520
        self.vy = math.sin(angle) * 520
        self.vz = 170
        self.timer = 1.35
        self.dead = False
        self.radius = 230

    def update(self, dt, game):
        self.timer -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt
        self.vx *= 0.975
        self.vy *= 0.975
        self.vz -= 330 * dt
        if self.z < 12:
            self.z = 12
            self.vz *= -0.38
            self.vx *= 0.75
            self.vy *= 0.75
        if is_wall_px(self.x, self.y):
            self.vx *= -0.45
            self.vy *= -0.45
            self.x += self.vx * dt * 2
            self.y += self.vy * dt * 2
        if self.timer <= 0:
            self.explode(game)
            self.dead = True

    def explode(self, game):
        game.player.shake = max(game.player.shake, 1.15)
        play(SND_KILL)
        for _ in range(95):
            game.spawn_particle(self.x, self.y, random.uniform(10, 110), random.choice([ORANGE, YELLOW, RED, GREY]), random.uniform(0.35, 1.05), random.uniform(240, 780), glow=True)
        for e in game.enemies:
            if e.dead:
                continue
            d = dist2(self.x, self.y, e.x, e.y)
            if d < self.radius and line_of_sight(self.x, self.y, e.x, e.y):
                damage = 115 * (1 - d / self.radius) + 28
                e.hit(damage, False, game)
        pd = dist2(self.x, self.y, game.player.x, game.player.y)
        if pd < self.radius * 0.75:
            game.player.damage(32 * (1 - pd / (self.radius * 0.75)))

class Pickup:
    def __init__(self, x, y, kind):
        self.x = x
        self.y = y
        self.kind = kind
        self.t = random.random() * 100

    @property
    def color(self):
        return {"health": GREEN, "ammo": YELLOW, "armor": BLUE, "boost": PINK}.get(self.kind, WHITE)

    def apply(self, player):
        if self.kind == "health":
            player.hp = min(player.max_hp, player.hp + 38)
        elif self.kind == "ammo":
            for w in player.weapons:
                w.reserve += int(w.mag_size * 1.15)
        elif self.kind == "armor":
            player.armor = min(100, player.armor + 32)
        elif self.kind == "boost":
            player.score += 250
        play(SND_PICK)

# ------------------------------------------------------------
# Game
# ------------------------------------------------------------
class Game:
    def __init__(self):
        self.state = "menu"
        self.player = Player()
        self.enemies = []
        self.pickups = []
        self.particles = []
        self.texts = []
        self.enemy_projectiles = []
        self.grenades = []
        self.level = 1
        self.message = ""
        self.message_timer = 0
        self.mouse_locked = False
        self.ray_depths = [MAX_DEPTH] * NUM_RAYS_NORMAL
        self.ray_hits = []
        self.bg_time = 0
        self.last_single_fire = False
        self.menu_buttons = []
        self.spawn_wave()

    def reset(self):
        self.__init__()
        self.state = "play"
        self.lock_mouse(True)

    def lock_mouse(self, value):
        self.mouse_locked = value
        pygame.mouse.set_visible(not value)
        pygame.event.set_grab(value)

    def random_empty_pos(self, far=True):
        for _ in range(700):
            mx = random.randint(1, MAP_W - 2)
            my = random.randint(1, MAP_H - 2)
            if WORLD_MAP[my][mx] != "#":
                x, y = (mx + 0.5) * TILE, (my + 0.5) * TILE
                if not far or dist2(x, y, self.player.x, self.player.y) > 420:
                    return x, y
        return 2.5 * TILE, 2.5 * TILE

    def spawn_pickup_at(self, x, y):
        self.pickups.append(Pickup(x, y, random.choices(["health", "ammo", "armor", "boost"], weights=[3, 4, 3, 1])[0]))

    def spawn_wave(self):
        amount = 6 + self.level * 3
        for _ in range(amount):
            x, y = self.random_empty_pos(True)
            self.enemies.append(Enemy(x, y, self.level))
        for _ in range(4 + self.level // 2):
            x, y = self.random_empty_pos(True)
            self.spawn_pickup_at(x, y)
        self.message = f"WAVE {self.level}"
        self.message_timer = 2.4

    def spawn_particle(self, x, y, z, color, life, speed, glow=False):
        a = random.random() * math.tau
        sp = random.uniform(speed * 0.25, speed)
        self.particles.append(Particle(x, y, z, math.cos(a) * sp, math.sin(a) * sp, random.uniform(-50, 190), life, life, color, random.uniform(3, 9), glow))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEMOTION and self.state == "play":
                sensitivity = 0.00155 if self.player.aiming else 0.00255
                self.player.angle = angle_norm(self.player.angle + event.rel[0] * sensitivity)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == "play":
                        self.state = "pause"
                        self.lock_mouse(False)
                    elif self.state == "pause":
                        self.state = "play"
                        self.lock_mouse(True)
                if event.key == pygame.K_RETURN and self.state in ("menu", "dead"):
                    self.reset()
                if self.state == "play":
                    if event.key == pygame.K_r:
                        self.player.weapon.reload()
                    if event.key == pygame.K_SPACE:
                        self.player.jump()
                    if event.key == pygame.K_g:
                        self.throw_grenade()
                    if event.key == pygame.K_q:
                        self.player.prev_weapon()
                    if event.key == pygame.K_e:
                        self.player.next_weapon()
                    if event.key == pygame.K_m:
                        self.player.minimap_big = not self.player.minimap_big
                    if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
                        self.player.switch_weapon(int(event.unicode) - 1)
            if event.type == pygame.MOUSEBUTTONDOWN and self.state == "menu":
                if event.button == 1:
                    self.handle_menu_click(event.pos)
            if event.type == pygame.MOUSEBUTTONDOWN and self.state == "dead":
                if event.button == 1:
                    self.handle_menu_click(event.pos)
            if event.type == pygame.MOUSEBUTTONDOWN and self.state == "pause":
                if event.button == 1:
                    self.handle_menu_click(event.pos)
            if event.type == pygame.MOUSEBUTTONDOWN and self.state == "play":
                if event.button == 4:
                    self.player.prev_weapon()
                if event.button == 5:
                    self.player.next_weapon()
                if event.button == 1:
                    self.shoot(single_click=True)

    def handle_menu_click(self, pos):
        mx, my = pos
        for rect, action in self.menu_buttons:
            if rect.collidepoint(mx, my):
                if action == "start":
                    self.reset()
                elif action == "resume":
                    self.state = "play"
                    self.lock_mouse(True)
                elif action == "restart":
                    self.reset()
                elif action == "quit":
                    pygame.quit()
                    sys.exit()

    def throw_grenade(self):
        if self.player.grenades <= 0:
            return
        self.player.grenades -= 1
        self.grenades.append(Grenade(self.player.x + math.cos(self.player.angle) * 36, self.player.y + math.sin(self.player.angle) * 36, self.player.angle))
        self.player.shake = max(self.player.shake, 0.25)
        play(SND_DASH)

    def update(self, dt):
        self.bg_time += dt
        if self.state != "play":
            return
        keys = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pressed()
        self.player.update(dt, keys, mouse)

        # Auto-Waffen dauerhaft, Semi-Waffen nur Klick
        if mouse[0] and self.player.weapon.auto:
            self.shoot(single_click=False)

        for e in self.enemies:
            e.update(dt, self)
        self.enemies = [e for e in self.enemies if not (e.dead and e.death_timer <= 0)]

        for pr in self.enemy_projectiles[:]:
            pr.update(dt, self)
            if pr.life <= 0:
                self.enemy_projectiles.remove(pr)

        for gr in self.grenades[:]:
            gr.update(dt, self)
            if gr.dead:
                self.grenades.remove(gr)

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

        for t in self.texts:
            t.update(dt)
        self.texts = [t for t in self.texts if t.alive]

        for pu in self.pickups[:]:
            pu.t += dt
            if dist2(pu.x, pu.y, self.player.x, self.player.y) < 46:
                pu.apply(self.player)
                for _ in range(18):
                    self.spawn_particle(pu.x, pu.y, 35, pu.color, 0.45, 220, glow=True)
                self.pickups.remove(pu)

        if not self.enemies:
            self.level += 1
            self.spawn_wave()

        self.message_timer = max(0, self.message_timer - dt)
        if self.player.hp <= 0:
            self.state = "dead"
            self.lock_mouse(False)

    def shoot(self, single_click=False):
        p = self.player
        w = p.weapon
        if not w.auto and not single_click:
            return
        if w.reloading:
            return
        if w.ammo <= 0:
            w.reload()
            return
        if not w.can_fire():
            return
        w.fire_event()
        p.shake = max(p.shake, 0.28 + w.recoil * 4)
        p.angle = angle_norm(p.angle + random.uniform(-w.recoil, w.recoil) * (0.45 if p.aiming else 1))

        any_hit = False
        for _ in range(w.pellets):
            spread = w.aim_spread if p.aiming else w.spread
            shot_angle = p.angle + random.uniform(-spread, spread)
            hit_enemy = self.trace_bullet(shot_angle, w.damage)
            any_hit = any_hit or hit_enemy
        if any_hit:
            p.hitmarker = 1
            play(SND_HIT)
        for _ in range(10):
            self.spawn_particle(p.x + math.cos(p.angle)*35, p.y + math.sin(p.angle)*35, 35, w.color, 0.18, 160, glow=True)

    def trace_bullet(self, shot_angle, base_damage):
        p = self.player
        best = None
        best_score = 10**9
        best_head = False
        for e in self.enemies:
            if e.dead:
                continue
            dx, dy = e.x - p.x, e.y - p.y
            d = math.hypot(dx, dy)
            if d > 1500:
                continue
            ang = math.atan2(dy, dx)
            diff = abs(angle_diff(ang, shot_angle))
            # Faire Hitbox: etwas größer als das Modell, damit Treffen nicht frustriert.
            body_width = math.atan2(e.size * 1.45, d)
            head_width = math.atan2(e.size * 0.48, d)
            if diff < body_width and line_of_sight(p.x, p.y, e.x, e.y):
                score = d + diff * 2600
                if score < best_score:
                    best = e
                    best_score = score
                    best_head = diff < head_width * 0.72
        if best:
            d = dist2(p.x, p.y, best.x, best.y)
            falloff = clamp(1.18 - d / 1650, 0.52, 1.05)
            dmg = base_damage * falloff * (1.75 if best_head else 1.0)
            best.hit(dmg, best_head, self)
            self.player.score += int(dmg)
            if best_head:
                self.player.headshot_marker = 1
                self.message = "HEADSHOT"
                self.message_timer = 0.5
            return True
        else:
            # Einschlag-Partikel in Welt
            for d in range(80, 1200, 36):
                x = p.x + math.cos(shot_angle) * d
                y = p.y + math.sin(shot_angle) * d
                if is_cover_px(x, y):
                    for _ in range(10):
                        self.spawn_particle(x, y, random.uniform(20, 60), GREY, 0.34, 170)
                    break
        return False

    # --------------------------------------------------------
    # Raycasting Render
    # --------------------------------------------------------
    def cast_rays(self, fov):
        num_rays = NUM_RAYS_NORMAL
        delta = fov / num_rays
        dist_plane = num_rays / (2 * math.tan(fov / 2))
        proj_coeff = 3.25 * dist_plane * TILE
        scale = WIDTH / num_rays
        self.ray_depths = [MAX_DEPTH] * num_rays
        self.ray_hits = []
        ox, oy = self.player.x, self.player.y
        angle = self.player.angle - fov / 2
        for ray in range(num_rays):
            sin_a, cos_a = math.sin(angle), math.cos(angle)
            depth = 1
            material = "#"
            hit_x = hit_y = 0
            while depth < MAX_DEPTH:
                x = ox + cos_a * depth
                y = oy + sin_a * depth
                mx, my = cell_at(x, y)
                if mx < 0 or my < 0 or mx >= MAP_W or my >= MAP_H:
                    break
                ch = WORLD_MAP[my][mx]
                if ch == "#" or ch == "C":
                    material = ch
                    hit_x, hit_y = x, y
                    break
                depth += 5
            corrected = depth * math.cos(self.player.angle - angle)
            self.ray_depths[ray] = corrected
            side = 0.82 if abs((hit_x % TILE) - TILE / 2) > abs((hit_y % TILE) - TILE / 2) else 1.0
            h = min(HEIGHT * 2.7, proj_coeff / (corrected + 0.001))
            shade = clamp(260 / (1 + corrected * corrected * 0.0000038), 24, 245)
            if material == "C":
                base = (95, 75, 50)
            else:
                base = (75, 94, 142)
            color = tuple(int(c * shade / 150 * side) for c in base)
            self.ray_hits.append((corrected, int(ray * scale), int(HALF_H - h / 2), int(scale + 1.5), int(h), color, material))
            angle += delta
        return proj_coeff, dist_plane, scale, num_rays

    def project_point(self, x, y, z, fov, dist_plane, scale):
        dx, dy = x - self.player.x, y - self.player.y
        d = math.hypot(dx, dy)
        if d < 8:
            return None
        theta = math.atan2(dy, dx)
        gamma = angle_diff(theta, self.player.angle)
        if abs(gamma) > fov * 0.62:
            return None
        sx = HALF_W + math.tan(gamma) * dist_plane * scale
        # Spielerhöhe durch Sprung verschiebt die Welt im Blickfeld nach unten/oben.
        sy = HALF_H + self.player.jump_z * 1.15 - z * (dist_plane * scale) / d
        return sx, sy, d, gamma

    def draw_background(self, surf):
        # schönerer Himmel mit mehreren Bändern
        for y in range(0, HALF_H, 4):
            t = y / HALF_H
            r = int(14 + 22 * t)
            g = int(20 + 35 * t)
            b = int(45 + 85 * t)
            pygame.draw.rect(surf, (r, g, b), (0, y, WIDTH, 4))
        # Sonne/Neon-Glow
        pulse = 0.5 + 0.5 * math.sin(self.bg_time * 0.8)
        pygame.draw.circle(surf, (45, 70, 120), (WIDTH - 190, 115), int(75 + 8 * pulse))
        pygame.draw.circle(surf, (70, 115, 180), (WIDTH - 190, 115), 42)
        # Boden
        for y in range(HALF_H, HEIGHT, 4):
            t = (y - HALF_H) / HALF_H
            col = (int(28 + 27 * t), int(30 + 24 * t), int(40 + 16 * t))
            pygame.draw.rect(surf, col, (0, y, WIDTH, 4))
        pygame.draw.line(surf, (70, 130, 200), (0, HALF_H), (WIDTH, HALF_H), 2)
        # Perspektivische Bodenlinien
        for i in range(1, 18):
            y = HALF_H + int((i / 18) ** 1.8 * HALF_H)
            pygame.draw.line(surf, (34, 43, 63), (0, y), (WIDTH, y), 1)
        for i in range(-12, 13):
            x = HALF_W + i * 105
            pygame.draw.line(surf, (30, 39, 58), (x, HALF_H), (HALF_W + i * 360, HEIGHT), 1)

    def draw_walls(self, surf):
        for depth, x, y, w, h, color, material in self.ray_hits:
            pygame.draw.rect(surf, color, (x, y, w, h))
            if material == "C":
                if x % 11 < 3:
                    pygame.draw.line(surf, (140, 105, 65), (x, y), (x, y + h), 1)
            else:
                # Wandstruktur: horizontale Streifen je nach Entfernung
                if x % 9 < 2:
                    c2 = tuple(clamp(c + 18, 0, 255) for c in color)
                    pygame.draw.line(surf, c2, (x, y), (x, y + h), 1)
                if h > 90 and x % 17 < 2:
                    pygame.draw.rect(surf, tuple(max(0, c - 22) for c in color), (x, y + h * 0.45, w, 2))

    def draw_sprite_objects(self, surf, fov, dist_plane, scale):
        objs = []
        for e in self.enemies:
            pr = self.project_point(e.x, e.y, 0, fov, dist_plane, scale)
            if pr:
                objs.append((pr[2], "enemy", e, pr))
        for pu in self.pickups:
            pr = self.project_point(pu.x, pu.y, 0, fov, dist_plane, scale)
            if pr:
                objs.append((pr[2], "pickup", pu, pr))
        for prj in self.enemy_projectiles:
            pr = self.project_point(prj.x, prj.y, prj.z, fov, dist_plane, scale)
            if pr:
                objs.append((pr[2], "projectile", prj, pr))
        for gr in self.grenades:
            pr = self.project_point(gr.x, gr.y, gr.z, fov, dist_plane, scale)
            if pr:
                objs.append((pr[2], "grenade", gr, pr))
        for part in self.particles:
            pr = self.project_point(part.x, part.y, part.z, fov, dist_plane, scale)
            if pr:
                objs.append((pr[2], "particle", part, pr))
        for txt in self.texts:
            pr = self.project_point(txt.x, txt.y, txt.z, fov, dist_plane, scale)
            if pr:
                objs.append((pr[2], "text", txt, pr))

        objs.sort(key=lambda x: x[0], reverse=True)
        for d, typ, obj, pr in objs:
            sx, sy, distance, gamma = pr
            ray = int(clamp(sx / (WIDTH / len(self.ray_depths)), 0, len(self.ray_depths) - 1))
            if distance > self.ray_depths[ray] + 45:
                continue
            if typ == "enemy":
                self.draw_enemy(surf, obj, sx, sy, distance)
            elif typ == "pickup":
                self.draw_pickup(surf, obj, sx, sy, distance)
            elif typ == "projectile":
                size = clamp(1900 / distance, 4, 22)
                pygame.draw.circle(surf, obj.color, (int(sx), int(sy)), int(size))
                pygame.draw.circle(surf, WHITE, (int(sx), int(sy)), max(1, int(size/2)))
            elif typ == "grenade":
                size = clamp(2300 / distance, 8, 34)
                pygame.draw.circle(surf, (25, 30, 36), (int(sx), int(sy)), int(size))
                pygame.draw.circle(surf, ORANGE if obj.timer < 0.45 else GREEN, (int(sx), int(sy)), max(2, int(size * 0.38)))
                pygame.draw.circle(surf, WHITE, (int(sx), int(sy)), max(2, int(size * 0.58)), 2)
            elif typ == "particle":
                alpha = clamp(obj.life / obj.max_life, 0, 1)
                size = clamp(obj.size * 250 / distance, 1.4, 12)
                col = tuple(int(c * alpha) for c in obj.color)
                if obj.glow:
                    pygame.draw.circle(surf, tuple(min(255, c+45) for c in col), (int(sx), int(sy)), int(size*1.8))
                pygame.draw.circle(surf, col, (int(sx), int(sy)), int(size))
            elif typ == "text":
                alpha = int(255 * clamp(obj.life / obj.max_life, 0, 1))
                img = FONT_SMALL.render(obj.text, True, obj.color)
                img.set_alpha(alpha)
                surf.blit(img, img.get_rect(center=(sx, sy)))

    def draw_enemy(self, surf, e, sx, sy, d):
        # Stabilere und größere Gegner-Darstellung.
        # Alles wird hier bewusst in int-Rectangles umgewandelt, damit Pygame nicht crasht.
        size = int(clamp(11200 / max(d, 1) * (e.size / 40), 82, 430))
        floor_y = int(HALF_H + self.player.jump_z * 1.15 + clamp(3400 / max(d, 1), 12, 92))
        x = int(sx - size / 2)
        y = int(floor_y - size)
        col = WHITE if e.flash > 0 else e.color
        outline = tuple(max(0, c - 95) for c in col)
        hi = tuple(min(255, c + 34) for c in col)

        def rr(rx, ry, rw, rh):
            return pygame.Rect(int(rx), int(ry), max(1, int(rw)), max(1, int(rh)))

        # Schatten direkt auf dem Boden, damit Gegner nicht wirken, als würden sie schweben oder in der Wand hängen.
        shadow = pygame.Surface((int(size * 1.35), int(size * 0.30)), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 135), shadow.get_rect())
        surf.blit(shadow, (int(x - size * 0.17), int(floor_y - size * 0.11)))

        # Deutliche Silhouette / Trefferfläche
        pygame.draw.rect(surf, (245, 248, 255), rr(x - 3, y - 3, size + 6, size * 1.06 + 6), 2, border_radius=max(9, int(size * 0.06)))

        # Beine und Füße
        pygame.draw.rect(surf, (24, 25, 34), rr(x + size * 0.13, y + size * 0.78, size * 0.27, size * 0.20), border_radius=max(5, int(size * 0.04)))
        pygame.draw.rect(surf, (24, 25, 34), rr(x + size * 0.60, y + size * 0.78, size * 0.27, size * 0.20), border_radius=max(5, int(size * 0.04)))
        pygame.draw.rect(surf, (12, 14, 22), rr(x + size * 0.08, y + size * 0.93, size * 0.34, size * 0.10), border_radius=max(4, int(size * 0.03)))
        pygame.draw.rect(surf, (12, 14, 22), rr(x + size * 0.58, y + size * 0.93, size * 0.34, size * 0.10), border_radius=max(4, int(size * 0.03)))

        # Körper
        pygame.draw.rect(surf, outline, rr(x + size * 0.02, y + size * 0.25, size * 0.96, size * 0.58), border_radius=max(8, int(size * 0.06)))
        pygame.draw.rect(surf, col, rr(x + size * 0.10, y + size * 0.30, size * 0.80, size * 0.46), border_radius=max(7, int(size * 0.05)))
        pygame.draw.rect(surf, hi, rr(x + size * 0.18, y + size * 0.35, size * 0.23, size * 0.33), border_radius=max(4, int(size * 0.025)))
        pygame.draw.rect(surf, tuple(max(0, c - 35) for c in col), rr(x + size * 0.48, y + size * 0.35, size * 0.34, size * 0.12), border_radius=max(4, int(size * 0.025)))

        # Kopf
        pygame.draw.rect(surf, outline, rr(x + size * 0.18, y + size * 0.03, size * 0.64, size * 0.31), border_radius=max(8, int(size * 0.06)))
        pygame.draw.rect(surf, hi, rr(x + size * 0.23, y, size * 0.54, size * 0.30), border_radius=max(8, int(size * 0.055)))

        # Augen
        eye_col = (12, 16, 25)
        pygame.draw.rect(surf, eye_col, rr(x + size * 0.31, y + size * 0.105, size * 0.13, size * 0.075), border_radius=max(2, int(size * 0.015)))
        pygame.draw.rect(surf, eye_col, rr(x + size * 0.56, y + size * 0.105, size * 0.13, size * 0.075), border_radius=max(2, int(size * 0.015)))
        pygame.draw.line(surf, WHITE, (int(x + size * 0.33), int(y + size * 0.105)), (int(x + size * 0.42), int(y + size * 0.105)), max(1, int(size * 0.01)))

        # Gegner-Waffe bei Blaster
        if e.shooter:
            pygame.draw.rect(surf, (25, 28, 38), rr(x + size * 0.58, y + size * 0.50, size * 0.56, size * 0.13), border_radius=max(4, int(size * 0.025)))
            pygame.draw.rect(surf, e.color, rr(x + size * 0.62, y + size * 0.535, size * 0.24, size * 0.035), border_radius=3)
            pygame.draw.circle(surf, e.color, (int(x + size * 1.15), int(y + size * 0.565)), max(3, int(size * 0.045)))

        # Lebensbalken
        hp_p = clamp(e.hp / max(e.max_hp, 1), 0, 1)
        bw = int(size * 0.96)
        bx = int(sx - bw / 2)
        by = int(y - max(18, size * 0.09))
        pygame.draw.rect(surf, (20, 22, 31), rr(bx, by, bw, 10), border_radius=5)
        pygame.draw.rect(surf, GREEN if hp_p > .45 else RED, rr(bx, by, bw * hp_p, 10), border_radius=5)
        pygame.draw.rect(surf, WHITE, rr(bx, by, bw, 10), 1, border_radius=5)
        name = FONT_TINY.render(e.name, True, SOFT)
        surf.blit(name, name.get_rect(center=(int(sx), int(by - 11))))

    def draw_pickup(self, surf, pu, sx, sy, d):
        size = clamp(2600 / d, 18, 78)
        bob = math.sin(pu.t * 4) * size * 0.12
        col = pu.color
        cx, cy = int(sx), int(HALF_H + 35 - size * 0.38 + bob)
        pygame.draw.circle(surf, tuple(max(0, c - 80) for c in col), (cx, cy), int(size * 0.58))
        pygame.draw.circle(surf, col, (cx, cy), int(size * 0.45))
        pygame.draw.circle(surf, WHITE, (cx, cy), int(size * 0.30), 2)
        icon = {"health": "+", "ammo": "A", "armor": "S", "boost": "$"}[pu.kind]
        draw_text(surf, icon, FONT_SMALL, BLACK, center=(cx, cy), shadow=False)

    def draw_weapon(self, surf):
        p = self.player
        w = p.weapon
        aim_shift = 120 if p.aiming else 0
        kick = w.kick * (38 if not p.aiming else 20)
        bob = math.sin(pygame.time.get_ticks() * 0.012) * (2 if p.aiming else 6)
        cx = WIDTH - 365 - aim_shift
        cy = HEIGHT - 195 + kick + bob + self.player.jump_z * 0.20
        col = w.color

        # Arme
        pygame.draw.rect(surf, (197, 150, 112), (cx - 105, cy + 90, 310, 44), border_radius=19)
        pygame.draw.rect(surf, (170, 125, 95), (cx + 50, cy + 105, 180, 34), border_radius=15)
        # Waffe detaillierter
        pygame.draw.rect(surf, (18, 20, 30), (cx - 115, cy + 35, 360, 72), border_radius=13)
        pygame.draw.rect(surf, (48, 55, 76), (cx - 94, cy + 12, 245, 50), border_radius=10)
        pygame.draw.rect(surf, (32, 35, 47), (cx + 58, cy + 76, 70, 93), border_radius=9)
        pygame.draw.rect(surf, (12, 14, 22), (cx + 134, cy + 50, 170, 32), border_radius=7)
        pygame.draw.rect(surf, (25, 27, 36), (cx + 286, cy + 58, 92, 15), border_radius=5)
        pygame.draw.rect(surf, col, (cx - 76, cy + 24, 165, 9), border_radius=5)
        pygame.draw.rect(surf, col, (cx - 16, cy + 45, 95, 5), border_radius=3)
        pygame.draw.circle(surf, col, (int(cx + 383), int(cy + 65)), 7)
        # Scope nur optisch auf der Rail Scout
        if "RAIL" in w.name:
            pygame.draw.rect(surf, (15, 17, 24), (cx - 28, cy - 18, 125, 30), border_radius=13)
            pygame.draw.circle(surf, col, (int(cx + 98), int(cy - 3)), 13, 3)
        # Muzzle flash
        if w.muzzle > 0:
            r = int(18 + random.random() * 18)
            pygame.draw.circle(surf, ORANGE, (int(cx + 398), int(cy + 65)), r)
            pygame.draw.circle(surf, YELLOW, (int(cx + 398), int(cy + 65)), int(r * 0.55))

    def draw_scope_overlay(self, surf):
        if not self.player.aiming:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        pygame.draw.circle(overlay, (0, 0, 0, 0), (HALF_W, HALF_H), 230)
        surf.blit(overlay, (0, 0))
        pygame.draw.circle(surf, (25, 30, 42), (HALF_W, HALF_H), 232, 8)
        pygame.draw.line(surf, (20, 25, 35), (HALF_W - 210, HALF_H), (HALF_W + 210, HALF_H), 2)
        pygame.draw.line(surf, (20, 25, 35), (HALF_W, HALF_H - 210), (HALF_W, HALF_H + 210), 2)
        pygame.draw.circle(surf, CYAN, (HALF_W, HALF_H), 5, 1)

    def draw_crosshair(self, surf):
        p = self.player
        if p.aiming:
            return
        spread = 15 + int(p.weapon.spread * 450) + int(p.weapon.kick * 16)
        col = RED if p.hitmarker > 0 else CYAN if p.headshot_marker > 0 else WHITE
        pygame.draw.line(surf, col, (HALF_W - spread - 13, HALF_H), (HALF_W - spread, HALF_H), 2)
        pygame.draw.line(surf, col, (HALF_W + spread, HALF_H), (HALF_W + spread + 13, HALF_H), 2)
        pygame.draw.line(surf, col, (HALF_W, HALF_H - spread - 13), (HALF_W, HALF_H - spread), 2)
        pygame.draw.line(surf, col, (HALF_W, HALF_H + spread), (HALF_W, HALF_H + spread + 13), 2)
        pygame.draw.circle(surf, col, (HALF_W, HALF_H), 2)
        if p.hitmarker > 0:
            pygame.draw.line(surf, RED, (HALF_W - 22, HALF_H - 22), (HALF_W - 9, HALF_H - 9), 3)
            pygame.draw.line(surf, RED, (HALF_W + 22, HALF_H - 22), (HALF_W + 9, HALF_H - 9), 3)
            pygame.draw.line(surf, RED, (HALF_W - 22, HALF_H + 22), (HALF_W - 9, HALF_H + 9), 3)
            pygame.draw.line(surf, RED, (HALF_W + 22, HALF_H + 22), (HALF_W + 9, HALF_H + 9), 3)

    def draw_hud(self, surf):
        p = self.player
        w = p.weapon
        # HUD Panel
        panel = pygame.Surface((WIDTH, 128), pygame.SRCALPHA)
        pygame.draw.rect(panel, (4, 6, 12, 178), (0, 0, WIDTH, 128))
        pygame.draw.line(panel, (65, 120, 170, 160), (0, 0), (WIDTH, 0), 2)
        surf.blit(panel, (0, HEIGHT - 128))

        def bar(x, y, ww, hh, val, maxv, color, label):
            pygame.draw.rect(surf, (35, 38, 50), (x, y, ww, hh), border_radius=8)
            pygame.draw.rect(surf, color, (x, y, int(ww * clamp(val / maxv, 0, 1)), hh), border_radius=8)
            draw_text(surf, f"{label} {int(val)}", FONT_SMALL, WHITE, topleft=(x + 9, y + 4), shadow=False)

        bar(26, HEIGHT - 102, 300, 27, p.hp, p.max_hp, GREEN if p.hp > 35 else RED, "HP")
        bar(26, HEIGHT - 66, 300, 22, p.armor, 100, BLUE, "ARMOR")
        bar(26, HEIGHT - 36, 300, 13, p.jump_z if p.jump_z > 0 else (1 if p.on_ground else 0), 130, PINK, "JUMP")

        draw_text(surf, w.name, FONT_MED, w.color, topleft=(WIDTH - 440, HEIGHT - 108))
        ammo_color = RED if w.ammo == 0 else WHITE
        draw_text(surf, f"{w.ammo:02d} / {w.reserve:03d}", FONT_MED, ammo_color, topleft=(WIDTH - 440, HEIGHT - 68))
        if w.reloading:
            pygame.draw.rect(surf, (35, 38, 50), (WIDTH - 440, HEIGHT - 28, 260, 8), border_radius=4)
            pygame.draw.rect(surf, YELLOW, (WIDTH - 440, HEIGHT - 28, int(260 * (1 - w.reload_timer / w.reload_time)), 8), border_radius=4)

        draw_text(surf, f"SCORE {p.score}   KILLS {p.kills}   WAVE {self.level}   GRENADES {p.grenades}", FONT, WHITE, center=(HALF_W, HEIGHT - 75))
        if p.combo > 1:
            draw_text(surf, f"COMBO x{p.combo}", FONT_MED, YELLOW, center=(HALF_W, HEIGHT - 34))

        # Waffenleiste mit klar sichtbarem aktiven Slot
        x0 = 365
        for i, weapon in enumerate(p.weapons):
            active = i == p.weapon_index
            rect = pygame.Rect(x0 + i * 154, HEIGHT - 121, 140, 38)
            pygame.draw.rect(surf, weapon.color if active else (40, 45, 60), rect, border_radius=10)
            pygame.draw.rect(surf, WHITE if active else (80, 90, 110), rect, 2, border_radius=10)
            draw_text(surf, f"{i+1} {weapon.name[:10]}", FONT_TINY, BLACK if active else WHITE, center=rect.center, shadow=False)
            ammo_txt = FONT_TINY.render(f"{weapon.ammo}/{weapon.reserve}", True, BLACK if active else SOFT)
            surf.blit(ammo_txt, ammo_txt.get_rect(midtop=(rect.centerx, rect.bottom + 2)))

        if p.weapon_switch_flash > 0:
            alpha = int(210 * p.weapon_switch_flash)
            big = FONT_BIG.render(p.weapon.name, True, p.weapon.color)
            big.set_alpha(alpha)
            surf.blit(big, big.get_rect(center=(HALF_W, HALF_H + 115)))

        self.draw_minimap(surf)
        if self.message_timer > 0:
            alpha = 255 if self.message_timer > 0.55 else int(255 * self.message_timer / 0.55)
            img = FONT_MED.render(self.message, True, WHITE)
            img.set_alpha(alpha)
            surf.blit(img, img.get_rect(center=(HALF_W, 92)))

        # Damage Overlay
        if p.damage_flash > 0:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 30, 45, int(90 * p.damage_flash)))
            surf.blit(overlay, (0, 0))

    def draw_minimap(self, surf):
        p = self.player
        scale = 10 if not p.minimap_big else 17
        w, h = MAP_W * scale, MAP_H * scale
        x0 = WIDTH - w - 28
        y0 = 24
        mm = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mm, (0, 0, 0, 145), (0, 0, w, h), border_radius=10)
        for y, row in enumerate(WORLD_MAP):
            for x, ch in enumerate(row):
                if ch == "#":
                    pygame.draw.rect(mm, (95, 110, 155, 200), (x * scale, y * scale, scale, scale))
                elif ch == "C":
                    pygame.draw.rect(mm, (115, 80, 45, 210), (x * scale, y * scale, scale, scale))
        pygame.draw.circle(mm, CYAN, (int(p.x / TILE * scale), int(p.y / TILE * scale)), max(4, scale // 2))
        pygame.draw.line(mm, CYAN, (int(p.x/TILE*scale), int(p.y/TILE*scale)), (int((p.x/TILE+math.cos(p.angle)*1.2)*scale), int((p.y/TILE+math.sin(p.angle)*1.2)*scale)), 2)
        for e in self.enemies:
            pygame.draw.circle(mm, e.color, (int(e.x / TILE * scale), int(e.y / TILE * scale)), max(3, scale // 3))
        for pu in self.pickups:
            pygame.draw.circle(mm, pu.color, (int(pu.x / TILE * scale), int(pu.y / TILE * scale)), max(2, scale // 4))
        pygame.draw.rect(mm, (100, 180, 240, 200), (0, 0, w, h), 2, border_radius=10)
        surf.blit(mm, (x0, y0))

    def draw_menu(self, surf):
        surf.fill((7, 9, 18))
        # animierte Neon-Partikel
        for i in range(150):
            x = (i * 97 + self.bg_time * 55 * (0.3 + i % 5 * 0.08)) % WIDTH
            y = (i * 53 + math.sin(self.bg_time + i) * 12) % HEIGHT
            col = [CYAN, BLUE, PURPLE, ORANGE][i % 4]
            pygame.draw.circle(surf, tuple(int(c * 0.35) for c in col), (int(x), int(y)), 2 + i % 3)
        draw_text(surf, "BLOCKSTRIKE", FONT_HUGE, CYAN, center=(HALF_W, 150))
        draw_text(surf, "ARENA", FONT_BIG, WHITE, center=(HALF_W, 230))
        draw_text(surf, "lokaler Krunker-Style Shooter mit Raycasting, Wellen, Waffen, Pickups und Gegner-KI", FONT, SOFT, center=(HALF_W, 292))
        lines = [
            "WASD bewegen   |   Maus umsehen   |   Linksklick schießen   |   Rechtsklick: Scope nur Rail Scout",
            "R nachladen    |   Shift sprinten  |   Leertaste springen    |   1/2/3/4 Waffen",
            "Mausrad/Q/E Waffen wechseln | G Granate | M Minimap | ESC Pause",
            "Gegner sind jetzt größer, höher aufgelöst und klarer vom Boden getrennt."
        ]
        for i, line in enumerate(lines):
            draw_text(surf, line, FONT, SOFT, center=(HALF_W, 350 + i * 38))

        self.menu_buttons = []
        mouse = pygame.mouse.get_pos()
        buttons = [("SPIEL STARTEN", "start", CYAN), ("BEENDEN", "quit", RED)]
        for i, (label, action, color) in enumerate(buttons):
            rect = pygame.Rect(HALF_W - 245, 555 + i * 78, 490, 58)
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(surf, color if hover else (18, 24, 38), rect, border_radius=16)
            pygame.draw.rect(surf, WHITE if hover else color, rect, 3, border_radius=16)
            draw_text(surf, label, FONT_MED, BLACK if hover else color, center=rect.center, shadow=False)
            self.menu_buttons.append((rect, action))

    def draw_pause(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        surf.blit(overlay, (0, 0))
        draw_text(surf, "PAUSE", FONT_BIG, WHITE, center=(HALF_W, HALF_H - 120))
        self.menu_buttons = []
        mouse = pygame.mouse.get_pos()
        buttons = [("WEITERSPIELEN", "resume", CYAN), ("NEUSTART", "restart", YELLOW), ("BEENDEN", "quit", RED)]
        for i, (label, action, color) in enumerate(buttons):
            rect = pygame.Rect(HALF_W - 240, HALF_H - 35 + i * 72, 480, 52)
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(surf, color if hover else (18, 24, 38), rect, border_radius=15)
            pygame.draw.rect(surf, WHITE if hover else color, rect, 3, border_radius=15)
            draw_text(surf, label, FONT_MED, BLACK if hover else color, center=rect.center, shadow=False)
            self.menu_buttons.append((rect, action))

    def draw_dead(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 198))
        surf.blit(overlay, (0, 0))
        draw_text(surf, "GAME OVER", FONT_BIG, RED, center=(HALF_W, 220))
        draw_text(surf, f"Score {self.player.score} | Kills {self.player.kills} | Wave {self.level}", FONT_MED, WHITE, center=(HALF_W, 310))
        self.menu_buttons = []
        mouse = pygame.mouse.get_pos()
        buttons = [("NOCHMAL SPIELEN", "restart", CYAN), ("BEENDEN", "quit", RED)]
        for i, (label, action, color) in enumerate(buttons):
            rect = pygame.Rect(HALF_W - 245, 390 + i * 74, 490, 54)
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(surf, color if hover else (18, 24, 38), rect, border_radius=15)
            pygame.draw.rect(surf, WHITE if hover else color, rect, 3, border_radius=15)
            draw_text(surf, label, FONT_MED, BLACK if hover else color, center=rect.center, shadow=False)
            self.menu_buttons.append((rect, action))

    def render(self):
        if self.state == "menu":
            self.draw_menu(WIN)
            pygame.display.flip()
            return

        fov = FOV_AIM if self.player.aiming else FOV_NORMAL
        proj_coeff, dist_plane, scale, rays = self.cast_rays(fov)
        scene = pygame.Surface((WIDTH, HEIGHT))
        self.draw_background(scene)
        self.draw_walls(scene)
        self.draw_sprite_objects(scene, fov, dist_plane, scale)
        self.draw_scope_overlay(scene)
        self.draw_weapon(scene)
        self.draw_crosshair(scene)
        self.draw_hud(scene)

        # Screenshake am Ende
        sx = int(random.uniform(-9, 9) * self.player.shake)
        sy = int(random.uniform(-7, 7) * self.player.shake)
        WIN.fill(BLACK)
        WIN.blit(scene, (sx, sy))
        if self.state == "pause":
            self.draw_pause(WIN)
        if self.state == "dead":
            self.draw_dead(WIN)
        pygame.display.flip()

    def run(self):
        while True:
            dt = CLOCK.tick(FPS) / 1000
            self.handle_events()
            self.update(dt)
            self.render()

if __name__ == "__main__":
    Game().run()
