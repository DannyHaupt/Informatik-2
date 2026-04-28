import pygame
import random
import math
import sys

pygame.init()

WIDTH, HEIGHT = 1100, 800
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dark Vector Invaders – Neon Deluxe")

FPS = 60
clock = pygame.time.Clock()

BLACK = (5, 5, 18)
WHITE = (235, 235, 245)
RED = (255, 55, 80)
CYAN = (0, 220, 255)
PURPLE = (190, 70, 255)
GREEN = (0, 255, 140)
ORANGE = (255, 170, 45)
YELLOW = (255, 245, 120)
GREY = (120, 120, 160)
BLUE = (60, 120, 255)

FONT = pygame.font.SysFont("consolas", 25)
FONT_SMALL = pygame.font.SysFont("consolas", 18)
FONT_BIG = pygame.font.SysFont("consolas", 64)


def glow_circle(win, color, pos, radius):
    for i in range(4, 0, -1):
        pygame.draw.circle(win, color, pos, radius + i * 6, width=1)
    pygame.draw.circle(win, color, pos, radius)


def glow_rect(win, color, rect, width=2):
    for i in range(4, 0, -1):
        r = pygame.Rect(rect)
        r.inflate_ip(i * 8, i * 8)
        pygame.draw.rect(win, color, r, width=1, border_radius=8)
    pygame.draw.rect(win, color, rect, width=width, border_radius=8)


class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.speed = random.uniform(0.5, 3)
        self.size = random.choice([1, 1, 1, 2])

    def update(self):
        self.y += self.speed
        if self.y > HEIGHT:
            self.y = 0
            self.x = random.randint(0, WIDTH)

    def draw(self, win):
        brightness = int(80 + self.speed * 50)
        pygame.draw.circle(win, (brightness, brightness, brightness + 20), (int(self.x), int(self.y)), self.size)


stars = [Star() for _ in range(220)]


class Particle:
    def __init__(self, x, y, color, size=3):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.tau)
        speed = random.uniform(1, 6)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(20, 45)
        self.color = color
        self.size = size

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.05
        self.life -= 1

    def draw(self, win):
        if self.life > 0:
            pygame.draw.circle(win, self.color, (int(self.x), int(self.y)), max(1, self.size))


class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT - 120
        self.w = 64
        self.h = 55
        self.speed = 7
        self.cooldown = 300
        self.last_shot = 0
        self.lives = 3
        self.score = 0

        self.spread = False
        self.spread_end = 0

        self.shield_active = False
        self.shield_hits = 0
        self.shield_end = 0

    def draw(self, win):
        # Flamme
        flame = random.randint(12, 25)
        pygame.draw.polygon(win, ORANGE, [
            (self.x - 12, self.y + 25),
            (self.x + 12, self.y + 25),
            (self.x, self.y + 25 + flame)
        ])

        # Schiff Glow
        points = [
            (self.x, self.y - self.h // 2),
            (self.x - self.w // 2, self.y + self.h // 2),
            (self.x, self.y + 12),
            (self.x + self.w // 2, self.y + self.h // 2)
        ]

        for i in range(4, 0, -1):
            pygame.draw.polygon(win, CYAN, points, width=i)
        pygame.draw.polygon(win, WHITE, points, width=2)

        # Cockpit
        glow_circle(win, BLUE, (self.x, self.y), 7)

        # Schild
        if self.shield_active:
            radius = 72 + int(math.sin(pygame.time.get_ticks() * 0.01) * 4)
            pygame.draw.circle(win, CYAN, (self.x, self.y), radius, width=3)
            pygame.draw.circle(win, BLUE, (self.x, self.y), radius + 8, width=1)

    def move(self, dx):
        self.x += dx * self.speed
        self.x = max(self.w // 2, min(WIDTH - self.w // 2, self.x))

    def can_shoot(self):
        return pygame.time.get_ticks() - self.last_shot >= self.cooldown

    def shoot(self):
        self.last_shot = pygame.time.get_ticks()
        if self.spread:
            return [
                Bullet(self.x, self.y - 42, -13, 0, ORANGE),
                Bullet(self.x, self.y - 42, -12, -0.28, YELLOW),
                Bullet(self.x, self.y - 42, -12, 0.28, YELLOW)
            ]
        return [Bullet(self.x, self.y - 42, -13, 0, ORANGE)]

    def activate_shield(self):
        self.shield_active = True
        self.shield_hits = 6
        self.shield_end = pygame.time.get_ticks() + 16000

    def activate_spread(self):
        self.spread = True
        self.spread_end = pygame.time.get_ticks() + 14000

    def activate_fast(self):
        self.cooldown = max(110, self.cooldown - 70)

    def update_powerups(self):
        now = pygame.time.get_ticks()

        if self.shield_active and now > self.shield_end:
            self.shield_active = False

        if self.spread and now > self.spread_end:
            self.spread = False


class Enemy:
    def __init__(self, x, y, level):
        self.x = x
        self.y = y
        self.w = 48
        self.h = 34
        self.alive = True
        self.level = level
        self.pulse = random.random() * 100

    def draw(self, win):
        pulse = int(40 + math.sin(pygame.time.get_ticks() * 0.006 + self.pulse) * 30)
        color = (255, 50 + pulse, 80)

        rect = pygame.Rect(self.x, self.y, self.w, self.h)
        glow_rect(win, color, rect, 2)

        pygame.draw.line(win, color, (self.x + 8, self.y), (self.x - 6, self.y - 12), 2)
        pygame.draw.line(win, color, (self.x + self.w - 8, self.y), (self.x + self.w + 6, self.y - 12), 2)

        glow_circle(win, RED, (int(self.x + 14), int(self.y + 13)), 4)
        glow_circle(win, RED, (int(self.x + self.w - 14), int(self.y + 13)), 4)

    def update(self, t, speed, direction):
        self.x += direction * speed
        self.y += math.sin(t * 0.002 + self.x * 0.02) * 0.45
        self.y = max(40, self.y)


class Bullet:
    def __init__(self, x, y, vy, vx_factor, color):
        self.x = x
        self.y = y
        self.vy = vy
        self.vx_factor = vx_factor
        self.r = 5
        self.color = color

    def update(self):
        self.y += self.vy
        self.x += self.vx_factor * 10

    def draw(self, win):
        glow_circle(win, self.color, (int(self.x), int(self.y)), self.r)

    def off(self):
        return self.y < -60 or self.y > HEIGHT + 60


class PowerUp:
    def __init__(self, x, y, ptype):
        self.x = x
        self.y = y
        self.type = ptype
        self.size = 36
        self.speed = 3.2
        self.angle = 0

    def update(self):
        self.y += self.speed
        self.angle += 0.08

    def draw(self, win):
        color = {
            "shield": CYAN,
            "spread": PURPLE,
            "fast": GREEN,
            "life": RED
        }[self.type]

        cx = int(self.x + self.size // 2)
        cy = int(self.y + self.size // 2)

        radius = self.size // 2 + int(math.sin(self.angle) * 3)
        pygame.draw.circle(win, color, (cx, cy), radius, width=3)
        pygame.draw.circle(win, color, (cx, cy), radius + 8, width=1)

        if self.type == "shield":
            symbol = "S"
        elif self.type == "spread":
            symbol = "W"
        elif self.type == "fast":
            symbol = "F"
        else:
            symbol = "+"

        text = FONT.render(symbol, True, WHITE)
        WIN.blit(text, (cx - text.get_width() // 2, cy - text.get_height() // 2))

        label = FONT_SMALL.render(self.type.upper(), True, color)
        WIN.blit(label, (cx - label.get_width() // 2, cy + 24))

    def off(self):
        return self.y > HEIGHT + 60


def collide_rect_circle(rx, ry, rw, rh, cx, cy, cr):
    closest_x = max(rx, min(cx, rx + rw))
    closest_y = max(ry, min(cy, ry + rh))
    dx = cx - closest_x
    dy = cy - closest_y
    return dx * dx + dy * dy <= cr * cr


def spawn_enemies(level):
    enemies = []
    rows = min(6, 3 + level // 2)
    cols = 8
    gap = 42
    start_x = 80
    start_y = 80

    for r in range(rows):
        for c in range(cols):
            x = start_x + c * (48 + gap)
            y = start_y + r * (34 + gap)
            enemies.append(Enemy(x, y, level))

    return enemies


def maybe_powerup(x, y):
    # Höhere Chance: 65 %
    if random.random() < 0.65:
        return PowerUp(
            x,
            y,
            random.choice(["shield", "spread", "fast", "life"])
        )
    return None


def draw_background(win):
    win.fill(BLACK)

    for s in stars:
        s.update()
        s.draw(win)

    # leichter Neon-Horizont
    for y in range(HEIGHT - 160, HEIGHT, 35):
        pygame.draw.line(win, (20, 40, 80), (0, y), (WIDTH, y), 1)

    for x in range(0, WIDTH, 70):
        pygame.draw.line(win, (15, 35, 70), (x, HEIGHT), (WIDTH // 2, HEIGHT - 170), 1)


def draw_hud(player, level):
    hud = FONT.render(
        f"SCORE {player.score}    LIVES {player.lives}    LEVEL {level}",
        True,
        WHITE
    )
    WIN.blit(hud, (20, 20))

    x = WIDTH - 260
    y = 20

    active = []

    if player.shield_active:
        rest = max(0, (player.shield_end - pygame.time.get_ticks()) // 1000)
        active.append(("SHIELD", rest, CYAN))

    if player.spread:
        rest = max(0, (player.spread_end - pygame.time.get_ticks()) // 1000)
        active.append(("SPREAD", rest, PURPLE))

    active.append(("FIRE RATE", int(300 - player.cooldown), GREEN))

    for name, value, color in active:
        txt = FONT_SMALL.render(f"{name}: {value}", True, color)
        WIN.blit(txt, (x, y))
        y += 25


def menu():
    while True:
        draw_background(WIN)

        title = FONT_BIG.render("DARK VECTOR INVADERS", True, CYAN)
        subtitle = FONT.render("NEON DELUXE EDITION", True, PURPLE)
        start = FONT.render("Drücke [SPACE] zum Starten", True, WHITE)
        quit_txt = FONT.render("Drücke [ESC] zum Beenden", True, GREY)

        WIN.blit(title, (WIDTH // 2 - title.get_width() // 2, 230))
        WIN.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 305))
        WIN.blit(start, (WIDTH // 2 - start.get_width() // 2, 420))
        WIN.blit(quit_txt, (WIDTH // 2 - quit_txt.get_width() // 2, 465))

        pygame.display.flip()
        clock.tick(FPS)

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


def game_over_screen(score):
    while True:
        draw_background(WIN)

        over = FONT_BIG.render("GAME OVER", True, RED)
        score_txt = FONT.render(f"Final Score: {score}", True, WHITE)
        restart = FONT.render("[SPACE] Neustart    [ESC] Ende", True, CYAN)

        WIN.blit(over, (WIDTH // 2 - over.get_width() // 2, 280))
        WIN.blit(score_txt, (WIDTH // 2 - score_txt.get_width() // 2, 370))
        WIN.blit(restart, (WIDTH // 2 - restart.get_width() // 2, 450))

        pygame.display.flip()
        clock.tick(FPS)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    return True
                if e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()


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
    enemy_shot_rate = 1250

    while True:
        clock.tick(FPS)
        t = pygame.time.get_ticks()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()

        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        player.move(dx)

        if keys[pygame.K_SPACE] and player.can_shoot():
            bullets.extend(player.shoot())

        player.update_powerups()

        # Gegnerbewegung
        if enemies:
            min_x = min(e.x for e in enemies)
            max_x = max(e.x + e.w for e in enemies)

            if max_x > WIDTH - 40:
                direction = -1
                for e in enemies:
                    e.y += 12

            if min_x < 40:
                direction = 1
                for e in enemies:
                    e.y += 12

            for en in enemies:
                en.update(t, speed, direction)

        # Gegner schießen
        if enemies and t - last_enemy_shot > enemy_shot_rate:
            shooter = random.choice(enemies)
            enemy_bullets.append(
                Bullet(shooter.x + shooter.w // 2, shooter.y + shooter.h, 6, 0, RED)
            )
            last_enemy_shot = t

        # Update
        for b in bullets:
            b.update()
        bullets = [b for b in bullets if not b.off()]

        for b in enemy_bullets:
            b.update()
        enemy_bullets = [b for b in enemy_bullets if not b.off()]

        for p in powerups:
            p.update()
        powerups = [p for p in powerups if not p.off()]

        for pa in particles:
            pa.update()
        particles = [pa for pa in particles if pa.life > 0]

        # Spieler trifft Gegner
        for b in bullets[:]:
            for en in enemies:
                if en.alive and collide_rect_circle(en.x, en.y, en.w, en.h, b.x, b.y, b.r):
                    en.alive = False

                    if b in bullets:
                        bullets.remove(b)

                    player.score += 10 * level

                    for _ in range(32):
                        particles.append(
                            Particle(en.x + en.w // 2, en.y + en.h // 2, random.choice([RED, ORANGE, YELLOW]), 3)
                        )

                    pu = maybe_powerup(en.x + en.w // 2, en.y + en.h // 2)
                    if pu:
                        powerups.append(pu)

                    break

        enemies = [e for e in enemies if e.alive]

        # Gegner trifft Spieler
        for b in enemy_bullets[:]:
            if collide_rect_circle(
                player.x - player.w // 2,
                player.y - player.h // 2,
                player.w,
                player.h,
                b.x,
                b.y,
                b.r
            ):
                enemy_bullets.remove(b)

                if player.shield_active:
                    player.shield_hits -= 1

                    for _ in range(15):
                        particles.append(Particle(player.x, player.y, CYAN, 2))

                    if player.shield_hits <= 0:
                        player.shield_active = False
                else:
                    player.lives -= 1

                    for _ in range(35):
                        particles.append(Particle(player.x, player.y, RED, 3))

                    if player.lives <= 0:
                        return player.score

        # PowerUp einsammeln
        for p in powerups[:]:
            if (
                player.x - player.w // 2 < p.x + p.size and
                player.x + player.w // 2 > p.x and
                player.y - player.h // 2 < p.y + p.size and
                player.y + player.h // 2 > p.y
            ):
                if p.type == "shield":
                    player.activate_shield()

                elif p.type == "spread":
                    player.activate_spread()

                elif p.type == "fast":
                    player.activate_fast()

                elif p.type == "life":
                    player.lives = min(5, player.lives + 1)

                for _ in range(25):
                    particles.append(Particle(p.x, p.y, GREEN, 2))

                powerups.remove(p)

        # Gegner unten angekommen
        for en in enemies:
            if en.y + en.h > player.y - 30:
                return player.score

        # Neues Level
        if not enemies:
            level += 1
            enemies = spawn_enemies(level)
            speed += 0.25
            enemy_shot_rate = max(420, enemy_shot_rate - 80)

        # Zeichnen
        draw_background(WIN)

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
        draw_hud(player, level)

        pygame.display.flip()


if __name__ == "__main__":
    while True:
        menu()
        final_score = game()
        if not game_over_screen(final_score):
            break