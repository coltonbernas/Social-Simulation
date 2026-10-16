package com.socialsimulation.environment;

import java.util.Collections;
import java.util.EnumMap;
import java.util.Map;

/**
 * Immutable settings for one sandbox.
 * <p>
 * Wealth inequality is a target Gini coefficient: 0 spreads wealth evenly and 1
 * gives all of it to a single agent. Social mobility is the fraction of the gap
 * to a new wealth level that an agent can close in one step. The cooperation
 * incentive is the extra fraction added to a reward when agents cooperate.
 * Interaction frequency is the average number of interactions each agent
 * initiates per step. Resource amounts are total units available; one unit
 * covers one agent.
 */
public final class EnvironmentParameters {

    private final int numberOfAgents;
    private final double wealthInequality;
    private final double totalWealth;
    private final Rules rules;
    private final double socialMobility;
    private final double cooperationIncentive;
    private final double interactionFrequency;
    private final Map<ResourceType, Double> resources;

    private EnvironmentParameters(
            int numberOfAgents,
            double wealthInequality,
            double totalWealth,
            Rules rules,
            double socialMobility,
            double cooperationIncentive,
            double interactionFrequency,
            Map<ResourceType, Double> resources) {
        this.numberOfAgents = numberOfAgents;
        this.wealthInequality = wealthInequality;
        this.totalWealth = totalWealth;
        this.rules = rules;
        this.socialMobility = socialMobility;
        this.cooperationIncentive = cooperationIncentive;
        this.interactionFrequency = interactionFrequency;
        this.resources = resources;
    }

    public static Builder builder() {
        return new Builder();
    }

    /** The sandbox shown when the app opens. */
    public static EnvironmentParameters sample() {
        return builder()
                .numberOfAgents(12)
                .wealthInequality(0.75)
                .totalWealth(12_000)
                .rules(new Rules(false, 0.40, 0.50))
                .socialMobility(0.25)
                .cooperationIncentive(0.50)
                .interactionFrequency(1.5)
                .resource(ResourceType.FOOD, 10)
                .resource(ResourceType.HOUSING, 14)
                .build();
    }

    public int getNumberOfAgents() {
        return numberOfAgents;
    }

    public double getWealthInequality() {
        return wealthInequality;
    }

    public double getTotalWealth() {
        return totalWealth;
    }

    public Rules getRules() {
        return rules;
    }

    public double getSocialMobility() {
        return socialMobility;
    }

    public double getCooperationIncentive() {
        return cooperationIncentive;
    }

    public double getInteractionFrequency() {
        return interactionFrequency;
    }

    public double getResource(ResourceType type) {
        if (type == null) {
            throw new IllegalArgumentException("resource type is required");
        }
        return resources.get(type);
    }

    public Map<ResourceType, Double> getResources() {
        return resources;
    }

    public static final class Builder {

        private Integer numberOfAgents;
        private Double wealthInequality;
        private Double totalWealth;
        private Rules rules;
        private Double socialMobility;
        private Double cooperationIncentive;
        private Double interactionFrequency;
        private final EnumMap<ResourceType, Double> resources = new EnumMap<>(ResourceType.class);

        private Builder() {
            for (ResourceType type : ResourceType.values()) {
                resources.put(type, 0.0);
            }
        }

        public Builder numberOfAgents(int numberOfAgents) {
            if (numberOfAgents < 1) {
                throw new IllegalArgumentException("number of agents must be at least 1");
            }
            this.numberOfAgents = numberOfAgents;
            return this;
        }

        public Builder wealthInequality(double wealthInequality) {
            requireUnitInterval(wealthInequality, "wealth inequality");
            this.wealthInequality = wealthInequality;
            return this;
        }

        public Builder totalWealth(double totalWealth) {
            requireNonNegative(totalWealth, "total wealth");
            this.totalWealth = totalWealth;
            return this;
        }

        public Builder rules(Rules rules) {
            if (rules == null) {
                throw new IllegalArgumentException("rules are required");
            }
            this.rules = rules;
            return this;
        }

        public Builder socialMobility(double socialMobility) {
            requireUnitInterval(socialMobility, "social mobility");
            this.socialMobility = socialMobility;
            return this;
        }

        public Builder cooperationIncentive(double cooperationIncentive) {
            requireNonNegative(cooperationIncentive, "cooperation incentive");
            this.cooperationIncentive = cooperationIncentive;
            return this;
        }

        public Builder interactionFrequency(double interactionFrequency) {
            requireNonNegative(interactionFrequency, "interaction frequency");
            this.interactionFrequency = interactionFrequency;
            return this;
        }

        public Builder resource(ResourceType type, double amount) {
            if (type == null) {
                throw new IllegalArgumentException("resource type is required");
            }
            requireNonNegative(amount, type.label() + " availability");
            resources.put(type, amount);
            return this;
        }

        public EnvironmentParameters build() {
            requireSet(numberOfAgents, "number of agents");
            requireSet(wealthInequality, "wealth inequality");
            requireSet(totalWealth, "total wealth");
            requireSet(rules, "rules");
            requireSet(socialMobility, "social mobility");
            requireSet(cooperationIncentive, "cooperation incentive");
            requireSet(interactionFrequency, "interaction frequency");

            double minimumShare = 1.0 / numberOfAgents;
            if (rules.getMaxWealthShare() + 1e-9 < minimumShare) {
                throw new IllegalArgumentException(
                        "max wealth share " + rules.getMaxWealthShare()
                                + " is too low for " + numberOfAgents + " agents");
            }

            Map<ResourceType, Double> stored = Collections.unmodifiableMap(new EnumMap<>(resources));
            return new EnvironmentParameters(
                    numberOfAgents,
                    wealthInequality,
                    totalWealth,
                    rules,
                    socialMobility,
                    cooperationIncentive,
                    interactionFrequency,
                    stored);
        }

        private static void requireSet(Object value, String name) {
            if (value == null) {
                throw new IllegalArgumentException(name + " is required");
            }
        }

        private static void requireUnitInterval(double value, String name) {
            if (!(value >= 0 && value <= 1)) {
                throw new IllegalArgumentException(name + " must be between 0 and 1");
            }
        }

        private static void requireNonNegative(double value, String name) {
            if (!(value >= 0)) {
                throw new IllegalArgumentException(name + " must be at least 0");
            }
        }
    }
}
