import pygame
import sys
import requests
import random
import threading

pygame.init()

WIDTH, HEIGHT = 800, 800
CENTER = WIDTH // 2

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("We winning this, twin✌🏼")

# COLORS
BLACK = (0,0,0)
GRAY = (40,40,40)
WHITE = (255,255,255)
RED = (255,0,0)
YELLOW = (255,255,0)
GREEN = (0,255,0)
BLUE = (0,150,255)

font = pygame.font.SysFont(None, 24)

ESP32_URL = "http://192.168.1.31/status"

state_data = {
    "direction": 0,
    "state": "RED",
    "emergency": False,
    "pedestrian": False,
    "north": 0,
    "east": 0,
    "south": 0,
    "west": 0
}

clock = pygame.time.Clock()

# ROAD CONFIG
LANE_WIDTH = 20
LANES_PER_SIDE = 3
ROAD_HALF = LANE_WIDTH * LANES_PER_SIDE
STOP_OFFSET = 80
TURN_ZONE = 40
LANES = [-15, -5, 5]

STOP_LINE = {
    0: CENTER - STOP_OFFSET,
    1: CENTER + STOP_OFFSET,
    2: CENTER + STOP_OFFSET,
    3: CENTER - STOP_OFFSET
}

vehicles = []
pedestrians = []
ped_spawn_timer = 0

# LEFT SIDE LANES (incoming side)
lane_offsets = [-LANE_WIDTH*0.5, -LANE_WIDTH*1.5, -LANE_WIDTH*2.5]

# ================= FETCH =================
def fetch_loop():
    global state_data

    while True:
        try:
            res = requests.get(ESP32_URL, timeout=0.2)
            if res.status_code == 200:
                new_data = res.json()

                state_data["direction"] = new_data["direction"]
                state_data["emergency"] = new_data["emergency"]
                state_data["pedestrian"] = new_data["pedestrian"]
                state_data["north"] = new_data.get("north", 0)
                state_data["east"]  = new_data.get("east", 0)
                state_data["south"] = new_data.get("south", 0)
                state_data["west"]  = new_data.get("west", 0)

                if "GREEN" in new_data["state"]:
                    state_data["state"] = "GREEN"
                elif "YELLOW" in new_data["state"]:
                    state_data["state"] = "YELLOW"
                else:
                    state_data["state"] = "RED"

        except:
            pass

        pygame.time.wait(800)  # ~1 update/sec

# ================= DRAW =================
def draw_roads():
    screen.fill(GRAY)

    pygame.draw.rect(screen, BLACK, (CENTER-ROAD_HALF, 0, ROAD_HALF*2, HEIGHT))
    pygame.draw.rect(screen, BLACK, (0, CENTER-ROAD_HALF, WIDTH, ROAD_HALF*2))

    # vertical divider (TOP)
    pygame.draw.line(screen, (200,200,0),
                    (CENTER, 0),
                    (CENTER, STOP_LINE[0]), 2)

    # vertical divider (BOTTOM)
    pygame.draw.line(screen, (200,200,0),
                    (CENTER, STOP_LINE[2]),
                    (CENTER, HEIGHT), 2)

    # horizontal divider (LEFT)
    pygame.draw.line(screen, (200,200,0),
                    (0, CENTER),
                    (STOP_LINE[3], CENTER), 2)

    # horizontal divider (RIGHT)
    pygame.draw.line(screen, (200,200,0),
                    (STOP_LINE[1], CENTER),
                    (WIDTH, CENTER), 2)

def draw_zebra():
    stripe_width = 3
    gap = 4

    for i in range(-ROAD_HALF, ROAD_HALF, stripe_width + gap):
        # top crossing
        pygame.draw.rect(screen, WHITE, (CENTER + i, STOP_LINE[0] + 2.5, stripe_width, 15))
        # bottom
        pygame.draw.rect(screen, WHITE, (CENTER + i, STOP_LINE[2] - 15, stripe_width, 15))
        # left
        pygame.draw.rect(screen, WHITE, (STOP_LINE[3] + 2.5, CENTER + i, 15, stripe_width))
        # right
        pygame.draw.rect(screen, WHITE, (STOP_LINE[1] - 15, CENTER + i, 15, stripe_width))

def draw_lane_markings():
    for i in range(1, LANES_PER_SIDE):
        offset = i * LANE_WIDTH

        # vertical lanes
        for y in range(0, STOP_LINE[0], 40):
            pygame.draw.line(screen, WHITE, (CENTER-offset, y), (CENTER-offset, y+20), 2)
            pygame.draw.line(screen, WHITE, (CENTER+offset, y), (CENTER+offset, y+20), 2)

        for y in range(STOP_LINE[2], HEIGHT, 40):
            pygame.draw.line(screen, WHITE, (CENTER-offset, y), (CENTER-offset, y+20), 2)
            pygame.draw.line(screen, WHITE, (CENTER+offset, y), (CENTER+offset, y+20), 2)

        # horizontal lanes
        for x in range(0, STOP_LINE[3], 40):
            pygame.draw.line(screen, WHITE, (x, CENTER-offset), (x+20, CENTER-offset), 2)
            pygame.draw.line(screen, WHITE, (x, CENTER+offset), (x+20, CENTER+offset), 2)

        for x in range(STOP_LINE[1], WIDTH, 40):
            pygame.draw.line(screen, WHITE, (x, CENTER-offset), (x+20, CENTER-offset), 2)
            pygame.draw.line(screen, WHITE, (x, CENTER+offset), (x+20, CENTER+offset), 2)

def draw_crossing_active():
    if state_data["pedestrian"]:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 255, 255, 40))  # translucent glow
        screen.blit(overlay, (0,0))

def draw_pedestrian_signal():
    if state_data["pedestrian"]:
        pygame.draw.circle(screen, (0,255,255), (50, 50), 10)
        screen.blit(font.render("PEDESTRIAN WAIT", True, WHITE), (70, 45))

def draw_stop_lines():
    #TOP
    pygame.draw.line(screen, WHITE, (CENTER-ROAD_HALF, STOP_LINE[0]),(CENTER+ROAD_HALF, STOP_LINE[0]), 4)
    #RIGHT
    pygame.draw.line(screen, WHITE, (STOP_LINE[1], CENTER-ROAD_HALF),(STOP_LINE[1], CENTER+ROAD_HALF), 4)
    #BOTTOM
    pygame.draw.line(screen, WHITE, (CENTER-ROAD_HALF, STOP_LINE[2]),(CENTER+ROAD_HALF, STOP_LINE[2]), 4)
    #LEFT
    pygame.draw.line(screen, WHITE, (STOP_LINE[3], CENTER-ROAD_HALF),(STOP_LINE[3], CENTER+ROAD_HALF), 4)

def get_lane_center(direction, lane_offset):
    if direction in [0, 2]:  # vertical
        return CENTER + lane_offset
    else:  # horizontal
        return CENTER + lane_offset
    
#SIGNALS + ARROWS
def draw_signals():
    offset = 90

    positions = [
        (CENTER+offset, CENTER-ROAD_HALF-30),
        (CENTER+ROAD_HALF+30, CENTER+offset),
        (CENTER-offset, CENTER+ROAD_HALF+30),
        (CENTER-ROAD_HALF-30, CENTER-offset)
    ]

    for i, pos in enumerate(positions):

        if i == state_data["direction"]:
            if state_data["state"] == "GREEN":
                color = GREEN
            elif state_data["state"] == "YELLOW":
                color = YELLOW
            else:
                color = RED
        else:
            color = RED

        pygame.draw.circle(screen, color, pos, 10)

        # ARROW next to signal
        if i == 0:  # North
            pygame.draw.polygon(screen, WHITE, [
                (pos[0]-20, pos[1]),
                (pos[0]-10, pos[1]-6),
                (pos[0]-10, pos[1]+6)
            ])
        elif i == 1:  # East
            pygame.draw.polygon(screen, WHITE, [
                (pos[0], pos[1]-20),
                (pos[0]-6, pos[1]-10),
                (pos[0]+6, pos[1]-10)
            ])
        elif i == 2:  # South
            pygame.draw.polygon(screen, WHITE, [
                (pos[0]+20, pos[1]),
                (pos[0]+10, pos[1]-6),
                (pos[0]+10, pos[1]+6)
            ])
        elif i == 3:  # West
            pygame.draw.polygon(screen, WHITE, [
                (pos[0], pos[1]+20),
                (pos[0]-6, pos[1]+10),
                (pos[0]+6, pos[1]+10)
            ])

# ================= PEDESTRIAN =================            
class Pedestrian:
    def __init__(self, side):
        self.side = side
        self.speed = 80
        self.size = 8

        if side == 0:  # top → down
            self.x = CENTER - 30
            self.y = STOP_LINE[0] - 30

        elif side == 1:  # right → left
            self.x = STOP_LINE[1] + 30
            self.y = CENTER - 30

        elif side == 2:  # bottom → up
            self.x = CENTER + 30
            self.y = STOP_LINE[2] + 30

        elif side == 3:  # left → right
            self.x = STOP_LINE[3] - 30
            self.y = CENTER + 30

    def move(self, dt):
        if self.side == 0:
            self.y += self.speed * dt
        elif self.side == 1:
            self.x -= self.speed * dt
        elif self.side == 2:
            self.y -= self.speed * dt
        elif self.side == 3:
            self.x += self.speed * dt

    def draw(self):
        pygame.draw.circle(screen, (0,255,255), (int(self.x), int(self.y)), self.size)

# ================= VEHICLE =================
class Vehicle:
    def __init__(self, direction):
        import random

        self.type = random.choice(["car", "bus", "bike"])
        self.turn = random.choice(["straight", "left", "right"])
        self.turned = False
        lane = random.choice(lane_offsets)
        self.lane = lane

        if self.type == "car":
            self.size = 20
            self.max_speed = 120

        elif self.type == "bus":
            self.size = 40
            self.max_speed = 80

        elif self.type == "bike":
            self.size = 10
            self.max_speed = 140

        self.direction = direction
        self.speed = 0
        self.max_speed = 120
        self.acc = 200
        self.brake = 400
        self.is_emergency = False

        # randomly assign ONLY if ESP says emergency
        if state_data["emergency"] and direction == state_data.get("emergency_dir", -1):
            if random.random() < 0.3:  # spawn some emergency vehicles
                self.is_emergency = True

        if self.is_emergency:
            self.max_speed = 160

        self.size = 14

        if direction == 0:  # coming from top → going down
            self.x = CENTER - lane - self.size // 2
            self.y = -20 - self.size // 2

        elif direction == 1:  # right → going left
            self.x = WIDTH + 20 - self.size // 2
            self.y = CENTER - lane - self.size // 2

        elif direction == 2:  # bottom → going up
            self.x = CENTER + lane - self.size // 2
            self.y = HEIGHT + 20 - self.size // 2

        elif direction == 3:  # left → going right
            self.x = -20 - self.size // 2
            self.y = CENTER + lane - self.size // 2

    def move(self, others, dt):

        #CHECK IF ALREADY CROSSED
        crossed = False

        if self.direction == 0 and self.y > STOP_LINE[0]:
            crossed = True
        elif self.direction == 1 and self.x < STOP_LINE[1]:
            crossed = True
        elif self.direction == 2 and self.y < STOP_LINE[2]:
            crossed = True
        elif self.direction == 3 and self.x > STOP_LINE[3]:
            crossed = True

        #SIGNAL LOGIC
        allow = ((self.direction == state_data["direction"] and state_data["state"] == "GREEN") or crossed)
        desired_speed = self.max_speed

        # VEHICLE AHEAD LOGIC
        safe_gap = self.size * 2

        for v in others:
            if v == self:
                continue

            if v.direction != self.direction:
                continue

            # STRICT SAME LANE CHECK 
            same_lane = False

            if self.direction in [0, 2]:  # vertical
                if abs(v.x - self.x) < 3:
                    same_lane = True
            else:  # horizontal
                if abs(v.y - self.y) < 3:
                    same_lane = True

            if not same_lane:
                continue

            # CHECK ONLY VEHICLE AHEAD 
            if self.direction == 0 and v.y > self.y:
                gap = v.y - (self.y + self.size)

            elif self.direction == 1 and v.x < self.x:
                gap = (self.x) - (v.x + v.size)

            elif self.direction == 2 and v.y < self.y:
                gap = (self.y) - (v.y + v.size)

            elif self.direction == 3 and v.x > self.x:
                gap = v.x - (self.x + self.size)

            else:
                continue

            # HARD CONSTRAINT (NO OVERLAP)
            if gap < safe_gap:
                desired_speed = min(desired_speed, gap * 1.5)

            # EXTRA SAFETY STOP
            if gap < 10:
                self.speed = 0
                return

        #STOP LINE LOGIC
        stop_dist = 0

        if self.direction == 0:
            stop_dist = STOP_LINE[0] - (self.y + self.size)
        elif self.direction == 1:
            stop_dist = self.x - STOP_LINE[1]
        elif self.direction == 2:
            stop_dist = self.y - STOP_LINE[2]
        elif self.direction == 3:
            stop_dist = STOP_LINE[3] - (self.x + self.size)

        # slow down near stop if not allowed
        if not allow and stop_dist < 80:
            desired_speed = max(0, stop_dist * 2)

        # full stop
        if not allow and stop_dist <= 2:
            self.speed = 0
            return

        #PEDESTRIAN LOGIC
        if state_data["pedestrian"]:
            near_crossing = False

            if self.direction == 0 and self.y + self.size >= STOP_LINE[0] - 20:
                near_crossing = True
            elif self.direction == 1 and self.x <= STOP_LINE[1] + 20:
                near_crossing = True
            elif self.direction == 2 and self.y <= STOP_LINE[2] + 20:
                near_crossing = True
            elif self.direction == 3 and self.x + self.size >= STOP_LINE[3] - 20:
                near_crossing = True

            if near_crossing:
                desired_speed = 0

        #TURN LOGIC (SIMPLE & STABLE)
        turn_trigger = 10  # small zone

        if not self.turned:

            if self.direction == 0 and abs(self.y - CENTER) < turn_trigger:
                trigger = True
            elif self.direction == 1 and abs(self.x - CENTER) < turn_trigger:
                trigger = True
            elif self.direction == 2 and abs(self.y - CENTER) < turn_trigger:
                trigger = True
            elif self.direction == 3 and abs(self.x - CENTER) < turn_trigger:
                trigger = True
            else:
                trigger = False

            if trigger:
                if self.turn == "right":

                    if self.direction == 0:  # top → right
                        self.direction = 1
                        self.y = CENTER - self.lane - self.size // 2

                    elif self.direction == 1:  # right → bottom
                        self.direction = 2
                        self.x = CENTER + self.lane - self.size // 2

                    elif self.direction == 2:  # bottom → left
                        self.direction = 3
                        self.y = CENTER + self.lane - self.size // 2

                    elif self.direction == 3:  # left → top
                        self.direction = 0
                        self.x = CENTER - self.lane - self.size // 2

                    self.turned = True

                elif self.turn == "left":

                    if self.direction == 0:
                        self.direction = 3
                    elif self.direction == 3:
                        self.direction = 2
                    elif self.direction == 2:
                        self.direction = 1
                    elif self.direction == 1:
                        self.direction = 0

                    self.turned = True
                if abs(self.x - CENTER) < 50 and abs(self.y - CENTER) < 50:
                    self.speed = min(self.speed, 70)

        #ACCEL / BRAKE
        diff = desired_speed - self.speed

        if diff > 0:
            self.speed += min(self.acc * dt, diff)
        else:
            self.speed += max(-self.brake * dt, diff)

        self.speed = max(0, min(self.speed, self.max_speed))

        # slow down in intersection for smoother turning
        in_center = (
            abs(self.x - CENTER) < 60 and
            abs(self.y - CENTER) < 60
        )

        if in_center:
            self.speed = min(self.speed, 80)

        #MOVE
        move_dist = self.speed * dt

        if self.direction == 0:
            self.y += move_dist
        elif self.direction == 1:
            self.x -= move_dist
        elif self.direction == 2:
            self.y -= move_dist
        elif self.direction == 3:
            self.x += move_dist

    def draw(self):
        if self.type == "car":
            color = (0,150,255)  # blue
            pygame.draw.rect(screen, color, (int(self.x), int(self.y), self.size, self.size))
        elif self.type == "bus":
            color = (255,165,0)  # orange
            pygame.draw.rect(screen, color, (int(self.x), int(self.y), self.size, self.size))
        else:
            color = (0,255,100)  # green bike
            pygame.draw.rect(screen, color, (int(self.x), int(self.y), self.size, self.size))



# ================= MAIN LOOP =================
spawn_timer = 0
fetch_timer = 0
fetching = False
threading.Thread(target=fetch_loop, daemon=True).start()
prev_direction = -1
prev_counts = [0, 0, 0, 0]
def spawn_from_esp():
            if len(vehicles) > 100:
                return
            
            counts = [
                state_data["north"],
                state_data["east"],
                state_data["south"],
                state_data["west"]
            ]

            for direction, count in enumerate(counts):
                for _ in range(max(1, count // 10)):  # scale down (important)
                    vehicles.append(Vehicle(direction))

def fetch_data():
    global state_data

    try:
        res = requests.get(ESP32_URL, timeout=0.2)
        if res.status_code == 200:
            state_data = res.json()
    except Exception as e:
        print("Fetch error:", e)

while True:
    dt = clock.tick(60) / 1000.0

    fetch_data()
    if state_data["direction"] != prev_direction:
        spawn_from_esp()
        prev_direction = state_data["direction"]
    
    if state_data["pedestrian"]:
        ped_spawn_timer += 1
        if ped_spawn_timer > 20:
            pedestrians.append(Pedestrian(random.randint(0,3)))
            ped_spawn_timer = 0
    else:
        pedestrians.clear()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    fetch_timer += dt

    if fetch_timer > 1:   
        fetch_timer = 0

    spawn_timer += 1
    if spawn_timer > 30:
        spawn_from_esp()
        spawn_timer = 0

    draw_roads()
    draw_lane_markings()
    draw_stop_lines()
    draw_zebra()               
    draw_signals()
    draw_pedestrian_signal()   
    draw_crossing_active()     

    for v in vehicles:
        v.move(vehicles, dt)
        v.draw()
    
    for p in pedestrians:
        p.move(dt)
        p.draw()

    pygame.display.flip()