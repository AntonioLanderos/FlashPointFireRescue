# -*- coding: utf-8 -*-

from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import json

import heapq

from mesa import Agent, Model, batch_run
from mesa.space import MultiGrid
from mesa.time import SimultaneousActivation
from mesa.datacollection import DataCollector

import random

import itertools

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import matplotlib.animation as animation

import pandas as pd

import seaborn as sns

random.seed(42)

class FireRescueAgent(Agent):
    def __init__(self, id, model, start_position):
        super().__init__(id, model)
        self.id = id
        self.carrying_survivor = False
        self.action_points = 0
        self.skip_turn = False
        self.history = []
        self.starting_position = start_position

    def calculate_distance(self, start_cell, target_cell):
        # Calculate Manhattan distance
        return abs(start_cell[0] - target_cell[0]) + abs(start_cell[1] - target_cell[1])

    def find_path(self, grid_map, current_location, targets):
        '''
        A* pathfinding algorithm to find the shortest path to a target cell.
        '''
        priority_queue = [(0, current_location)]
        visited_nodes = set()
        path_trail = {}
        accumulated_cost = {current_location: 0}

        if targets:
            while priority_queue:
                _, active_cell = heapq.heappop(priority_queue)

                if active_cell in targets:
                    path = []
                    while active_cell in path_trail:
                        path.append(active_cell)
                        active_cell = path_trail[active_cell]
                    return path[::-1]

                visited_nodes.add(active_cell)

                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    neighbor = (active_cell[0] + dx, active_cell[1] + dy)

                    if neighbor not in grid_map or neighbor in visited_nodes:
                        continue

                    move_cost = grid_map[neighbor]
                    total_cost = accumulated_cost[active_cell] + move_cost

                    if neighbor not in accumulated_cost or total_cost < accumulated_cost[neighbor]:
                        accumulated_cost[neighbor] = total_cost
                        valid_targets = [self.calculate_distance(neighbor, goal) for goal in targets if targets[goal]]

                        if valid_targets:
                            priority = total_cost + min(valid_targets)
                        else:
                            priority = total_cost + self.calculate_distance(neighbor, current_location)

                        heapq.heappush(priority_queue, (priority, neighbor))
                        path_trail[neighbor] = active_cell

            return [current_location]  # No path found
        return [current_location]

    def move_agent(self):
        neighbors = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)

        if self.carrying_survivor:
            target_goal = {self.starting_position: False}
        else:
            target_goal = self.model.poi

        path = self.find_path(self.model.grid_values, self.pos, target_goal)

        next_cell = path[0] if path else random.choice(neighbors)

        if model.check_collision(self.pos, next_cell):
            next_cell = random.choice(neighbors)

        if neighbors:
            is_fire = self.model.grid_values[next_cell] == 2
            is_safe = self.model.grid_values[next_cell] != 2

            if self.pos in self.model.door_data and next_cell in self.model.door_data and self.action_points >= 1:
                if not self.model.door_data[self.pos] and not self.model.door_data[next_cell]:
                    self.toggle_door(self.pos, next_cell)

            if not model.check_collision(self.pos, next_cell):
                if is_fire and self.action_points >= 2:
                    self.model.grid.move_agent(self, next_cell)
                    self.history.append(f"Moved to: {next_cell}")
                    self.action_points -= 2
                elif is_safe and self.action_points >= 1:
                    self.model.grid.move_agent(self, next_cell)
                    self.history.append(f"Moved to: {next_cell}")
                    self.action_points -= 1

            self.reveal_poi()

    def reveal_poi(self):
        if self.pos in self.model.poi and self.model.poi[self.pos]:
            self.carrying_survivor = True
            del self.model.poi[self.pos]
            self.history.append(f"Revealed POI at: {self.pos}")

    def toggle_door(self, cell_1, cell_2):
        if cell_1 in self.model.door_data and cell_2 in self.model.door_data:
            self.model.door_data[cell_1] = True
            self.model.door_data[cell_2] = True
            self.history.append(f"Opened door between: {cell_1} and {cell_2}")
            self.action_points -= 1

    def extinguish_fire(self):
        neighbors = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
        fire_cells = [cell for cell in neighbors if self.model.grid_values[cell] == 2]
        smoke_cells = [cell for cell in neighbors if self.model.grid_values[cell] == 1]

        if fire_cells and self.action_points >= 2:
            target_cell = random.choice(fire_cells)
            self.model.grid_values[target_cell] = 0
            self.history.append(f"Extinguished fire at: {target_cell}")
            self.action_points -= 2
        elif smoke_cells and self.action_points >= 1:
            target_cell = random.choice(smoke_cells)
            self.model.grid_values[target_cell] = 0
            self.history.append(f"Extinguished smoke at: {target_cell}")
            self.action_points -= 1

    def take_action(self):
        '''
        The agent will take actions until it runs out of action points or it decides to end its turn.
        '''
        if self.pos == self.starting_position and self.carrying_survivor:
            self.model.survivors_saved += 1
            self.carrying_survivor = False

        actions = [self.move_agent, self.extinguish_fire]
        random.shuffle(actions)

        while not self.skip_turn and self.action_points > 0:
            chosen_action = random.choice(actions)
            chosen_action()
            if self.action_points <= 0:
                self.end_turn()

    def end_turn(self):
        self.history.append("Turn ended")
        self.skip_turn = True

    def step(self):
        self.skip_turn = False
        self.history = []
        self.action_points += 4
        self.action_points = min(self.action_points, 8)
        self.take_action()


def get_grid(model):
    grid = []
    for row_index in range(model.grid.height):
        row_data = []
        for col_index in range(model.grid.width):
            cell = (col_index, row_index)
            if not model.grid.is_cell_empty(cell):
                row_data.append(3)  # Agent
            elif cell in model.poi:
                row_data.append(4)  # POI
            elif model.grid_values[cell] == 1:
                row_data.append(1)  
            elif model.grid_values[cell] == 2:
                row_data.append(2)  
            else:
                row_data.append(0)  # Empty
        grid.append(row_data)
    return grid

def get_walls(model):
    walls = []
    for row_index in range(model.grid.height):
        wall_row = []
        for col_index in range(model.grid.width):
            wall_row.append(model.wall_states[(col_index, row_index)][0])
        walls.append(wall_row)
    return walls


class FireRescueModel(Model):
    def __init__(self, num_firefighters, poi, wall_data, door_states, initial_fire, spawn_points):
        super().__init__()
        self.current_step = 0
        self.schedule = SimultaneousActivation(self)
        self.survivors_saved = 0
        self.survivor_losses = 0
        self.simulation_status = "In progress"
        self.fire_locations = [(int(y) - 1, int(x) - 1) for x, y in (coord.split() for coord in initial_fire)]
        self.wall_configuration = [row.split() for row in wall_data]
        self.datacollector = DataCollector(
            model_reporters={
                "Grid": get_grid,
                "Walls": get_walls,
                "StepCount": "current_step",
                "DoorStatus": "door_data",
                "POIs": "interest_points",
                "RescuedCount": "survivors_saved",
                "SimulationStatus": "simulation_status",
                "DamageScore": "damage_tracker",
                "Efficiency": lambda model: model.survivors_saved / model.current_step if model.current_step > 0 else 0,
            },
            agent_reporters={
                "AgentID": lambda agent: agent.id,
                "CurrentPosition": lambda agent: (agent.pos[0], agent.pos[1]),
                "Actions": lambda agent: agent.history,
            },
        )
        self.poi = {
            (int(y) - 1, int(x) - 1): state for (x, y), state in poi.items()
        }
        self.width = 8
        self.height = 6
        self.door_data = door_states
        self.spawn_points = [(int(y) - 1, int(x) - 1) for x, y in (coord.split() for coord in spawn_points)]
        self.grid = MultiGrid(self.width, self.height, torus=False)
        self.grid_values = {(x, y): 0 for y in range(self.height) for x in range(self.width)}
        self.wall_states = {(x, y): ["0000", "0000"] for y in range(self.height) for x in range(self.width)}
        self.damage_tracker = 0
        self.victory_counter = 0

        # Initialize walls
        for y, row in enumerate(self.wall_configuration):
            for x, value in enumerate(row):
                self.wall_states[(x, y)] = [value, "0000"]

        # Initialize fire 
        for pos in self.fire_locations:
            self.grid_values[pos] = 2

        # Initialize POIs
        for key, state in self.poi.items():
            pass  

        # Add firefighters to the simulation
        spawn_cycle = itertools.cycle(self.spawn_points)
        for firefighter_id in range(num_firefighters):
            spawn_position = next(spawn_cycle)
            agent = FireRescueAgent(firefighter_id, self, spawn_position)
            self.grid.place_agent(agent, spawn_position)
            self.schedule.add(agent)

    def add_poi(self):
        current_count = len(self.poi)
        if current_count < 3:
            points_to_add = 3 - current_count
            while points_to_add > 0:
                random_point = (random.randint(0, self.width - 1), random.randint(0, self.height - 1))
                if random_point not in self.poi:
                    self.poi[random_point] = True
                    self.grid_values[random_point] = 0
                    points_to_add -= 1

    def spread_fire(self):
        fire_candidates = [pos for pos, value in self.grid_values.items() if value in (0, 1, 2)]
        if fire_candidates:
            fire_source = random.choice(fire_candidates)
            if self.grid_values[fire_source] == 0:
                self.grid_values[fire_source] = 1
            elif self.grid_values[fire_source] == 1:
                self.grid_values[fire_source] = 2
            elif self.grid_values[fire_source] == 2:
                neighbors = self.grid.get_neighborhood(fire_source, moore=False, include_center=False)
                for neighbor in neighbors:
                    if self.check_collision(fire_source, neighbor):
                        self.damage(fire_source, neighbor)
                    if self.grid_values[neighbor] == 0:
                        self.grid_values[neighbor] = 2
                    elif self.grid_values[neighbor] == 1:
                        self.grid_values[neighbor] = 2

    def check_collision(self, origin, destination):
      """
        Check if there is a wall or door blocking the path between two cells
      """
      x_diff = destination[0] - origin[0]
      y_diff = destination[1] - origin[1]

      direction = None
      if x_diff == 0:
          direction = 0 if y_diff < 0 else 2
      elif y_diff == 0:
          direction = 1 if x_diff < 0 else 3

      wall_block = direction is not None and self.wall_states[origin][0][direction] == "1"
      door_block = origin in self.door_data and destination in self.door_data and not (
          self.door_data[origin] and self.door_data[destination])

      return wall_block or door_block


    def damage(self, start, end):
        if start in self.door_data and end in self.door_data:
            if not self.door_data[start] and not self.door_data[end]:
                del self.door_data[start]
                del self.door_data[end]
                self.damage_tracker += 1
        else:
            self.damage_tracker += 1

    def win_condition(self):
        if self.survivor_losses >= 4 or self.damage_tracker >= 24:
            self.simulation_status = "Defeat"
            return True
        elif self.survivors_saved >= 7:
            self.simulation_status = "Victory"
            self.victory_counter += 1
            return True
        return False

    def step(self):
        self.datacollector.collect(self)
        if not self.win_condition():
            self.current_step += 1
            self.schedule.step()
            self.spread_fire()
            self.add_poi()

WALLS=  [
    "1100" "1000" "1000" "1000" "1001" "1111" "1101" "1101",
    "0110" "0010" "0000" "0000" "0001" "1111" "0100" "0001",
    "1100" "1000" "0001" "1110" "1011" "1110" "0010" "0011",
    "0100" "0001" "0100" "1010" "1010" "1011" "1110" "1011",
    "0100" "0000" "0001" "1100" "1001" "1100" "1000" "1001",
    "0110" "0010" "0011" "0110" "0011" "0110" "0010" "0011"
]

POI = {(2,4):False,(6,7):True,(4,8):True,}

NUM_FIREFIGHTERS= 6

FIRE= [
    "1 7",
    "4 3",
    "5 2",
    "1 5",
    "2 2",
    "2 6",
    "6 1",
    "1 8",
    "2 1",
    "6 4"
    ]

DOORS= [
    "1 6 1 7",
    "2 6 2 7",
    "3 6 4 6",
    "4 6 4 7",
    "4 5 5 5",
    "4 6 5 6",
    "5 3 5 4",
    "3 5 4 5"
    ]

ENTRY_POINTS= [
    "1 3",
    "1 8",
    "5 1",
    "6 3"
]

DOORS_DICTIONARY = {
    (y -1, x-1): False
    for door in DOORS
    for x1, y1, x2, y2 in [map(int, door.split())]
    for x in range(min(x1, x2), max(x1, x2) + 1)
    for y in range(min(y1, y2), max(y1, y2) + 1)
}

steps = 30

model = FireRescueModel(NUM_FIREFIGHTERS, POI, WALLS, DOORS_DICTIONARY, FIRE, ENTRY_POINTS)

for i in range(steps):
    model.step()
    print("Survivors saved: ", model.survivors_saved)
    print("Survivors lost: ", model.survivor_losses)
    print("Damage score: ", model.damage_tracker)
    print("Simulation status: ", model.simulation_status)
    print("")

print('Victory counter: ', model.victory_counter)

# def get_json( datacollector):
    
#         model_data = datacollector.get_model_vars_dataframe().to_dict(orient="records")
#         # print it
#         print(model_data)
        
#         # Maneja inconsistencias en los datos de los agentes
#          # unnecessary
#         agent_data = datacollector.get_agent_vars_dataframe().to_dict(orient="records")
#         # print it 
#         print(agent_data)
     
        
#         # Combina los datos
#         output_data = {
#             "model": model_data,
#             "agents": agent_data
#         }
#         print(output_data)
        
#         # Guarda en un archivo JSON
#         with open(json_file_path, "w") as json_file:
#             json.dump(output_data, json_file, indent=4)
#         print(f"Datos exportados a {json_file_path}")
#     except Exception as e:
#         print(f"Error al exportar datos: {e}")


# get_json( model.datacollector)

# all_grids = model.datacollector.get_model_vars_dataframe()
# print(all_grids.head(10))

# empty = 'white'
# fire = 'red'
# smoke = 'gray'
# poi = 'green'
# firefighter = 'blue'

# cmap = ListedColormap([empty, smoke, fire, firefighter, poi])

# fig, axis = plt.subplots(figsize=(6, 6))
# axis.set_xticks([])
# axis.set_yticks([])
# patch = plt.imshow(all_grids.iloc[0,0], cmap=cmap)

# def animate(i):
#   patch.set_data(all_grids.iloc[i][0])

# anim= animation.FuncAnimation(fig, animate, frames=steps)

# params = {
#     'num_firefighters': [6],  # Lista para iterar en batch_run
#     'poi': [  # Lista con diferentes configuraciones de puntos de interés
#         {
#             (2, 4): False,
#             (6, 7): True,
#             (4, 8): True,
#         }
#     ],
#     'wall_data': [  # Lista de configuraciones de paredes
#         [
#             "1100 1000 1000 1000 1001 1111 1101 1101",
#             "0110 0010 0000 0000 0001 1111 0100 0001",
#             "1100 1000 0001 1110 1011 1110 0010 0011",
#             "0100 0001 0100 1010 1010 1011 1110 1011",
#             "0100 0000 0001 1100 1001 1100 1000 1001",
#             "0110 0010 0011 0110 0011 0110 0010 0011"
#         ]
#     ],
#     'door_states': [  # Lista con diferentes configuraciones de puertas
#         {
#             (0, 5): False, (0, 6): False,
#             (1, 5): False, (1, 6): False,
#             (2, 5): False, (3, 5): False,
#             (3, 3): False, (3, 4): False,
#         }
#     ],
#     'initial_fire': [  # Lista de configuraciones iniciales de fuego
#         [
#             "1 7",
#             "4 3",
#             "5 2",
#             "1 5",
#             "2 2",
#             "2 6",
#             "6 1",
#             "1 8",
#             "2 1",
#             "6 4"
#         ]
#     ],
#     'spawn_points': [  # Lista de configuraciones de puntos de entrada
#         [
#             "1 3",
#             "1 8",
#             "5 1",
#             "6 3"
#         ]
#     ]
# }



# ITERATIONS = 10

# results = batch_run(
#     FireRescueModel,
#     parameters=params,
#     iterations=ITERATIONS,
#     max_steps=30,
#     number_processes=1,
#     data_collection_period=1,
#     display_progress=True
# )
