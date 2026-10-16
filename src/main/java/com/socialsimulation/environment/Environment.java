package com.socialsimulation.environment;

import java.util.Arrays;

/**
 * The isolated sandbox agents act inside. Parameters stay fixed; starting wealth
 * is derived from the inequality target and then clipped by the wealth rule.
 */
public final class Environment {

    private final EnvironmentParameters parameters;
    private final double[] startingWealth;

    public Environment(EnvironmentParameters parameters) {
        if (parameters == null) {
            throw new IllegalArgumentException("parameters are required");
        }
        this.parameters = parameters;
        this.startingWealth = distributeWealth(parameters);
    }

    public EnvironmentParameters getParameters() {
        return parameters;
    }

    public int getNumberOfAgents() {
        return parameters.getNumberOfAgents();
    }

    /** Starting wealth from poorest to richest. */
    public double[] getStartingWealth() {
        return startingWealth.clone();
    }

    public double getRealizedGini() {
        return gini(startingWealth);
    }

    public double getResource(ResourceType type) {
        return parameters.getResource(type);
    }

    /** Units of a resource available for each agent. */
    public double perCapita(ResourceType type) {
        return getResource(type) / getNumberOfAgents();
    }

    /** True when there is less than one unit of the resource per agent. */
    public boolean isScarce(ResourceType type) {
        return getResource(type) < getNumberOfAgents();
    }

    /**
     * Wealth after one step of mobility toward {@code opportunityWealth}.
     * The result stays inside the debt and wealth-share rules.
     */
    public double projectWealth(double currentWealth, double opportunityWealth) {
        if (!Double.isFinite(currentWealth) || !Double.isFinite(opportunityWealth)) {
            throw new IllegalArgumentException("wealth values must be finite");
        }
        Rules rules = parameters.getRules();
        if (!rules.isDebtAllowed() && (currentWealth < 0 || opportunityWealth < 0)) {
            throw new IllegalArgumentException("debt is not allowed");
        }

        double next = currentWealth + parameters.getSocialMobility() * (opportunityWealth - currentWealth);
        if (!rules.isDebtAllowed() && next < 0) {
            next = 0;
        }
        if (parameters.getTotalWealth() > 0 && rules.getMaxWealthShare() < 1) {
            double cap = rules.getMaxWealthShare() * parameters.getTotalWealth();
            if (next > cap) {
                next = cap;
            }
        }
        return next;
    }

    /** Reward after the cooperation incentive is applied. */
    public double cooperativePayoff(double baseReward) {
        if (!(baseReward >= 0)) {
            throw new IllegalArgumentException("base reward must be at least 0");
        }
        return baseReward * (1.0 + parameters.getCooperationIncentive());
    }

    /** Whether one agent may take {@code amount} of a resource under the claim cap and current stock. */
    public boolean canClaim(ResourceType type, double amount) {
        if (!(amount >= 0)) {
            return false;
        }
        double stock = getResource(type);
        if (amount > stock) {
            return false;
        }
        double cap = parameters.getRules().getMaxResourceShare() * stock;
        return amount <= cap + 1e-9;
    }

    public double expectedInteractionsPerStep() {
        return getNumberOfAgents() * parameters.getInteractionFrequency();
    }

    public String summary() {
        StringBuilder text = new StringBuilder();
        text.append("Environment\n");
        text.append("  Agents: ").append(getNumberOfAgents()).append('\n');
        text.append("  Wealth inequality (target Gini): ")
                .append(format(parameters.getWealthInequality())).append('\n');
        text.append("  Realized Gini: ").append(format(getRealizedGini())).append('\n');
        text.append("  Total wealth: ").append(format(parameters.getTotalWealth())).append('\n');
        text.append("  Social mobility: ").append(format(parameters.getSocialMobility())).append('\n');
        text.append("  Cooperation incentive: ")
                .append(format(parameters.getCooperationIncentive())).append('\n');
        text.append("  Interaction frequency: ")
                .append(format(parameters.getInteractionFrequency()))
                .append(" per agent per step (")
                .append(format(expectedInteractionsPerStep()))
                .append(" expected interactions per step)\n");
        text.append("  Rules: ").append(parameters.getRules().describe()).append('\n');
        text.append("  Resources:\n");
        for (ResourceType type : ResourceType.values()) {
            String supply = isScarce(type) ? "scarce" : "sufficient";
            text.append("    ").append(type.label())
                    .append(": ").append(format(getResource(type)))
                    .append(" (").append(format(perCapita(type)))
                    .append(" per agent, ").append(supply).append(")\n");
        }
        text.append("  Starting wealth, poorest to richest:\n");
        for (int i = 0; i < startingWealth.length; i++) {
            text.append("    ").append(i + 1).append(": ").append(format(startingWealth[i])).append('\n');
        }
        if (startingWealth.length > 1) {
            double current = startingWealth[(startingWealth.length - 1) / 2];
            double opportunity = startingWealth[startingWealth.length - 1];
            text.append("  Mobility example: median wealth ")
                    .append(format(current))
                    .append(" can reach ")
                    .append(format(projectWealth(current, opportunity)))
                    .append(" in one step toward ")
                    .append(format(opportunity))
                    .append('\n');
        }
        text.append("  Cooperation example: a base reward of 100.00 pays ")
                .append(format(cooperativePayoff(100)))
                .append(" when agents cooperate\n");
        return text.toString();
    }

    /**
     * Split total wealth with Lorenz curve {@code L(p) = p^k}, where
     * {@code k = (1 + g) / (1 - g)} and {@code g} is the target Gini.
     * A wealth-share cap then redistributes anything above the legal maximum.
     */
    private static double[] distributeWealth(EnvironmentParameters parameters) {
        int agentCount = parameters.getNumberOfAgents();
        double totalWealth = parameters.getTotalWealth();
        double inequality = parameters.getWealthInequality();
        double[] wealth = new double[agentCount];
        if (totalWealth == 0) {
            return wealth;
        }
        if (inequality >= 1.0) {
            wealth[agentCount - 1] = totalWealth;
        } else {
            double exponent = (1.0 + inequality) / (1.0 - inequality);
            double allocated = 0;
            for (int i = 0; i < agentCount - 1; i++) {
                double upper = (i + 1.0) / agentCount;
                double lower = i / (double) agentCount;
                double share = Math.pow(upper, exponent) - Math.pow(lower, exponent);
                wealth[i] = totalWealth * share;
                allocated += wealth[i];
            }
            wealth[agentCount - 1] = totalWealth - allocated;
        }
        enforceWealthCap(wealth, parameters.getRules().getMaxWealthShare());
        Arrays.sort(wealth);
        return wealth;
    }

    private static void enforceWealthCap(double[] wealth, double maxShare) {
        if (maxShare >= 1.0) {
            return;
        }
        double total = 0;
        for (double value : wealth) {
            total += value;
        }
        if (total == 0) {
            return;
        }
        double cap = maxShare * total;
        for (int pass = 0; pass < wealth.length; pass++) {
            double surplus = 0;
            int recipients = 0;
            for (double value : wealth) {
                if (value > cap) {
                    surplus += value - cap;
                } else if (value < cap) {
                    recipients++;
                }
            }
            if (surplus <= 1e-8 * Math.max(1.0, total)) {
                return;
            }
            if (recipients == 0) {
                throw new IllegalArgumentException(
                        "max wealth share " + maxShare + " cannot be satisfied across " + wealth.length + " agents");
            }
            double gift = surplus / recipients;
            for (int i = 0; i < wealth.length; i++) {
                if (wealth[i] > cap) {
                    wealth[i] = cap;
                } else if (wealth[i] < cap) {
                    wealth[i] += gift;
                }
            }
        }
    }

    /** Gini of wealth sorted from poorest to richest. */
    private static double gini(double[] wealth) {
        int count = wealth.length;
        if (count == 0) {
            return 0;
        }
        double sum = 0;
        double weighted = 0;
        for (int i = 0; i < count; i++) {
            sum += wealth[i];
            weighted += (i + 1.0) * wealth[i];
        }
        if (sum == 0) {
            return 0;
        }
        return (2.0 * weighted) / (count * sum) - (count + 1.0) / count;
    }

    private static String format(double value) {
        return String.format("%.2f", value);
    }
}
