import pygame
import sys

# Pygame starten
pygame.init()

# Fenster
BREITE = 800
HOEHE = 600
fenster = pygame.display.set_mode((BREITE, HOEHE))
pygame.display.set_caption("Quadrat bewegen")

# Farben
WEISS = (255, 255, 255)
BLAU = (0, 100, 255)

# Quadrat
quadrat_x = 350
quadrat_y = 250
quadrat_breite = 100
geschwindigkeit = 5

# Uhr für konstante Framerate
clock = pygame.time.Clock()

# Hauptschleife
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    # Tastaturzustand abfragen
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

    # Zeichnen
    fenster.fill(WEISS)
    pygame.draw.rect(fenster, BLAU, (quadrat_x, quadrat_y, quadrat_breite, quadrat_breite))
    pygame.display.flip()

    # 60 FPS
    clock.tick(60)