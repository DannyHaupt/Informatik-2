import pygame
import sys
import random

pygame.init()

# Fenster
BREITE = 800
HOEHE = 600
fenster = pygame.display.set_mode((BREITE, HOEHE))
pygame.display.set_caption("Space Invader")

# Farben
WEISS = (255, 255, 255)
BLAU = (0, 100, 255)
ROT = (255, 0, 0)
GRUEN = (0, 200, 0)

# Spieler
quadrat_breite = 60
quadrat_x = BREITE // 2 - quadrat_breite // 2
quadrat_y = HOEHE - quadrat_breite - 10
geschwindigkeit = 5

# Schüsse
schuesse = []
letzter_schuss = 0
schuss_intervall = 300
schuss_breite = 8
schuss_länge = 30
schuss_geschwindigkeit = 10

# Gegner
gegner = []
letzter_gegner = 0
gegner_intervall = 80
gegner_groesse = 40
gegner_geschwindigkeit = 3

clock = pygame.time.Clock()

while True:
    # Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    # Tastatur
    tasten = pygame.key.get_pressed()

    if tasten[pygame.K_LEFT]:
        quadrat_x -= geschwindigkeit
    if tasten[pygame.K_RIGHT]:
        quadrat_x += geschwindigkeit

    # Begrenzung
    if quadrat_x < 0:
        quadrat_x = 0
    if quadrat_x > BREITE - quadrat_breite:
        quadrat_x = BREITE - quadrat_breite

    # 🔫 Schießen
    jetzt = pygame.time.get_ticks()
    if jetzt - letzter_schuss > schuss_intervall:
        schuesse.append([quadrat_x + quadrat_breite // 2, quadrat_y])
        letzter_schuss = jetzt

    # Schüsse bewegen
    for schuss in schuesse:
        schuss[1] -= schuss_geschwindigkeit

    # Schüsse löschen
    schuesse = [s for s in schuesse if s[1] > 0]

    # 👾 Gegner spawnen
    if jetzt - letzter_gegner > gegner_intervall:
        x = random.randint(0, BREITE - gegner_groesse)
        gegner.append([x, 0])
        letzter_gegner = jetzt

    # Gegner bewegen
    for g in gegner:
        g[1] += gegner_geschwindigkeit

    # Gegner löschen
    gegner = [g for g in gegner if g[1] < HOEHE]

    # Zeichnen
    fenster.fill(WEISS)

    # Spieler
    pygame.draw.rect(fenster, BLAU, (quadrat_x, quadrat_y, quadrat_breite, quadrat_breite))

    # Schüsse
    for schuss in schuesse:
        pygame.draw.rect(fenster, ROT, (schuss[0], schuss[1], schuss_breite, schuss_länge))

    # Gegner
    for g in gegner:
        pygame.draw.rect(fenster, GRUEN, (g[0], g[1], gegner_groesse, gegner_groesse))

    pygame.display.flip()
    clock.tick(60)