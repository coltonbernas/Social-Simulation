package com.socialsimulation.agent;

public class Agent {

    private final int id;  //final bc the identity shouldnt randomly change
    private String name;
    private int age;

    public Agent(int id, String name, int age) {
        this.id = id;
        this.name = name;
        this.age = age;
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

}
