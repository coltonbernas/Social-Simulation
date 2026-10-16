package com.socialsimulation.environment;

/**
 * Sandbox laws that limit debt, wealth concentration, and resource claims.
 */
public final class Rules {

    private final boolean debtAllowed;
    private final double maxWealthShare;
    private final double maxResourceShare;

    /**
     * @param debtAllowed       whether an agent's wealth may fall below zero
     * @param maxWealthShare    largest fraction of total wealth one agent may hold, in (0, 1]
     * @param maxResourceShare  largest fraction of one resource stock one agent may claim, in (0, 1]
     */
    public Rules(boolean debtAllowed, double maxWealthShare, double maxResourceShare) {
        if (!(maxWealthShare > 0 && maxWealthShare <= 1)) {
            throw new IllegalArgumentException("max wealth share must be greater than 0 and at most 1");
        }
        if (!(maxResourceShare > 0 && maxResourceShare <= 1)) {
            throw new IllegalArgumentException("max resource share must be greater than 0 and at most 1");
        }
        this.debtAllowed = debtAllowed;
        this.maxWealthShare = maxWealthShare;
        this.maxResourceShare = maxResourceShare;
    }

    public boolean isDebtAllowed() {
        return debtAllowed;
    }

    public double getMaxWealthShare() {
        return maxWealthShare;
    }

    public double getMaxResourceShare() {
        return maxResourceShare;
    }

    public String describe() {
        String debt = debtAllowed ? "permitted" : "forbidden";
        return "debt " + debt
                + ", max wealth share " + percent(maxWealthShare)
                + ", max resource share " + percent(maxResourceShare);
    }

    private static String percent(double share) {
        return String.format("%.0f%%", share * 100);
    }
}
