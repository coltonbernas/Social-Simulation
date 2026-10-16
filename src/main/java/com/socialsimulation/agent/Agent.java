package com.socialsimulation.agent;

public class Agent {

    private final int id;  //final bc the identity shouldnt randomly change
    private String name;
    private int age;
    private double wealth;

    public Agent(int id, String name, int age) {
        this(id, name, age, 0);
    }

    public Agent(int id, String name, int age, double wealth) {
        this.id = id;
        this.name = name;
        this.age = age;
        setWealth(wealth);
    }
    public int getId() {
        return id;
    }
    public String getName() {
        return name;
    }
    public int getAge() {
        return age;
    }
    public double getWealth() {
        return wealth;
    }
    public void setWealth(double wealth) {
        if (!Double.isFinite(wealth)) {
            throw new IllegalArgumentException("wealth must be finite");
        }
        this.wealth = wealth;
    }

}
