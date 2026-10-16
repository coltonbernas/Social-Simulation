package com.socialsimulation;

import com.socialsimulation.agent.Agent;
import com.socialsimulation.environment.Environment;
import com.socialsimulation.environment.EnvironmentParameters;
import com.socialsimulation.population.Population;
import com.socialsimulation.ui.EnvironmentStudio;

import java.awt.GraphicsEnvironment;

public class Main {

    private static final int STARTING_AGE = 21;

    public static void main(String[] args) {
        System.setProperty("apple.awt.application.name", "Social Simulation");
        if (GraphicsEnvironment.isHeadless()) {
            printSample();
            return;
        }
        EnvironmentStudio.open();
    }

    private static void printSample() {
        Environment environment = new Environment(EnvironmentParameters.sample());
        Population population = new Population();
        double[] startingWealth = environment.getStartingWealth();
        for (int i = 0; i < environment.getNumberOfAgents(); i++) {
            population.addAgent(new Agent(i + 1, "Agent " + (i + 1), STARTING_AGE, startingWealth[i]));
        }

        System.out.println(environment.summary());
        System.out.println("Population size: " + population.getSize());
        for (Agent agent : population.getAgents()) {
            System.out.printf(
                    "%d - %s - age %d - wealth %.2f%n",
                    agent.getId(),
                    agent.getName(),
                    agent.getAge(),
                    agent.getWealth());
        }
    }
}
