import pygame
import math
import random
import sys
from dataclasses import dataclass

# ============================================================
#  MINI-KRUNKER LOCAL SHOOTER
#  Ein lokaler FPS im Raycasting-Stil mit Gegnern, Waffen,
#  Partikeln, Treffer-Feedback, Minimap, Menüs, Level, Sounds
#  Benötigt: pip install pygame
#  Start: python krunker_style_local_shooter.py
# ============================================================

pygame.init()
try:
    pygame.mixer.init()
except Exception:
    pass

WIDTH, HEIGHT = 1280, 720
HALF_W, HALF_H = WIDTH // 2, HEIGHT // 2
FPS = 60
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Block Arena Shooter - Local Edition")
CLOCK = pygame.time.Clock()

# ----------------------------
# Farben
# ----------------------------
BLACK = (8, 9, 14)
WHITE = (240, 245, 255)
GREY = (120, 125, 140)
DARK = (17, 18, 28)
RED = (255, 70, 80)
GREEN = (75, 255, 130)
BLUE = (70, 160, 255)
CYAN = (80, 230, 255)
YELLOW = (255, 220, 90)
ORANGE = (255, 150, 50)
PURPLE = (180, 100, 255)

FONT = pygame.font.SysFont("consolas", 22)
FONT_BIG = pygame.font.SysFont("consolas", 62, bold=True)
FONT_MED = pygame.font.SysFont("consolas", 34, bold=True)
FONT_SMALL = pygame.font.SysFont("consolas", 16)

# ----------------------------
# Raycasting / Welt
# ----------------------------
TILE = 96
MAP_W, MAP_H = 18, 18
FOV = math.radians(72)
NUM_RAYS = 240
MAX_DEPTH = 1600
DELTA_ANGLE = FOV / NUM_RAYS
DIST = NUM_RAYS / (2 * math.tan(FOV / 2))
PROJ_COEFF = 3 * DIST * TILE
SCALE = WIDTH // NUM_RAYS + 1

WORLD_MAP = [
    "##################",
    "#........#.......#",
    "#..##....#..##...#",
    "#..#.........#...#",
    "#......##........#",
    "###............###",
    "#....#............#"[:18],
    "#....#.....##....#",
    "#..........##....#",
    "#..####..........#",
    "#..............#.#",
    "#....##........#.#",
    "#....##....#.....#",
    "#..........#.....#",
    "#..##............#",
    "#...........##...#",
    "#.....#..........#",
    "##################",
]
# Sicherheitskorrektur, falls eine Zeile zu lang/kurz ist
WORLD_MAP = [(row + "#" * MAP_W)[:MAP_W] for row in WORLD_MAP[:MAP_H]]

WALL_COLORS = {
    "#": (80, 90, 125),
}

# ----------------------------
# Hilfsfunktionen
# ----------------------------
def clamp(v, a, b):
    return max(a, min(b, v))


def length(dx, dy):
    return math.hypot(dx, dy)


def angle_norm(a):
    return a % (math.tau)


def angle_diff(a, b):
    return (a - b + math.pi) % (math.tau) - math.pi


def cell_at_px(x, y):
    return int(x // TILE), int(y // TILE)


def is_wall_px(x, y):
    mx, my = cell_at_px(x, y)
    if mx < 0 or my < 0 or mx >= MAP_W or my >= MAP_H:
        return True
    return WORLD_MAP[my][mx] == "#"


def has_line_of_sight(x1, y1, x2, y2, step=24):
    dist = length(x2 - x1, y2 - y1)
    steps = max(1, int(dist / step))
    for i in range(1, steps + 1):
        t = i / steps
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        if is_wall_px(x, y):
            return False
    return True

# ----------------------------
# Fake-Sound: kurze Beeps ohne externe Dateien
# ----------------------------
def beep(freq=440, duration_ms=60, volume=0.15):
    try:
        import array
        sample_rate = 22050
        n = int(sample_rate * duration_ms / 1000)
        buf = array.array("h")
        amp = int(32767 * volume)
        for i in range(n):
            val = int(amp * math.sin(math.tau * freq * i / sample_rate))
            buf.append(val)
        snd = pygame.mixer.Sound(buffer=buf)
        snd.play()
    except Exception:
        pass

# ----------------------------
# Partikel
# ----------------------------
@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: tuple
    size: float

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= dt

    def alive(self):
        return self.life > 0

# ----------------------------
# Waffe
# ----------------------------
class Weapon:
    def __init__(self, name, damage, fire_rate, mag_size, reload_time, spread, recoil, color):
        self.name = name
        self.damage = damage
        self.fire_rate = fire_rate
        self.mag_size = mag_size
        self.reload_time = reload_time
        self.spread = spread
        self.recoil = recoil
        self.color = color
        self.ammo = mag_size
        self.reserve = mag_size * 5
        self.cooldown = 0
        self.reloading = False
        self.reload_timer = 0
        self.kick = 0

    def update(self, dt):
        self.cooldown = max(0, self.cooldown - dt)
        self.kick *= 0.84
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

    def start_reload(self):
        if not self.reloading and self.ammo < self.mag_size and self.reserve > 0:
            self.reloading = True
            self.reload_timer = self.reload_time
            beep(260, 45, 0.07)

    def fired(self):
        self.ammo -= 1
        self.cooldown = 1 / self.fire_rate
        self.kick = 1.0
        beep(140 + random.randint(0, 40), 35, 0.12)

# ----------------------------
# Spieler
# ----------------------------
class Player:
    def __init__(self):
        self.x = 2.5 * TILE
        self.y = 2.5 * TILE
        self.angle = 0.0
        self.speed = 270
        self.strafe_speed = 245
        self.rot_speed = 2.6
        self.hp = 100
        self.max_hp = 100
        self.armor = 25
        self.score = 0
        self.kills = 0
        self.damage_flash = 0
        self.hit_marker = 0
        self.shake = 0
        self.sprint = 1.0
        self.weapon_index = 0
        self.weapons = [
            Weapon("VECTOR SMG", 17, 11.5, 32, 1.35, 0.030, 0.025, CYAN),
            Weapon("SCOUT RIFLE", 52, 2.4, 8, 1.75, 0.006, 0.055, ORANGE),
            Weapon("BLOCK PISTOL", 25, 5.2, 14, 1.05, 0.015, 0.025, YELLOW),
        ]

    @property
    def weapon(self):
        return self.weapons[self.weapon_index]

    def update(self, dt, keys):
        weapon = self.weapon
        weapon.update(dt)
        self.damage_flash = max(0, self.damage_flash - dt * 2.8)
        self.hit_marker = max(0, self.hit_marker - dt * 4.0)
        self.shake = max(0, self.shake - dt * 9.0)

        sprinting = keys[pygame.K_LSHIFT] and keys[pygame.K_w]
        self.sprint = 1.35 if sprinting else 1.0
        move_speed = self.speed * self.sprint

        sin_a = math.sin(self.angle)
        cos_a = math.cos(self.angle)
        dx = dy = 0
        if keys[pygame.K_w]:
            dx += cos_a * move_speed * dt
            dy += sin_a * move_speed * dt
        if keys[pygame.K_s]:
            dx -= cos_a * move_speed * dt * 0.8
            dy -= sin_a * move_speed * dt * 0.8
        if keys[pygame.K_a]:
            dx += sin_a * self.strafe_speed * dt
            dy -= cos_a * self.strafe_speed * dt
        if keys[pygame.K_d]:
            dx -= sin_a * self.strafe_speed * dt
            dy += cos_a * self.strafe_speed * dt

        self.move(dx, dy)

        if keys[pygame.K_LEFT]:
            self.angle -= self.rot_speed * dt
        if keys[pygame.K_RIGHT]:
            self.angle += self.rot_speed * dt
        self.angle = angle_norm(self.angle)

    def move(self, dx, dy):
        pad = 22
        nx = self.x + dx
        if not is_wall_px(nx + math.copysign(pad, dx if dx != 0 else 1), self.y):
            self.x = nx
        ny = self.y + dy
        if not is_wall_px(self.x, ny + math.copysign(pad, dy if dy != 0 else 1)):
            self.y = ny

    def damage(self, amount):
        if self.armor > 0:
            armor_take = min(self.armor, amount * 0.55)
            self.armor -= armor_take
            amount -= armor_take * 0.65
        self.hp -= amount
        self.damage_flash = 1.0
        self.shake = 1.0
        beep(90, 70, 0.11)

# ----------------------------
# Gegner
# ----------------------------
class Enemy:
    TYPES = [
        {"name": "Runner", "hp": 55, "speed": 155, "damage": 9, "color": RED, "size": 34},
        {"name": "Heavy", "hp": 120, "speed": 85, "damage": 18, "color": PURPLE, "size": 44},
        {"name": "Striker", "hp": 78, "speed": 120, "damage": 13, "color": ORANGE, "size": 38},
    ]

    def __init__(self, x, y, level=1):
        t = random.choice(self.TYPES)
        self.kind = t["name"]
        self.x = x
        self.y = y
        self.hp = t["hp"] + level * 8
        self.max_hp = self.hp
        self.speed = t["speed"] + level * 3
        self.damage_amt = t["damage"] + level * 1.2
        self.color = t["color"]
        self.size = t["size"]
        self.attack_cd = random.random() * 0.5
        self.stun = 0
        self.wander_angle = random.random() * math.tau
        self.wander_timer = random.uniform(0.3, 1.8)
        self.dead = False
        self.death_timer = 0

    def update(self, dt, player, particles):
        if self.dead:
            self.death_timer -= dt
            return
        self.attack_cd = max(0, self.attack_cd - dt)
        self.stun = max(0, self.stun - dt)
        dist = length(player.x - self.x, player.y - self.y)
        see = dist < 850 and has_line_of_sight(self.x, self.y, player.x, player.y)

        if self.stun <= 0:
            if see:
                ang = math.atan2(player.y - self.y, player.x - self.x)
                side = math.sin(pygame.time.get_ticks() * 0.0015 + self.x) * 0.45
                ang += side
                dx = math.cos(ang) * self.speed * dt
                dy = math.sin(ang) * self.speed * dt
                self.try_move(dx, dy)
            else:
                self.wander_timer -= dt
                if self.wander_timer <= 0:
                    self.wander_angle = random.random() * math.tau
                    self.wander_timer = random.uniform(0.5, 1.8)
                dx = math.cos(self.wander_angle) * self.speed * 0.33 * dt
                dy = math.sin(self.wander_angle) * self.speed * 0.33 * dt
                self.try_move(dx, dy)

        if dist < self.size + 28 and self.attack_cd <= 0:
            player.damage(self.damage_amt)
            self.attack_cd = 0.75
            for _ in range(8):
                a = random.random() * math.tau
                particles.append(Particle(player.x, player.y, math.cos(a)*120, math.sin(a)*120, 0.28, 0.28, RED, 5))

    def try_move(self, dx, dy):
        nx = self.x + dx
        if not is_wall_px(nx, self.y):
            self.x = nx
        else:
            self.wander_angle += random.uniform(1, 2)
        ny = self.y + dy
        if not is_wall_px(self.x, ny):
            self.y = ny
        else:
            self.wander_angle += random.uniform(1, 2)

    def hit(self, dmg, player, particles):
        self.hp -= dmg
        self.stun = 0.055
        for _ in range(12):
            a = random.random() * math.tau
            sp = random.uniform(80, 260)
            particles.append(Particle(self.x, self.y, math.cos(a)*sp, math.sin(a)*sp, random.uniform(0.22, 0.55), 0.55, self.color, random.uniform(3, 7)))
        if self.hp <= 0 and not self.dead:
            self.dead = True
            self.death_timer = 0.5
            player.score += 100
            player.kills += 1
            if random.random() < 0.45:
                player.armor = min(100, player.armor + random.randint(4, 12))
            for _ in range(26):
                a = random.random() * math.tau
                sp = random.uniform(130, 430)
                particles.append(Particle(self.x, self.y, math.cos(a)*sp, math.sin(a)*sp, random.uniform(0.35, 0.85), 0.85, self.color, random.uniform(4, 10)))
            beep(580, 70, 0.11)

# ----------------------------
# Pickups
# ----------------------------
class Pickup:
    def __init__(self, x, y, kind):
        self.x = x
        self.y = y
        self.kind = kind
        self.t = random.random() * 10

    def update(self, dt):
        self.t += dt

    def apply(self, player):
        if self.kind == "health":
            player.hp = min(player.max_hp, player.hp + 35)
            beep(620, 80, 0.08)
        elif self.kind == "ammo":
            for w in player.weapons:
                w.reserve += w.mag_size
            beep(440, 80, 0.08)
        elif self.kind == "armor":
            player.armor = min(100, player.armor + 35)
            beep(520, 80, 0.08)

# ----------------------------
# Spielzustand
# ----------------------------
class Game:
    def __init__(self):
        self.state = "menu"
        self.player = Player()
        self.enemies = []
        self.particles = []
        self.pickups = []
        self.ray_depths = [MAX_DEPTH] * NUM_RAYS
        self.level = 1
        self.wave_timer = 0
        self.mouse_locked = False
        self.message = ""
        self.message_timer = 0
        self.spawn_wave()

    def reset(self):
        self.__init__()
        self.state = "play"
        self.lock_mouse(True)

    def lock_mouse(self, value):
        self.mouse_locked = value
        pygame.mouse.set_visible(not value)
        pygame.event.set_grab(value)

    def random_empty_pos(self):
        for _ in range(500):
            mx = random.randint(1, MAP_W - 2)
            my = random.randint(1, MAP_H - 2)
            if WORLD_MAP[my][mx] != "#":
                x = (mx + 0.5) * TILE
                y = (my + 0.5) * TILE
                if length(x - self.player.x, y - self.player.y) > 350:
                    return x, y
        return 3 * TILE, 3 * TILE

    def spawn_wave(self):
        amount = 5 + self.level * 2
        for _ in range(amount):
            x, y = self.random_empty_pos()
            self.enemies.append(Enemy(x, y, self.level))
        for _ in range(4):
            x, y = self.random_empty_pos()
            self.pickups.append(Pickup(x, y, random.choice(["health", "ammo", "armor"])))
        self.message = f"WAVE {self.level}"
        self.message_timer = 2.2

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == "play":
                        self.state = "pause"
                        self.lock_mouse(False)
                    elif self.state == "pause":
                        self.state = "play"
                        self.lock_mouse(True)
                if self.state in ("menu", "dead") and event.key == pygame.K_RETURN:
                    self.reset()
                if self.state == "play":
                    if event.key == pygame.K_r:
                        self.player.weapon.start_reload()
                    if event.key == pygame.K_1:
                        self.player.weapon_index = 0
                    if event.key == pygame.K_2:
                        self.player.weapon_index = 1
                    if event.key == pygame.K_3:
                        self.player.weapon_index = 2
            if event.type == pygame.MOUSEMOTION and self.state == "play":
                mx, _ = event.rel
                self.player.angle += mx * 0.0026
                self.player.angle = angle_norm(self.player.angle)
            if event.type == pygame.MOUSEBUTTONDOWN and self.state == "play":
                if event.button == 1:
                    self.shoot()
                if event.button == 4:
                    self.player.weapon_index = (self.player.weapon_index - 1) % len(self.player.weapons)
                if event.button == 5:
                    self.player.weapon_index = (self.player.weapon_index + 1) % len(self.player.weapons)

    def update(self, dt):
        if self.state != "play":
            return
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)
        if pygame.mouse.get_pressed()[0]:
            self.shoot()
        for enemy in self.enemies:
            enemy.update(dt, self.player, self.particles)
        self.enemies = [e for e in self.enemies if not (e.dead and e.death_timer <= 0)]
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive()]
        for pu in self.pickups[:]:
            pu.update(dt)
            if length(pu.x - self.player.x, pu.y - self.player.y) < 42:
                pu.apply(self.player)
                self.pickups.remove(pu)
        if not self.enemies:
            self.level += 1
            self.spawn_wave()
        self.message_timer = max(0, self.message_timer - dt)
        if self.player.hp <= 0:
            self.state = "dead"
            self.lock_mouse(False)

    def shoot(self):
        player = self.player
        weapon = player.weapon
        if weapon.reloading:
            return
        if weapon.ammo <= 0:
            weapon.start_reload()
            return
        if not weapon.can_fire():
            return
        weapon.fired()
        player.shake = max(player.shake, 0.33)
        player.angle += random.uniform(-weapon.recoil, weapon.recoil)

        shot_angle = player.angle + random.uniform(-weapon.spread, weapon.spread)
        best = None
        best_score = 999999
        for e in self.enemies:
            if e.dead:
                continue
            dx, dy = e.x - player.x, e.y - player.y
            dist = length(dx, dy)
            if dist > 1250:
                continue
            ang_to = math.atan2(dy, dx)
            diff = abs(angle_diff(ang_to, shot_angle))
            hit_width = math.atan2(e.size, dist)
            if diff < hit_width and has_line_of_sight(player.x, player.y, e.x, e.y):
                score = dist + diff * 2000
                if score < best_score:
                    best = e
                    best_score = score
        if best:
            dist = length(best.x - player.x, best.y - player.y)
            falloff = clamp(1.18 - dist / 1300, 0.55, 1.0)
            dmg = weapon.damage * falloff
            if abs(angle_diff(math.atan2(best.y-player.y, best.x-player.x), shot_angle)) < 0.012:
                dmg *= 1.6
                self.message = "HEADSHOT"
                self.message_timer = 0.55
            best.hit(dmg, player, self.particles)
            player.hit_marker = 1.0
            player.score += int(dmg)
        else:
            # Staub am Ende der Kugelrichtung
            for _ in range(4):
                d = random.uniform(280, 700)
                x = player.x + math.cos(shot_angle) * d
                y = player.y + math.sin(shot_angle) * d
                if not is_wall_px(x, y):
                    self.particles.append(Particle(x, y, random.uniform(-30,30), random.uniform(-30,30), 0.25, 0.25, GREY, 3))

    # ----------------------------
    # Rendering
    # ----------------------------
    def cast_rays(self):
        ox, oy = self.player.x, self.player.y
        cur_angle = self.player.angle - FOV / 2
        walls = []
        for ray in range(NUM_RAYS):
            sin_a = math.sin(cur_angle)
            cos_a = math.cos(cur_angle)
            depth = 1
            hit_vertical = False
            while depth < MAX_DEPTH:
                x = ox + depth * cos_a
                y = oy + depth * sin_a
                if is_wall_px(x, y):
                    hit_vertical = abs((x % TILE) - TILE/2) > abs((y % TILE) - TILE/2)
                    break
                depth += 6
            depth *= math.cos(self.player.angle - cur_angle)
            self.ray_depths[ray] = depth
            proj_h = min(HEIGHT * 2, PROJ_COEFF / (depth + 0.001))
            shade = clamp(255 / (1 + depth * depth * 0.000005), 35, 235)
            base = 0.75 if hit_vertical else 1.0
            c = (int(shade * 0.46 * base), int(shade * 0.54 * base), int(shade * 0.74 * base))
            x_screen = ray * SCALE
            walls.append((depth, x_screen, HALF_H - proj_h // 2, SCALE, proj_h, c))
            cur_angle += DELTA_ANGLE
        return walls

    def draw_background(self, surf, shake_x, shake_y):
        # Himmel mit einfachen Streifen
        for i in range(0, HALF_H, 8):
            t = i / HALF_H
            col = (int(20 + 18*t), int(28 + 34*t), int(55 + 65*t))
            pygame.draw.rect(surf, col, (0, i + shake_y, WIDTH, 8))
        # Boden
        for i in range(HALF_H, HEIGHT, 6):
            t = (i - HALF_H) / HALF_H
            col = (int(32 + 22*t), int(33 + 20*t), int(43 + 18*t))
            pygame.draw.rect(surf, col, (0, i + shake_y, WIDTH, 6))
        # Neon-Horizont
        pygame.draw.line(surf, (70, 115, 180), (0, HALF_H + shake_y), (WIDTH, HALF_H + shake_y), 2)

    def render_sprites(self, surf):
        objects = []
        px, py = self.player.x, self.player.y

        for e in self.enemies:
            dx, dy = e.x - px, e.y - py
            dist = length(dx, dy)
            theta = math.atan2(dy, dx)
            gamma = angle_diff(theta, self.player.angle)
            if abs(gamma) < FOV / 1.65 and dist > 20:
                screen_x = HALF_W + math.tan(gamma) * DIST * SCALE
                size = clamp(PROJ_COEFF / dist * (e.size / 42), 18, 260)
                objects.append((dist, "enemy", e, screen_x, size))

        for pu in self.pickups:
            dx, dy = pu.x - px, pu.y - py
            dist = length(dx, dy)
            theta = math.atan2(dy, dx)
            gamma = angle_diff(theta, self.player.angle)
            if abs(gamma) < FOV / 1.7 and dist > 20:
                screen_x = HALF_W + math.tan(gamma) * DIST * SCALE
                size = clamp(PROJ_COEFF / dist * 0.35, 14, 90)
                objects.append((dist, "pickup", pu, screen_x, size))

        objects.sort(reverse=True, key=lambda x: x[0])
        for dist, kind, obj, sx, size in objects:
            ray = int(clamp(sx / SCALE, 0, NUM_RAYS - 1))
            if dist > self.ray_depths[ray] + 30:
                continue
            if kind == "enemy":
                x = int(sx - size/2)
                y = int(HALF_H - size/2 + 35)
                shadow = pygame.Surface((int(size*1.15), int(size*0.35)), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow, (0,0,0,95), shadow.get_rect())
                surf.blit(shadow, (x - size*0.08, y + size*0.82))
                col = obj.color
                # Körper blockig wie Arena-Shooter
                pygame.draw.rect(surf, (max(col[0]-70,0), max(col[1]-70,0), max(col[2]-70,0)), (x, y, int(size), int(size)), border_radius=8)
                pygame.draw.rect(surf, col, (x+5, y+5, int(size)-10, int(size)-10), border_radius=7)
                pygame.draw.rect(surf, WHITE, (x+size*0.22, y+size*0.26, size*0.18, size*0.13), border_radius=3)
                pygame.draw.rect(surf, WHITE, (x+size*0.60, y+size*0.26, size*0.18, size*0.13), border_radius=3)
                # Lebensbalken
                hp_w = int(size)
                hp_p = clamp(obj.hp / obj.max_hp, 0, 1)
                pygame.draw.rect(surf, (30,30,35), (x, y - 12, hp_w, 6), border_radius=3)
                pygame.draw.rect(surf, GREEN if hp_p > .45 else RED, (x, y - 12, int(hp_w*hp_p), 6), border_radius=3)
            else:
                x = int(sx - size/2)
                y = int(HALF_H - size/2 + math.sin(obj.t*4)*6)
                col = GREEN if obj.kind == "health" else YELLOW if obj.kind == "ammo" else BLUE
                pygame.draw.circle(surf, col, (int(sx), int(y+size/2)), int(size/2))
                pygame.draw.circle(surf, WHITE, (int(sx), int(y+size/2)), int(size/3), 2)
                icon = "+" if obj.kind == "health" else "A" if obj.kind == "ammo" else "S"
                txt = FONT_SMALL.render(icon, True, BLACK)
                surf.blit(txt, txt.get_rect(center=(int(sx), int(y+size/2))))

    def render_particles_3d(self, surf):
        px, py = self.player.x, self.player.y
        for p in self.particles:
            dx, dy = p.x - px, p.y - py
            dist = length(dx, dy)
            if dist < 15 or dist > 1000:
                continue
            theta = math.atan2(dy, dx)
            gamma = angle_diff(theta, self.player.angle)
            if abs(gamma) < FOV / 1.5:
                sx = HALF_W + math.tan(gamma) * DIST * SCALE
                ray = int(clamp(sx / SCALE, 0, NUM_RAYS - 1))
                if dist > self.ray_depths[ray] + 25:
                    continue
                sy = HALF_H + 35 - (PROJ_COEFF / dist) * 0.05
                alpha = clamp(p.life / p.max_life, 0, 1)
                size = clamp(p.size * 200 / dist, 1.5, 8)
                col = tuple(int(c * alpha) for c in p.color)
                pygame.draw.circle(surf, col, (int(sx), int(sy)), int(size))

    def draw_weapon(self, surf):
        w = self.player.weapon
        kick = w.kick * 34
        bob = math.sin(pygame.time.get_ticks() * 0.012) * (4 if self.player.sprint > 1 else 2)
        cx = WIDTH - 285
        cy = HEIGHT - 170 + kick + bob
        col = w.color
        # Arme
        pygame.draw.rect(surf, (210, 170, 130), (cx-70, cy+68, 220, 35), border_radius=16)
        # Waffe: mehrere Blockteile
        pygame.draw.rect(surf, (25, 28, 38), (cx-90, cy+15, 270, 65), border_radius=13)
        pygame.draw.rect(surf, (45, 52, 70), (cx-72, cy, 185, 42), border_radius=9)
        pygame.draw.rect(surf, col, (cx-60, cy+7, 120, 9), border_radius=4)
        pygame.draw.rect(surf, (15, 17, 25), (cx+50, cy+38, 55, 75), border_radius=8)
        pygame.draw.rect(surf, (35, 37, 48), (cx+120, cy+25, 115, 26), border_radius=8)
        pygame.draw.rect(surf, (20,20,25), (cx+210, cy+30, 70, 13), border_radius=4)
        pygame.draw.circle(surf, col, (cx+285, cy+36), 6)
        if w.kick > 0.3:
            pygame.draw.circle(surf, ORANGE, (cx+303, cy+36), int(12 + random.random()*14))
            pygame.draw.circle(surf, YELLOW, (cx+303, cy+36), int(6 + random.random()*8))

    def draw_hud(self, surf):
        p = self.player
        w = p.weapon
        # Crosshair
        ch_col = RED if p.hit_marker > 0 else WHITE
        gap = 9 if p.hit_marker <= 0 else 15
        pygame.draw.line(surf, ch_col, (HALF_W-gap-10, HALF_H), (HALF_W-gap, HALF_H), 2)
        pygame.draw.line(surf, ch_col, (HALF_W+gap, HALF_H), (HALF_W+gap+10, HALF_H), 2)
        pygame.draw.line(surf, ch_col, (HALF_W, HALF_H-gap-10), (HALF_W, HALF_H-gap), 2)
        pygame.draw.line(surf, ch_col, (HALF_W, HALF_H+gap), (HALF_W, HALF_H+gap+10), 2)
        if p.hit_marker > 0:
            pygame.draw.line(surf, RED, (HALF_W-18, HALF_H-18), (HALF_W+18, HALF_H+18), 2)
            pygame.draw.line(surf, RED, (HALF_W+18, HALF_H-18), (HALF_W-18, HALF_H+18), 2)

        # Untere HUD-Box
        panel = pygame.Surface((WIDTH, 118), pygame.SRCALPHA)
        pygame.draw.rect(panel, (4, 6, 12, 155), (0, 0, WIDTH, 118))
        surf.blit(panel, (0, HEIGHT-118))

        def bar(x, y, ww, hh, val, maxv, col, label):
            pygame.draw.rect(surf, (35, 37, 48), (x, y, ww, hh), border_radius=7)
            pygame.draw.rect(surf, col, (x, y, int(ww*clamp(val/maxv,0,1)), hh), border_radius=7)
            surf.blit(FONT_SMALL.render(f"{label}: {int(val)}", True, WHITE), (x+8, y+3))

        bar(26, HEIGHT-96, 260, 24, p.hp, p.max_hp, GREEN if p.hp > 35 else RED, "HP")
        bar(26, HEIGHT-62, 260, 20, p.armor, 100, BLUE, "ARMOR")

        surf.blit(FONT.render(f"{w.name}", True, w.color), (WIDTH-370, HEIGHT-100))
        ammo_col = RED if w.ammo == 0 else WHITE
        surf.blit(FONT_MED.render(f"{w.ammo:02d} / {w.reserve:03d}", True, ammo_col), (WIDTH-370, HEIGHT-68))
        if w.reloading:
            surf.blit(FONT_SMALL.render("RELOADING...", True, YELLOW), (WIDTH-370, HEIGHT-30))
        surf.blit(FONT.render(f"Score {p.score}   Kills {p.kills}   Wave {self.level}", True, WHITE), (330, HEIGHT-74))

        # Minimap
        mini_scale = 8
        mx0, my0 = WIDTH-190, 24
        mm = pygame.Surface((MAP_W*mini_scale, MAP_H*mini_scale), pygame.SRCALPHA)
        pygame.draw.rect(mm, (0,0,0,120), mm.get_rect(), border_radius=8)
        for y,row in enumerate(WORLD_MAP):
            for x,ch in enumerate(row):
                if ch == "#":
                    pygame.draw.rect(mm, (95,105,145,190), (x*mini_scale,y*mini_scale,mini_scale,mini_scale))
        pygame.draw.circle(mm, CYAN, (int(p.x/TILE*mini_scale), int(p.y/TILE*mini_scale)), 4)
        for e in self.enemies:
            pygame.draw.circle(mm, RED, (int(e.x/TILE*mini_scale), int(e.y/TILE*mini_scale)), 3)
        pygame.draw.line(mm, CYAN, (int(p.x/TILE*mini_scale), int(p.y/TILE*mini_scale)), (int((p.x/TILE+math.cos(p.angle))*mini_scale), int((p.y/TILE+math.sin(p.angle))*mini_scale)), 2)
        surf.blit(mm, (mx0,my0))

        if self.message_timer > 0:
            alpha = int(255 * clamp(self.message_timer / 0.55, 0, 1)) if self.message_timer < 0.55 else 255
            txt = FONT_MED.render(self.message, True, WHITE)
            txt.set_alpha(alpha)
            surf.blit(txt, txt.get_rect(center=(HALF_W, 96)))

        if p.damage_flash > 0:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 30, 45, int(90 * p.damage_flash)))
            surf.blit(overlay, (0,0))

    def draw_menu(self, surf):
        surf.fill((7, 9, 18))
        for i in range(90):
            x = (i*97 + pygame.time.get_ticks()*0.025) % WIDTH
            y = (i*43) % HEIGHT
            pygame.draw.circle(surf, (25,35,65), (int(x), int(y)), 2)
        title = FONT_BIG.render("BLOCK ARENA SHOOTER", True, CYAN)
        surf.blit(title, title.get_rect(center=(HALF_W, 150)))
        sub = FONT_MED.render("Lokaler Krunker-Style FPS", True, WHITE)
        surf.blit(sub, sub.get_rect(center=(HALF_W, 210)))
        lines = [
            "ENTER  - Spiel starten",
            "WASD   - bewegen",
            "Maus   - umsehen / zielen",
            "Linksklick - schießen",
            "R      - nachladen",
            "1/2/3  - Waffe wechseln",
            "SHIFT  - sprinten",
            "ESC    - Pause",
        ]
        for i,l in enumerate(lines):
            txt = FONT.render(l, True, WHITE if i == 0 else (190,200,220))
            surf.blit(txt, txt.get_rect(center=(HALF_W, 305+i*35)))
        pygame.draw.rect(surf, CYAN, (HALF_W-220, 600, 440, 48), 2, border_radius=12)
        surf.blit(FONT.render("Drücke ENTER", True, CYAN), (HALF_W-92, 612))

    def draw_pause(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,150))
        surf.blit(overlay, (0,0))
        txt = FONT_BIG.render("PAUSE", True, WHITE)
        surf.blit(txt, txt.get_rect(center=(HALF_W, HALF_H-30)))
        txt2 = FONT.render("ESC drücken zum Weiterspielen", True, CYAN)
        surf.blit(txt2, txt2.get_rect(center=(HALF_W, HALF_H+45)))

    def draw_dead(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,185))
        surf.blit(overlay, (0,0))
        txt = FONT_BIG.render("GAME OVER", True, RED)
        surf.blit(txt, txt.get_rect(center=(HALF_W, 230)))
        stats = FONT_MED.render(f"Score {self.player.score}  |  Kills {self.player.kills}  |  Wave {self.level}", True, WHITE)
        surf.blit(stats, stats.get_rect(center=(HALF_W, 320)))
        again = FONT.render("ENTER zum Neustart", True, CYAN)
        surf.blit(again, again.get_rect(center=(HALF_W, 390)))

    def render(self):
        if self.state == "menu":
            self.draw_menu(WIN)
            pygame.display.flip()
            return

        shake = self.player.shake
        shake_x = int(random.uniform(-8,8) * shake)
        shake_y = int(random.uniform(-6,6) * shake)
        scene = pygame.Surface((WIDTH, HEIGHT))
        self.draw_background(scene, shake_x, shake_y)

        walls = self.cast_rays()
        for depth, x, y, w, h, col in walls:
            pygame.draw.rect(scene, col, (x+shake_x, y+shake_y, w, h))
            # dezente vertikale Kanten
            if random.random() < 0.012:
                pygame.draw.line(scene, (120,140,190), (x+shake_x, y+shake_y), (x+shake_x, y+h+shake_y), 1)

        self.render_sprites(scene)
        self.render_particles_3d(scene)
        self.draw_weapon(scene)
        self.draw_hud(scene)
        WIN.blit(scene, (0,0))
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
