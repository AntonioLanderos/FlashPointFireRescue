from mesa import Agent, Model
from mesa.space import MultiGrid
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from matplotlib.colors import ListedColormap


def calculate_distance(pos1, pos2):
  """Calcula la distancia de Manhattan entre dos posiciones."""
  x1, y1 = pos1
  x2, y2 = pos2
  return abs(x1 - x2) + abs(y1 - y2)

class FireRescueAgent(Agent):
    def __init__(self, unique_id, model, agent_type, state=None):
        super().__init__(unique_id, model)
        self.agent_type = agent_type
        self.state = state
        self.action_points = 4
        self.carrying_victim = False

    def step(self):
        if self.agent_type == "firefighter":
            self.firefighter_step()
        elif self.agent_type == "fire":
            self.fire_step()
        elif self.agent_type == "poi":
            pass  # Los POI no hacen nada en su paso

    def firefighter_step(self):
        if self.action_points <= 0:
            return

        # 1. Extinguir fuego adyacente
        if self.try_extinguish_fire():
            return

        # 2. Rescatar víctima adyacente
        if self.try_rescue_victim():
            return

        # 3. Moverse hacia la salida si está cargando víctima
        if self.carrying_victim:
            if self.move_towards_exit():
                return

        # 5. Moverse hacia la víctima más cercana
        if self.move_towards_victim():
            return

        # Si no hay acciones disponibles, terminar turno
        self.action_points = 0

    def try_extinguish_fire(self):
        neighbors = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
        for neighbor in neighbors:
            for agent in self.model.grid.get_cell_list_contents(neighbor):
                if agent.agent_type == "fire" and agent.state == "fire":
                    agent.state = "smoke"
                    self.action_points -= 1
                    print(f"Firefighter {self.unique_id} extinguished fire at {neighbor}")
                    return True
        return False

    def try_rescue_victim(self):
        for agent in self.model.grid.get_cell_list_contents(self.pos):
            if agent.agent_type == "poi" and agent.state == "v":
                self.carrying_victim = True
                self.model.grid.remove_agent(agent)
                self.model.saved_victims += 1
                self.action_points -= 1
                print(f"Firefighter {self.unique_id} rescued victim at {self.pos}")
                return True
        return False

    def move_towards_exit(self):
        exit_pos = self.find_closest_exit()
        if exit_pos:
            print(f"Firefighter {self.unique_id} targeting exit at {exit_pos}")
        if exit_pos and self.can_move_to(self.pos, exit_pos):
            print(f"Firefighter {self.unique_id} moving to exit at {exit_pos}")
            self.model.grid.move_agent(self, exit_pos)
            self.action_points -= 1
            if exit_pos in self.model.entry_points:
                self.carrying_victim = False
                print(f"Firefighter {self.unique_id} saved victim at exit {exit_pos}")
            return True
        print(f"Firefighter {self.unique_id} cannot move to exit {exit_pos}")
        return False


    def move_towards_victim(self):
        victim = self.find_closest_victim()
        if victim and self.can_move_to(self.pos, victim.pos):
            print(f"Firefighter {self.unique_id} targeting victim at {victim.pos}")
            self.model.grid.move_agent(self, victim.pos)
            self.action_points -= 1
            print(f"Firefighter {self.unique_id} moved towards victim at {victim.pos}")
            return True
        print(f"Firefighter {self.unique_id} cannot move towards victim at {victim.pos}")
        return False

    def find_closest_exit(self):
      exits = self.model.entry_points
      # Aquí `x` ya es una posición, por lo que no necesita cambios
      return min(exits, key=lambda x: self.calculate_distance(self.pos, x))


    def find_closest_victim(self):
        victims = [
            agent for agent in self.model.schedule.agents
            if agent.agent_type == "poi" and agent.state == "v"
        ]
        if not victims:
            return None
        # Pasar las posiciones de los agentes en lugar de los objetos
        return min(victims, key=lambda agent: self.calculate_distance(self.pos, agent.pos))

    
    def calculate_distance(self, pos1, pos2):
      """Calcula la distancia de Manhattan entre dos posiciones."""
      x1, y1 = pos1
      x2, y2 = pos2
      return abs(x1 - x2) + abs(y1 - y2)


    def fire_step(self):
        if self.state == "fire":
            neighbors = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
            for neighbor in neighbors:
                if self.random.random() < 0.3:  # Probabilidad de expansión
                    if self.model.grid.is_cell_empty(neighbor):  # Verificar que no haya pared u otro obstáculo
                        new_fire = FireRescueAgent(f"fire_{neighbor[0]}_{neighbor[1]}", self.model, "fire", state="fire")
                        self.model.grid.place_agent(new_fire, neighbor)
                        self.model.schedule.add(new_fire)
                        print(f"Fire spread to {neighbor}")


    def can_move_to(self, current_pos, target_pos):
        """Determina si un agente puede moverse de current_pos a target_pos."""
        x, y = current_pos
        tx, ty = target_pos

        # Verificar límites del grid
        if not (0 <= tx < self.model.grid.width and 0 <= ty < self.model.grid.height):
            print(f"Invalid movement direction from {current_pos} to {target_pos}")
            return False

        # Obtener el agente pared en la celda actual
        wall_agents = [
            agent for agent in self.model.grid.get_cell_list_contents(current_pos)
            if agent.agent_type == "wall"
        ]

        # Si hay paredes en la celda actual, verificar su configuración
        for wall in wall_agents:
            direction = (tx - x, ty - y)  # Dirección del movimiento
            wall_config = wall.state.get("walls", "0000")
            if not self.is_direction_open(wall_config, direction):
                print(f"Blocked by wall at {current_pos} in direction {direction}")
                return False

        # Si no hay agentes bloqueando, el movimiento es válido
        return True

    def is_direction_open(self, wall_config, direction):
        """Verifica si la dirección está abierta según la configuración de la pared."""
        direction_map = {
            (0, -1): 0,  # Izquierda
            (0, 1): 1,   # Derecha
            (-1, 0): 2,  # Arriba
            (1, 0): 3    # Abajo
        }
        dir_index = direction_map.get(direction)
        if dir_index is None:
            return False  # Movimiento inválido
        return wall_config[dir_index] == "0"

class FireRescueModel(Model):
    def __init__(self, width, height, config):
        super().__init__()
        self.width = width
        self.height = height
        self.grid = MultiGrid(width, height, torus=False)
        self.schedule = RandomActivation(self)
        self.saved_victims = 0
        self.lost_victims = 0
        self.total_damage_counter = 0
        self.victory_victims = 7
        self.failure_victims = 4
        self.running = True
        self.entry_points = []

        # Configuración inicial
        self.place_walls(config[0])
        self.place_pois(config[1])
        self.place_fire(config[2])
        self.place_doors(config[3])
        self.place_entry_points(config[4])
        self.place_firefighters()

        self.datacollector = DataCollector({
            'Grid': self.get_grid,
            "Saved Victims": lambda m: m.saved_victims,
            "Lost Victims": lambda m: m.lost_victims,
            "Total Damage": lambda m: m.total_damage_counter
        })

    def place_walls(self, walls_data):
        for x, row in enumerate(walls_data):
            for y, config in enumerate(row):
                if 0 <= x < self.height and 0 <= y < self.width:  # Validar coordenadas
                    if config != "0000":
                        wall = FireRescueAgent(f"wall_{x}_{y}", self, "wall", state={"integrity": 2, "damage_taken": 0})
                        self.grid.place_agent(wall, (x, y))
                        self.schedule.add(wall)
                else:
                    print(f"Error placing wall at ({x}, {y}). Out of grid bounds.")

    def place_pois(self, pois_data):
        for x, y, is_victim in pois_data:  # Cada elemento tiene tres valores
            state = "v" if is_victim else "f"  # Determina el estado del POI
            poi = FireRescueAgent(f"poi_{x}_{y}", self, "poi", state=state)
            self.grid.place_agent(poi, (x - 1, y - 1))  # Ajusta las coordenadas a base 0 si es necesario
            self.schedule.add(poi)

    def place_fire(self, fire_data):
        for x, y in fire_data:
            fire = FireRescueAgent(f"fire_{x}_{y}", self, "fire", state="fire")
            self.grid.place_agent(fire, (x - 1, y - 1))
            self.schedule.add(fire)

    def place_doors(self, doors_data):
        for (x1, y1), (x2, y2) in doors_data:
            door = FireRescueAgent(f"door_{x1}_{y1}", self, "door", state={"is_open": False})
            self.grid.place_agent(door, (x1 - 1, y1 - 1))
            self.grid.place_agent(door, (x2 - 1, y2 - 1))
            self.schedule.add(door)

    def place_entry_points(self, entry_points):
        """
        Coloca puntos de entrada en el grid y los marca como puertas de salida.
        """
        for x, y in entry_points:
            if 1 <= x <= self.height and 1 <= y <= self.width:  # Validar coordenadas
                # Ajustar a base 0 para el grid
                self.entry_points.append((x - 1, y - 1))
                # Crear un marcador visual opcional para los puntos de entrada
                marker = FireRescueAgent(f"entry_{x}_{y}", self, "entry_point")
                self.grid.place_agent(marker, (x - 1, y - 1))
                self.schedule.add(marker)
            else:
                print(f"Error: Entry point ({x}, {y}) is out of bounds.")


    def place_firefighters(self):
        """
        Coloca a seis bomberos en posiciones iniciales definidas (fijas).
        """
        initial_positions = [
            (1, 1), (1, self.width),  # Esquinas superiores
            (self.height // 2, 1), (self.height // 2, self.width),  # Centro izquierdo/derecho
            (self.height, 1), (self.height, self.width)  # Esquinas inferiores
        ]
        for i, (x, y) in enumerate(initial_positions):
            if 1 <= x <= self.height and 1 <= y <= self.width:
                firefighter = FireRescueAgent(f"firefighter_{i}", self, "firefighter")
                self.grid.place_agent(firefighter, (x - 1, y - 1))  # Ajustar a base 0
                self.schedule.add(firefighter)
            else:
                print(f"Error placing firefighter at ({x}, {y}). Out of grid bounds.")


    def add_fire(self, pos):
        if self.grid.is_cell_empty(pos):
            fire = FireRescueAgent(f"fire_{pos[0]}_{pos[1]}", self, "fire", state="fire")
            self.grid.place_agent(fire, pos)
            self.schedule.add(fire)

    def get_grid(self):
        """Devuelve una representación numérica del grid para visualización."""
        grid = np.zeros((self.grid.width, self.grid.height))
        for cell in self.grid.coord_iter():
            content, (x, y) = cell  # Asegúrate de que las coordenadas se obtienen como una tupla
            for agent in content:
                if agent.agent_type == "wall":
                    grid[x][y] = 1  # Representar paredes como 1
                elif agent.agent_type == "fire":
                    grid[x][y] = 2 if agent.state == "fire" else 3  # Fuego activo = 2, humo = 3
                elif agent.agent_type == "poi":
                    grid[x][y] = 4  # Puntos de interés/víctimas
                elif agent.agent_type == "firefighter":
                    grid[x][y] = 5  # Bomberos
        return grid


    def step(self):
        self.schedule.step()
        self.datacollector.collect(self)

        # Verificar condiciones de victoria o derrota
        if self.saved_victims >= self.victory_victims:
            print("Victory!")
            self.running = False
        elif self.lost_victims >= self.failure_victims or self.total_damage_counter >= 24:
            print("Game over!")
            self.running = False


# Configuración inicial
WIDTH = 8
HEIGHT = 6

configInicial = [
    [["1100", "1000", "1001", "1100", "1001", "1100", "1000", "1001"],
     ["0100", "0000", "0011", "0100", "0011", "0110", "0010", "0011"],
     ["0100", "0001", "1100", "1000", "1000", "1001", "1100", "1001"],
     ["0100", "0011", "0110", "0010", "0010", "0011", "0110", "0011"],
     ["1100", "1000", "1000", "1000", "1001", "1100", "1001", "1101"],
     ["0110", "0010", "0010", "0010", "0011", "0110", "0011", "0111"]],
    [(2, 4, True), (5, 1, False), (5, 8, True)],  # Cambia aquí
    [(2, 2), (2, 3), (3, 2), (3, 3), (3, 4), (3, 5), (4, 4), (5, 6), (5, 7), (6, 6)],
    [[(1, 3), (1, 4)], [(2, 5), (2, 6)], [(2, 8), (3, 8)], [(3, 2), (3, 3)], [(4, 4), (5, 4)], [(4, 6), (4, 7)], [(6, 5), (6, 6)], [(6, 7), (6, 8)]],
    [(1, 6), (3, 1), (4, 8), (6, 3)]
]

'''
configInicial2 = [
    [["0000"] * 8 for _ in range(6)],  # Sin paredes
    [(2, 4, True)],  # Una víctima
    [(3, 3)],  # Un fuego
    [],  # Sin puertas
    [(1, 1)],  # Un bombero
    [(1, 1)]  # Una salida
]
'''


# Crear el modelo
model = FireRescueModel(WIDTH, HEIGHT, configInicial)


# Ejecutar la simulación
steps = 0
while model.running and steps < 30:
    print(f"Step {steps + 1}")
    model.step()
    print(f"Saved victims: {model.saved_victims}, Lost victims: {model.lost_victims}, Total damage: {model.total_damage_counter}")
    steps += 1

# Imprimir resultados
all_grids = model.datacollector.get_model_vars_dataframe()
print(all_grids.head(5))

empty = 'white'
wall = 'black'
fire = 'red'
smoke = 'gray'
poi = 'green'
firefighter = 'blue'

#cmap = ListedColormap(['white', 'grey', 'red', 'yellow', "blue"])

cmap = ListedColormap([empty, wall, fire, smoke, poi, firefighter])

fig, axis = plt.subplots(figsize = (4, 4))
axis.set_xticks([])
axis.set_yticks([])
patch = plt.imshow(all_grids.iloc[0][0], cmap = cmap)

def animate(i):
  patch.set_data(all_grids.iloc[i][0])

anim = animation.FuncAnimation(fig, animate, frames = len(all_grids))


