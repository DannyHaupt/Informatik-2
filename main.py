import pygame
import sys

# Pygame starten
pygame.init()

# Fenster
BREITE = 800
HOEHE = 600
fenster = pygame.display.set_mode((BREITE, HOEHE))
pygame.display.set_caption("Space Invader Anfang")

# Farben
WEISS = (255, 255, 255)
BLAU = (0, 100, 255)
ROT = (255, 0, 0)

# Spieler (Quadrat)
quadrat_breite = 100
quadrat_x = 350
quadrat_y = HOEHE - quadrat_breite - 10
geschwindigkeit = 5

# Schüsse
schuesse = []
letzter_schuss = 0
schuss_intervall = 300  # Millisekunden

# Uhr
clock = pygame.time.Clock()

# Hauptschleife
while True:
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

    # Im Fenster halten
    if quadrat_x < 0:
        quadrat_x = 0
    if quadrat_x > BREITE - quadrat_breite:
        quadrat_x = BREITE - quadrat_breite

    # 🔫 Automatisch schießen
    jetzt = pygame.time.get_ticks()
    if jetzt - letzter_schuss > schuss_intervall:
        schuesse.append([quadrat_x + quadrat_breite // 2, quadrat_y])
        letzter_schuss = jetzt

    # Schüsse bewegen
    for schuss in schuesse:
        schuss[1] -= 10

    # Alte Schüsse entfernen
    schuesse = [s for s in schuesse if s[1] > 0]

    # Zeichnen
    fenster.fill(WEISS)

    # Spieler
    pygame.draw.rect(fenster, BLAU, (quadrat_x, quadrat_y, quadrat_breite, quadrat_breite))

    # Schüsse
    for schuss in schuesse:
        pygame.draw.rect(fenster, ROT, (schuss[0], schuss[1], 5, 10))

    pygame.display.flip()

    clock.tick(60)