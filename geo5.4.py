import pygame
import sys
import random
import os

# ---------- CONFIG ----------
WIDTH, HEIGHT = 900, 400
FPS = 80
GRAVITY = 0.5
JUMP_VELOCITY = -10  # Aumentado para saltar más alto
GROUND_HEIGHT = 80
SCROLL_SPEED_BASE = 8  # Velocidad base más moderada
OBSTACLE_FREQ = 2000  # ms entre obstáculos
FONT_NAME = None
HIGHSCORE_FILE = "gd_highscore.txt"
LEVEL_DISTANCE = 10000  # Distancia para completar cada nivel
SCORE_SPEED = 4  # velocidad fija del puntaje (puedes ajustarla)


# ---------- INICIALIZAR PYGAME ----------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Geometry Dash - Multi Nivel")
clock = pygame.time.Clock()
font = pygame.font.Font(FONT_NAME, 24)


 
# ---------- FUNCIONES UTILES ----------
def load_highscore():
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, "r") as f:
                return int(f.read().strip() or 0)
        except Exception:
            return 0
    return 0

def save_highscore(value):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(value))
    except Exception:
        pass

def draw_text(surf, text, size, x, y, center=False, color=(255,255,255)):
    f = pygame.font.Font(FONT_NAME, size)
    r = f.render(text, True, color)
    rect = r.get_rect()
    if center:
        rect.center = (x,y)
    else:
        rect.topleft = (x,y)
    surf.blit(r, rect)

# ---------- CLASES ----------
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.size = 36
        self.normal_color = (255,215,0)
        self.collision_color = (255,50,50)
        self.current_color = self.normal_color
        
        # Imagen base
        self.base_image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.rect(self.base_image, self.current_color, (0,0,self.size,self.size), border_radius=6)
        pygame.draw.polygon(self.base_image, (255,100,100),
                            [(int(self.size*0.7), int(self.size*0.25)),
                             (int(self.size*0.9), int(self.size*0.5)),
                             (int(self.size*0.7), int(self.size*0.75))])

        self.image = self.base_image.copy()
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

        self.vel_y = 0
        self.on_ground = False
        self.alive = True
        self.collision_timer = 0

        # Rotación
        self.angle = 90
        self.rotation_speed = 3   # giro más fluido

    def update_image(self):
        """Actualiza el color del cubo."""
        self.base_image.fill((0,0,0,0))
        pygame.draw.rect(self.base_image, self.current_color, (0,0,self.size,self.size), border_radius=6)
        pygame.draw.polygon(self.base_image, (255,100,100),
                            [(int(self.size*0.7), int(self.size*0.25)),
                             (int(self.size*0.9), int(self.size*0.5)),
                             (int(self.size*0.7), int(self.size*0.75))])

    def update(self):
        # -------- FÍSICA --------
        self.vel_y += GRAVITY
        self.rect.y += int(self.vel_y)

        ground_y = HEIGHT - GROUND_HEIGHT

        # Suelo estable reforzado
        if self.rect.bottom >= ground_y:
            self.rect.bottom = ground_y
            self.vel_y = 0
            self.on_ground = True
        else:
            self.on_ground = False

        # -------- ROTACIÓN --------
        old_center = self.rect.center

        if not self.on_ground:
            self.angle = (self.angle + self.rotation_speed) % 360
        else:
            self.angle = 0  # alineado en el suelo

        rotated = pygame.transform.rotate(self.base_image, self.angle)
        self.image = rotated
        self.rect = self.image.get_rect(center=old_center)

        # -------- COLOR DAÑO --------
        if self.collision_timer > 0:
            self.collision_timer -= 1
            if self.collision_timer == 0:
                self.current_color = self.normal_color
                self.update_image()

    def jump(self):
        if self.on_ground and self.alive:
            self.vel_y = JUMP_VELOCITY

    def set_collision(self):
        self.current_color = self.collision_color
        self.update_image()
        self.collision_timer = 25

    def draw(self, surface):
        surface.blit(self.image, self.rect.topleft)

class Obstacle(pygame.sprite.Sprite):
    def __init__(self, x, kind="spike", height=60, width=35):
        super().__init__()
        self.kind = kind
        self.width = width
        self.height = height
        self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        if kind == "spike":
            pygame.draw.polygon(self.image, (200,40,40),
                                [(0,self.height),(self.width/2,0),(self.width,self.height)])
        else:
            pygame.draw.rect(self.image, (100,180,255), (0,0,self.width,self.height))
        self.rect = self.image.get_rect()
        self.rect.bottomleft = (x, HEIGHT - GROUND_HEIGHT)
    
    def update(self, scroll_speed):
        self.rect.x -= scroll_speed

    def draw(self, surface):
        surface.blit(self.image, self.rect.topleft)

# ---------- FUNCIONES DE JUEGO ----------
def reset_game(level):
    global player, obstacles, distance, scroll_speed, last_obstacle_time, game_active, bg_elements
    
    # Limpiar obstáculos
    for o in obstacles:
        o.kill()
    obstacles.empty()
    
    # Reiniciar jugador
    player.rect.topleft = (120, HEIGHT - GROUND_HEIGHT - player.size)
    player.vel_y = 0
    player.alive = True
    player.current_color = player.normal_color
    player.update_image()
    player.collision_timer = 0
    
    # Velocidad según nivel
    scroll_speed = SCROLL_SPEED_BASE + (level - 1) * 1.5
    distance = 0
    last_obstacle_time = pygame.time.get_ticks()
    game_active = True
    
    # Regenerar fondo parallax más sutil
    bg_elements = []
    for i in range(8):
        x = i * 250
        h = random.randint(30, 80)
        bg_elements.append([x, HEIGHT - GROUND_HEIGHT - h, h, random.randint(25,60)])

def next_level():
    global current_level, show_level_transition, transition_timer
    current_level += 1
    show_level_transition = True
    transition_timer = 120  # 2 segundos a 60 FPS
    reset_game(current_level)

# ---------- INICIALIZACIÓN ----------
player = Player(120, HEIGHT - GROUND_HEIGHT - 36)
obstacles = pygame.sprite.Group()
current_level = 1
distance = 0
highscore = load_highscore()
last_obstacle_time = pygame.time.get_ticks()
scroll_speed = SCROLL_SPEED_BASE
game_active = True
show_level_transition = True
transition_timer = 90
auto_restart_timer = 0
bg_color = (30, 30, 40)
bg_elements = []

# Inicializar primer nivel
reset_game(current_level)

# ---------- BUCLE PRINCIPAL ----------
running = True
while running:
    dt = clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_UP:
                if game_active:
                    player.jump()
            if event.key == pygame.K_ESCAPE:
                running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if game_active:
                player.jump()
        

    # ---------- TRANSICIÓN DE NIVEL ----------
    if show_level_transition:
        transition_timer -= 1
        if transition_timer <= 0:
            show_level_transition = False

    # ---------- LÓGICA ----------
    if game_active and not show_level_transition:
        # Actualizar jugador
        player.update()
        
        # Actualizar obstáculos
        for ob in list(obstacles):
            ob.update(scroll_speed)
            if ob.rect.right < -50:
                ob.kill()

        # Colisiones
        if pygame.sprite.spritecollideany(player, obstacles):
            player.alive = False
            player.set_collision()
            game_active = False
            auto_restart_timer = 90  # 1.5 segundos
            if int(distance) > highscore:
                highscore = int(distance)
                save_highscore(highscore)

        # Generar obstáculos
        now = pygame.time.get_ticks()
        if now - last_obstacle_time > OBSTACLE_FREQ:
            last_obstacle_time = now
            kind = random.choice(["spike", "spike", "spike", "block"])
            if kind == "spike":
                h = random.randint(40, 50)  # Altura considerable pero saltable
                o = Obstacle(WIDTH + 20, kind="spike", height=h, width=random.randint(40,50))
                obstacles.add(o)
            else:
                h = random.randint(40, 60) # Altura más baja para bloques
                o = Obstacle(WIDTH + 20, kind="block", height=h, width=random.randint(40,60))
                obstacles.add(o)

        # Actualizar distancia
        distance += SCORE_SPEED * (dt / 16.6667)  # Velocidad fija del puntaje
        
        # Verificar si completó el nivel
        if distance >= LEVEL_DISTANCE:
            next_level()

    # Auto-reinicio después de colisión
    elif not game_active:
        player.update()  # Para actualizar el timer de color
        auto_restart_timer -= 1
        if auto_restart_timer <= 0:
            reset_game(current_level)

    # ---------- DIBUJO ----------
    screen.fill(bg_color)

    # Fondo parallax sutil
    for i, b in enumerate(bg_elements):
        bx, by, h, w = b
        bx -= scroll_speed * (0.15 + (i % 3)*0.05)  # Velocidad muy reducida
        if bx + w < -50:
            bx = WIDTH + random.randint(50, 300)
            h = random.randint(30, 80)
            by = HEIGHT - GROUND_HEIGHT - h
        b[0] = bx
        b[1] = by
        # Color muy sutil para que no distraiga
        color_val = 35 + i*2
        pygame.draw.rect(screen, (color_val, color_val+5, color_val+10), (bx, by, w, h))

    # Suelo
    pygame.draw.rect(screen, (30,30,30), (0, HEIGHT - GROUND_HEIGHT, WIDTH, GROUND_HEIGHT))
    for i in range(0, WIDTH, 40):
        pygame.draw.rect(screen, (45,45,45), (i, HEIGHT - GROUND_HEIGHT, 20, GROUND_HEIGHT))

    # Dibujar obstáculos y jugador
    for ob in obstacles:
        ob.draw(screen)
    player.draw(screen)

    # HUD
    draw_text(screen, f"Nivel: {current_level}", 24, 12, 8, color=(100,200,255))
    draw_text(screen, f"Progreso: {int(distance)}/{LEVEL_DISTANCE}", 20, 12, 38)
    draw_text(screen, f"Record: {highscore}", 18, 12, 64)
    
    # Barra de progreso
    progress_width = 200
    progress_x = WIDTH - progress_width - 20
    progress_y = 20
    progress_fill = min(1.0, distance / LEVEL_DISTANCE) * progress_width
    pygame.draw.rect(screen, (60,60,60), (progress_x, progress_y, progress_width, 15))
    pygame.draw.rect(screen, (100,255,100), (progress_x, progress_y, progress_fill, 15))
    pygame.draw.rect(screen, (150,150,150), (progress_x, progress_y, progress_width, 15), 2)

    # Transición de nivel
    if show_level_transition:
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(150)
        overlay.fill((0,0,0))
        screen.blit(overlay, (0,0))
        draw_text(screen, f"NIVEL {current_level}", 64, WIDTH//2, HEIGHT//2 - 30, center=True, color=(100,255,100))
        draw_text(screen, "¡Preparate!", 36, WIDTH//2, HEIGHT//2 + 30, center=True, color=(255,255,100))

    # ---------- ACTUALIZAR PANTALLA ----------
    pygame.display.flip()

# Salir
pygame.quit()
sys.exit()