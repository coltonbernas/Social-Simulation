package com.socialsimulation;
import com.socialsimulation.agent.Agent;
import com.socialsimulation.population.Population;

public class Main {
    public static void main(String[] args) {

        Population population = new Population();

        Agent agent1 = new Agent(1, "Najin",22);
        Agent agent2 = new Agent(2, "Kaira",21);
        Agent agent3 = new Agent(3, "Colton",21);

        population.addAgent(agent1);
        population.addAgent(agent2);
        population.addAgent(agent3);

        System.out.println("Population size: " + population.getSize());

        for  (Agent agent : population.getAgents()) {
            System.out.println(agent.getId() + "-" + agent.getName() + "-" + agent.getAge());
        }
    }
}
