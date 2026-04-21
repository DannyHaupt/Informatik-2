import pygame
import random
import math
import sys

pygame.init()
WIDTH, HEIGHT = 1100, 800
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dark Vector Invaders – Deluxe Edition")

FPS = 60
clock = pygame.time.Clock()

# Farben
BLACK = (5, 5, 15)
WHITE = (230, 230, 230)
RED = (255, 60, 60)
CYAN = (0, 200, 255)
PURPLE = (180, 0, 255)
GREEN = (0, 255, 120)
ORANGE = (255, 150, 40)
YELLOW = (255, 255, 120)
GREY = (120, 120, 160)

FONT = pygame.font.SysFont("consolas", 28)
FONT_BIG = pygame.font.SysFont("consolas", 60)

# ---------------------------------------------------------
#   PARTIKEL
# ---------------------------------------------------------

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)
        self.life = random.randint(20, 40)
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, win):
        if self.life > 0:
            pygame.draw.circle(win, self.color, (int(self.x), int(self.y)), 2)


# ---------------------------------------------------------
#   SPIELER
# ---------------------------------------------------------

class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT - 120
        self.w = 60
        self.h = 50

        self.speed = 7
        self.cooldown = 300
        self.last_shot = 0

        self.lives = 3
        self.score = 0

        # PowerUps
        self.spread = False
        self.shield_active = False
        self.shield_hits = 0
        self.shield_end = 0

    def draw(self, win):
        # Schiff (Neon Dreieck)
        pygame.draw.polygon(win, CYAN, [
            (self.x, self.y - self.h//2),
            (self.x - self.w//2, self.y + self.h//2),
            (self.x + self.w//2, self.y + self.h//2)
        ], width=3)

        # Schild
        if self.shield_active:
            pygame.draw.circle(win, (0, 150, 255), (self.x, self.y), 70, width=3)

    def move(self, dx):
        self.x += dx * self.speed
        self.x = max(self.w//2, min(WIDTH - self.w//2, self.x))

    def can_shoot(self):
        return pygame.time.get_ticks() - self.last_shot >= self.cooldown

    def shoot(self):
        self.last_shot = pygame.time.get_ticks()
        shots = []

        if self.spread:
            shots.append(Bullet(self.x, self.y - 40, -12, 0))
            shots.append(Bullet(self.x, self.y - 40, -12, -0.25))
            shots.append(Bullet(self.x, self.y - 40, -12, 0.25))
        else:
            shots.append(Bullet(self.x, self.y - 40, -12, 0))

        return shots

    def activate_shield(self):
        self.shield_active = True
        self.shield_hits = 5
        self.shield_end = pygame.time.get_ticks() + 15000

    def update_shield(self):
        if self.shield_active and pygame.time.get_ticks() > self.shield_end:
            self.shield_active = False


# ---------------------------------------------------------
#   GEGNER
# ---------------------------------------------------------

class Enemy:
    def __init__(self, x, y, level):
        self.x = x
        self.y = y
        self.w = 45
        self.h = 30
        self.alive = True
        self.level = level

    def draw(self, win):
        # Körper
        pygame.draw.rect(win, (200, 40 + self.level*10, 40), (self.x, self.y, self.w, self.h), width=2)
        # Augen
        pygame.draw.circle(win, RED, (self.x + 10, self.y + 10), 4)
        pygame.draw.circle(win, RED, (self.x + self.w - 10, self.y + 10), 4)

    def update(self, t, speed, direction):
        self.x += direction * speed
        # Gegner dürfen nicht nach oben raus
        self.y = max(40, self.y + math.sin(t * 0.002 + self.x * 0.02) * 0.4)


# ---------------------------------------------------------
#   SCHÜSSE
# ---------------------------------------------------------

class Bullet:
    def __init__(self, x, y, vy, vx_factor):
        self.x = x
        self.y = y
        self.vy = vy
        self.vx_factor = vx_factor
        self.r = 5

    def update(self):
        self.y += self.vy
        self.x += self.vx_factor * 10

    def draw(self, win):
        pygame.draw.circle(win, ORANGE, (int(self.x), int(self.y)), self.r)

    def off(self):
        return self.y < -50 or self.y > HEIGHT + 50


# ---------------------------------------------------------
#   POWERUPS
# ---------------------------------------------------------

class PowerUp:
    def __init__(self, x, y, ptype):
        self.x = x
        self.y = y
        self.type = ptype
        self.size = 30
        self.speed = 3

    def update(self):
        self.y += self.speed

    def draw(self, win):
        color = {"shield": CYAN, "spread": PURPLE, "fast": GREEN}[self.type]
        pygame.draw.rect(win, color, (self.x, self.y, self.size, self.size), width=3)

    def off(self):
        return self.y > HEIGHT + 40


# ---------------------------------------------------------
#   HILFSFUNKTIONEN
# ---------------------------------------------------------

def collide_rect_circle(rx, ry, rw, rh, cx, cy, cr):
    closest_x = max(rx, min(cx, rx + rw))
    closest_y = max(ry, min(cy, ry + rh))
    dx = cx - closest_x
    dy = cy - closest_y
    return dx*dx + dy*dy <= cr*cr


def spawn_enemies(level):
    enemies = []
    rows = 3 + level // 2
    cols = 8
    gap = 40
    start_x = 80
    start_y = 80

    for r in range(rows):
        for c in range(cols):
            x = start_x + c * (45 + gap)
            y = start_y + r * (30 + gap)
            enemies.append(Enemy(x, y, level))

    return enemies


def maybe_powerup(x, y):
    # deutlich höhere Chance
    if random.random() < 0.45:
        return PowerUp(x, y, random.choice(["shield", "spread", "fast"]))
    return None


def draw_background(win, t):
    win.fill(BLACK)
    random.seed(1)
    for i in range(300):
        x = random.randint(0, WIDTH)
        y = (random.randint(0, HEIGHT) + int(t * 0.05)) % HEIGHT
        pygame.draw.circle(win, GREY, (x, y), 1)


# ---------------------------------------------------------
#   MENÜ
# ---------------------------------------------------------

def menu():
    while True:
        WIN.fill(BLACK)

        title = FONT_BIG.render("DARK VECTOR INVADERS", True, CYAN)
        start = FONT.render("Drücke [SPACE] um zu starten", True, WHITE)
        quit_txt = FONT.render("Drücke [ESC] um zu beenden", True, WHITE)

        WIN.blit(title, (WIDTH//2 - title.get_width()//2, 250))
        WIN.blit(start, (WIDTH//2 - start.get_width()//2, 400))
        WIN.blit(quit_txt, (WIDTH//2 - quit_txt.get_width()//2, 450))

        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    return
                if e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()


# ---------------------------------------------------------
#   GAME LOOP
# ---------------------------------------------------------

def game():
    player = Player()
    level = 1

    enemies = spawn_enemies(level)
    direction = 1
    speed = 1.2

    bullets = []
    enemy_bullets = []
    powerups = []
    particles = []

    last_enemy_shot = 0
    enemy_shot_rate = 1300

    while True:
        dt = clock.tick(FPS)
        t = pygame.time.get_ticks()

        # Input
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        player.move(dx)

        if keys[pygame.K_SPACE] and player.can_shoot():
            bullets.extend(player.shoot())

        player.update_shield()

        # Gegner bewegen
        if enemies:
            min_x = min(e.x for e in enemies)
            max_x = max(e.x + e.w for e in enemies)
            if max_x > WIDTH - 40:
                direction = -1
            if min_x < 40:
                direction = 1

            for en in enemies:
                en.update(t, speed, direction)

        # Gegner schießen
        if enemies and t - last_enemy_shot > enemy_shot_rate:
            shooter = random.choice(enemies)
            enemy_bullets.append(Bullet(shooter.x + shooter.w//2, shooter.y + shooter.h, 6, 0))
            last_enemy_shot = t

        # Bullets
        for b in bullets:
            b.update()
        bullets = [b for b in bullets if not b.off()]

        for b in enemy_bullets:
            b.update()
        enemy_bullets = [b for b in enemy_bullets if not b.off()]

        # PowerUps
        for p in powerups:
            p.update()
        powerups = [p for p in powerups if not p.off()]

        # Partikel
        for pa in particles:
            pa.update()
        particles = [pa for pa in particles if pa.life > 0]

        # Kollisionen: Spieler trifft Gegner
        for b in bullets[:]:
            for en in enemies:
                if en.alive and collide_rect_circle(en.x, en.y, en.w, en.h, b.x, b.y, b.r):
                    en.alive = False
                    bullets.remove(b)
                    player.score += 10 * level

                    # Explosion
                    for _ in range(20):
                        particles.append(Particle(en.x + en.w//2, en.y + en.h//2, (255, 80, 40)))

                    pu = maybe_powerup(en.x, en.y)
                    if pu:
                        powerups.append(pu)
                    break

        enemies = [e for e in enemies if e.alive]

        # Kollision: Gegner trifft Spieler
        for b in enemy_bullets[:]:
            if collide_rect_circle(player.x - player.w//2, player.y - player.h//2,
                                   player.w, player.h, b.x, b.y, b.r):
                enemy_bullets.remove(b)

                if player.shield_active:
                    player.shield_hits -= 1
                    if player.shield_hits <= 0:
                        player.shield_active = False
                else:
                    player.lives -= 1
                    if player.lives <= 0:
                        return

        # PowerUp einsammeln
        for p in powerups[:]:
            if (player.x - player.w//2 < p.x + p.size and
                player.x + player.w//2 > p.x and
                player.y - player.h//2 < p.y + p.size and
                player.y + player.h//2 > p.y):

                if p.type == "shield":
                    player.activate_shield()
                elif p.type == "spread":
                    player.spread = True
                elif p.type == "fast":
                    player.cooldown = max(120, player.cooldown - 80)

                powerups.remove(p)

        # Level geschafft
        if not enemies:
            level += 1
            enemies = spawn_enemies(level)
            speed += 0.25
            enemy_shot_rate = max(400, enemy_shot_rate - 80)

        # Zeichnen
        draw_background(WIN, t)

        for en in enemies:
            en.draw(WIN)
        for b in bullets:
            b.draw(WIN)
        for b in enemy_bullets:
            b.draw(WIN)
        for p in powerups:
            p.draw(WIN)
        for pa in particles:
            pa.draw(WIN)

        player.draw(WIN)

        hud = FONT.render(f"Score: {player.score}   Lives: {player.lives}   Level: {level}", True, WHITE)
        WIN.blit(hud, (20, 20))

        pygame.display.flip()


# ---------------------------------------------------------
#   START
# ---------------------------------------------------------

if __name__ == "__main__":
    menu()
    game()
