from agent import Agent
from config import agent_count
from pythonFiles import world


class Population:
    def __init__(self, count=agent_count):
        self.agents = [Agent(agent_id=i) for i in range(count)]
        
    def step_agents(self, world_obj):
        for agent in self.agents:
            agent.move(world_obj)
        world_obj.turnNo +=1;