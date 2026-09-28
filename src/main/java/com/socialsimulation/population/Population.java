package com.socialsimulation.population;

import com.socialsimulation.agent.Agent;

import java.util.ArrayList;
import java.util.List;

public class Population {

    private final List<Agent> agents;
    public Population() {
        agents = new ArrayList<>();
    }
    public void addAgent(Agent agent) {
        agents.add(agent);
    }
    public List<Agent> getAgents() {
        return agents;
    }
    public int getSize() {
        return agents.size();
    }
}
