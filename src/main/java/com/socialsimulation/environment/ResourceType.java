package com.socialsimulation.environment;

/**
 * A stock the sandbox can provide to agents.
 * Add a constant here to introduce another resource.
 */
public enum ResourceType {
    FOOD,
    HOUSING;

    public String label() {
        String lower = name().toLowerCase();
        return Character.toUpperCase(lower.charAt(0)) + lower.substring(1);
    }
}
