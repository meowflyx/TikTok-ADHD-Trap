import pygame
import random
import math
import os

# --- Randomization function ---
def randomize_settings():
    global NUM_RINGS, RING_THICKNESS, RING_COLOR, BALL_COLOR, PARTICLE_COLOR, RING_SPACING, BALL_SIZE
    global base_speed, min_speed, gap_angle, INITIAL_ANGLE
    NUM_RINGS = random.randint(3, 20)
    RING_THICKNESS = random.randint(2, 16)
    RING_COLOR = tuple(random.randint(80, 255) for _ in range(3))
    BALL_COLOR = tuple(random.randint(80, 255) for _ in range(3))
    def get_brighter_color(color, delta=30):
        return tuple(min(255, c + delta) for c in color)
    PARTICLE_COLOR = get_brighter_color(RING_COLOR)
    RING_SPACING = random.randint(10, 40)
    BALL_SIZE = random.randint(10, 18)  # Средний размер мяча
    base_speed = random.uniform(0.3, 1.2)
    min_speed = random.uniform(0.05, base_speed * 0.7)
    gap_angle = random.randint(20, 90)
    INITIAL_ANGLE = random.choice([0, 90, 180, 270])
    return

randomize_settings()

# --- Settings ---
WIDTH, HEIGHT = 800, 600
FPS = 60
GRAVITY = 0.05
# Цвета
def get_brighter_color(color, delta=30):
    return tuple(min(255, c + delta) for c in color)
PARTICLE_COLOR = get_brighter_color(RING_COLOR)
MAX_ROTATION_SPEED = 0.8
# Начальный угол для всех колец
SHRINK_FACTOR = 0.997  # Экспоненциальное сужение, очень плавно

# Константы физики
MAX_BALL_SPEED = 12.0        # Максимальная скорость шарика
MIN_BALL_SPEED = 4.0         # Минимальная скорость
BOUNCE_DAMPING = 1.0         # Нет затухания при отскоке
POSITION_CORRECTION = 1.1    # Коэффициент коррекции позиции
COLLISION_THRESHOLD = 0.1    # Порог для определения столкновения

# Субпиксельная отрисовка для быстро движущихся объектов
MOTION_BLUR_FRAMES = 2  # Уменьшаем количество кадров размытия

# --- Initialize ---
pygame.init()
pygame.mixer.init()  # Инициализация звука
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("TikTok ADHD Trap")
clock = pygame.time.Clock()

# Загрузка звуковых эффектов
try:
    # Путь к звуковому файлу - создаём его, если не существует
    sound_dir = os.path.join(os.path.dirname(__file__), 'sounds')
    if not os.path.exists(sound_dir):
        os.makedirs(sound_dir)
    break_sound_path = os.path.join(sound_dir, 'break.wav')
    
    # Проверяем существует ли файл звука, если нет - создаём простой звук
    if not os.path.exists(break_sound_path):
        print("Создание звукового файла...")
        # Генерация простого звука через pygame.mixer
        pygame.mixer.Sound(bytearray([128] * 44100)).write(break_sound_path)
    
    break_sound = pygame.mixer.Sound(break_sound_path)
except:
    print("Не удалось загрузить звуки. Игра продолжится без звука.")
    break_sound = None

particles = []

# --- Classes ---
class Ball:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.prev_x = x
        self.prev_y = y
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 0)
        self.radius = BALL_SIZE

    def update(self):
        self.prev_x = self.x
        self.prev_y = self.y
        # Гравитация
        self.vy += GRAVITY
        # Ограничение максимальной скорости
        speed = math.hypot(self.vx, self.vy)
        if speed > MAX_BALL_SPEED:
            scale = MAX_BALL_SPEED / speed
            self.vx *= scale
            self.vy *= scale
        self.x += self.vx
        self.y += self.vy

    def draw(self, surface):
        pygame.draw.circle(surface, BALL_COLOR, (int(self.x), int(self.y)), self.radius)

    def reflect(self, nx, ny, damping=1.0):
        v_dot_n = self.vx * nx + self.vy * ny
        self.vx = -nx * abs(v_dot_n) * damping
        self.vy = -ny * abs(v_dot_n) * damping
        # Добавляем небольшой случайный угол для разнообразия
        angle = math.atan2(self.vy, self.vx)
        angle += random.uniform(-0.18, 0.18)
        # Добавляем случайный множитель к скорости для большей прыгучести
        speed = max(abs(v_dot_n) * damping, MIN_BALL_SPEED)
        speed *= random.uniform(1.05, 1.15)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        # Ограничение максимальной скорости
        speed = math.hypot(self.vx, self.vy)
        if speed > MAX_BALL_SPEED:
            scale = MAX_BALL_SPEED / speed
            self.vx *= scale
            self.vy *= scale

    def correct_position(self, ring, inside):
        # Выталкиваем шарик ровно на границу кольца
        dx = self.x - ring.x
        dy = self.y - ring.y
        dist = math.hypot(dx, dy)
        if dist == 0:
            dx, dy = 1, 0
            dist = 1
        nx, ny = dx / dist, dy / dist
        if inside:
            target_dist = ring.radius - ring.thickness/2 - self.radius - 0.1
        else:
            target_dist = ring.radius + ring.thickness/2 + self.radius + 0.1
        self.x = ring.x + nx * target_dist
        self.y = ring.y + ny * target_dist

class Ring:
    def __init__(self, x, y, radius, gap_angle, rotation_speed, start_angle=INITIAL_ANGLE):
        self.x = x
        self.y = y
        self.radius = radius
        self.gap_angle = gap_angle
        self.angle = start_angle
        self.rotation_speed = rotation_speed
        self.thickness = RING_THICKNESS
        self.alive = True

    def update(self, shrink=False):
        if self.alive:
            self.angle = (self.angle + self.rotation_speed) % 360
            if shrink:
                self.radius *= SHRINK_FACTOR
                if self.radius < 20:
                    self.radius = 20

    def reverse_direction(self):
        self.rotation_speed *= -1

    def draw(self, surface):
        if not self.alive:
            return
        prev_point = None
        for deg in range(0, 361):
            angle_rad = math.radians(deg)
            x = self.x + self.radius * math.cos(angle_rad)
            y = self.y + self.radius * math.sin(angle_rad)
            dx = x - self.x
            dy = y - self.y
            angle = (math.degrees(math.atan2(-dy, dx)) + 360) % 360
            gap_start = self.angle % 360
            gap_end = (self.angle + self.gap_angle) % 360
            if gap_start < gap_end:
                in_gap = gap_start <= angle <= gap_end
            else:
                in_gap = angle >= gap_start or angle <= gap_end
            if in_gap:
                prev_point = None
                continue
            if prev_point is not None:
                pygame.draw.aaline(surface, RING_COLOR, prev_point, (x, y), self.thickness)
            prev_point = (x, y)

    def check_physics_collision(self, ball):
        if not self.alive:
            return None
        dx = ball.x - self.x
        dy = ball.y - self.y
        dist = math.hypot(dx, dy)
        r_in = self.radius - self.thickness/2 - ball.radius
        r_out = self.radius + self.thickness/2 + ball.radius
        # Проверяем попадание в кольцо
        if r_in < dist < r_out:
            # Проверяем дырку
            angle = (math.degrees(math.atan2(-dy, dx)) + 360) % 360
            gap_start = self.angle % 360
            gap_end = (self.angle + self.gap_angle) % 360
            if gap_start < gap_end:
                in_gap = gap_start <= angle <= gap_end
            else:
                in_gap = angle >= gap_start or angle <= gap_end
            if in_gap:
                self.alive = False
                spawn_ring_particles(self)
                if break_sound:
                    break_sound.play()
                return "destroyed"
            # Физическое столкновение
            # Определяем, с какой стороны пришёл шарик
            prev_dist = math.hypot(ball.prev_x - self.x, ball.prev_y - self.y)
            inside = prev_dist < self.radius
            return ("bounce", inside)
        return None

class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)
        self.life = random.randint(20, 40)
        self.size = random.randint(1, 2)  # Меньше размер

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            alpha = min(255, self.life * 8)
            color = (*PARTICLE_COLOR, alpha)
            particle_surf = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surf, color, (self.size, self.size), self.size)
            surface.blit(particle_surf, (int(self.x - self.size), int(self.y - self.size)))

# --- Particle System ---
def spawn_ring_particles(ring):
    # Партиклов гораздо больше, но они меньше
    num_particles = 200
    gap_start = math.radians(ring.angle)
    gap_end = math.radians((ring.angle + ring.gap_angle) % 360)
    for i in range(num_particles):
        angle = 2 * math.pi * i / num_particles
        in_gap = False
        if gap_start < gap_end:
            in_gap = gap_start <= angle <= gap_end
        else:
            in_gap = angle >= gap_start or angle <= gap_end
        if in_gap:
            continue
        x = ring.x + ring.radius * math.cos(angle)
        y = ring.y + ring.radius * math.sin(angle)
        particles.append(Particle(x, y))

def spawn_particles(x, y):
    for _ in range(40):
        particles.append(Particle(x, y))

# --- Setup ---
while True:
    randomize_settings()
    rings = []
    for i in range(NUM_RINGS):
        r = 100 + i * RING_SPACING
        if NUM_RINGS > 1:
            speed = base_speed + (min_speed - base_speed) * (i / (NUM_RINGS - 1))
        else:
            speed = base_speed
        direction = 1 if i % 2 == 0 else -1
        rings.append(Ring(WIDTH//2, HEIGHT//2, r, gap_angle=gap_angle, 
                         rotation_speed=direction * speed,
                         start_angle=INITIAL_ANGLE))
    ball = Ball(WIDTH//2, HEIGHT//2)
    particles.clear()
    running = True
    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

        # Update
        ball.update()
        # Определяем ближайшее к центру кольцо (которое alive)
        alive_rings = [ring for ring in rings if ring.alive]
        if alive_rings:
            closest_ring = min(alive_rings, key=lambda r: abs(r.radius - math.hypot(ball.x - r.x, ball.y - r.y)))
        else:
            closest_ring = None
        # Проверяем, находится ли шарик в зоне коллизии ближайшего кольца
        shrink_allowed = True
        if closest_ring:
            dx = ball.x - closest_ring.x
            dy = ball.y - closest_ring.y
            dist = math.hypot(dx, dy)
            min_r = closest_ring.radius - closest_ring.thickness/2 - ball.radius
            max_r = closest_ring.radius + closest_ring.thickness/2 + ball.radius
            if min_r <= dist <= max_r:
                shrink_allowed = False
        for ring in rings:
            ring.update(shrink=(ring is closest_ring and shrink_allowed))
        for p in particles:
            p.update()

        # Collisions
        for ring in rings:
            result = ring.check_physics_collision(ball)
            if result:
                if result == "destroyed":
                    for r in rings:
                        if r.alive:
                            r.reverse_direction()
                elif result[0] == "bounce":
                    inside = result[1]
                    # Корректируем позицию и отражаем скорость
                    ball.correct_position(ring, inside)
                    dx = ball.x - ring.x
                    dy = ball.y - ring.y
                    dist = math.hypot(dx, dy)
                    nx, ny = dx / dist, dy / dist
                    ball.reflect(nx, ny)

        particles[:] = [p for p in particles if p.life > 0]

        # Draw
        screen.fill((0, 0, 0))
        for ring in rings:
            ring.draw(screen)
        ball.draw(screen)
        for p in particles:
            p.draw(screen)

        pygame.display.flip()

        # Check if ball is off screen
        if ball.x < -ball.radius or ball.x > WIDTH + ball.radius or ball.y < -ball.radius or ball.y > HEIGHT + ball.radius:
            running = False
# После завершения игры — переход к следующей итерации while True (новая игра)