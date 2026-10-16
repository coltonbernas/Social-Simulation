package com.socialsimulation.ui;

import com.socialsimulation.agent.Agent;
import com.socialsimulation.environment.Environment;
import com.socialsimulation.environment.EnvironmentParameters;
import com.socialsimulation.environment.ResourceType;
import com.socialsimulation.environment.Rules;
import com.socialsimulation.population.Population;

import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JComponent;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JSlider;
import javax.swing.SwingUtilities;
import javax.swing.UIManager;
import javax.swing.WindowConstants;
import java.awt.BorderLayout;
import java.awt.Component;
import java.awt.Dimension;
import java.awt.GridLayout;
import java.util.EnumMap;
import java.util.IdentityHashMap;
import java.util.Map;

/**
 * Controls for the sandbox on the left, and a live reading of what they do on the right.
 */
public final class EnvironmentStudio {

    private static final int PLACEHOLDER_AGE = 21;

    private final Map<JSlider, JLabel> values = new IdentityHashMap<>();
    private final JSlider agents = slider(1, 40, 12, "Number of agents");
    private final JSlider inequality = slider(0, 100, 75, "Wealth inequality");
    private final JSlider totalWealth = slider(0, 500, 120, "Total wealth");
    private final JSlider wealthCap = slider(1, 100, 40, "Wealth limit");
    private final JSlider resourceCap = slider(1, 100, 50, "Resource claim limit");
    private final JSlider mobility = slider(0, 100, 25, "Social mobility");
    private final JSlider cooperation = slider(0, 200, 50, "Cooperation incentive");
    private final JSlider meetings = slider(0, 50, 15, "Interaction frequency");
    private final JCheckBox debt = new JCheckBox("Allow debt");
    private final JLabel debtValue = valueLabel();
    private final Map<ResourceType, JSlider> resources = new EnumMap<>(ResourceType.class);
    private final Map<ResourceType, ResourceMeter> meters = new EnumMap<>(ResourceType.class);

    private final Ui.WrappingLabel wealthLine = new Ui.WrappingLabel();
    private final Ui.WrappingLabel rulesLine = new Ui.WrappingLabel();
    private final Ui.WrappingLabel mobilityLine = new Ui.WrappingLabel();
    private final Ui.WrappingLabel cooperationLine = new Ui.WrappingLabel();
    private final JLabel giniLabel = new JLabel();
    private final WealthChart chart = new WealthChart();
    private final SandboxFloor floor = new SandboxFloor();

    private boolean adjusting;

    private EnvironmentStudio() {
        for (ResourceType type : ResourceType.values()) {
            resources.put(type, slider(0, 80, 0, type.label()));
            meters.put(type, new ResourceMeter());
        }
        debt.setText("Allow debt");
        debt.setOpaque(false);
        debt.setFont(Ui.body());
        debt.setForeground(Ui.INK);
        debt.getAccessibleContext().setAccessibleName("Allow debt");
        debt.addItemListener(event -> refresh());

        JFrame frame = new JFrame("Social Simulation");
        frame.setDefaultCloseOperation(WindowConstants.EXIT_ON_CLOSE);
        frame.getContentPane().setBackground(Ui.CANVAS);
        frame.getContentPane().setLayout(new BorderLayout());
        frame.getContentPane().add(controls(), BorderLayout.WEST);
        frame.getContentPane().add(preview(), BorderLayout.CENTER);
        frame.setMinimumSize(new Dimension(1080, 760));
        frame.setSize(1240, 880);
        frame.setLocationRelativeTo(null);
        apply(EnvironmentParameters.sample());
        frame.setVisible(true);
    }

    public static void open() {
        SwingUtilities.invokeLater(() -> {
            try {
                UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
            } catch (Exception ignored) {
                // The platform look is optional; the window still works with the default.
            }
            new EnvironmentStudio();
        });
    }

    private JScrollPane controls() {
        JPanel panel = new JPanel() {
            @Override
            public Dimension getPreferredSize() {
                Dimension size = super.getPreferredSize();
                if (getParent() instanceof javax.swing.JViewport viewport && viewport.getWidth() > size.width) {
                    size = new Dimension(viewport.getWidth(), size.height);
                }
                return size;
            }
        };
        panel.setLayout(new BoxLayout(panel, BoxLayout.Y_AXIS));
        panel.setOpaque(false);
        panel.setAlignmentX(Component.LEFT_ALIGNMENT);
        panel.setBorder(javax.swing.BorderFactory.createEmptyBorder(20, 22, 24, 16));
        pin(panel, title("Environment"));
        pin(panel, hint("Each control is one rule of the sandbox. The right side shows what it does, and the agents walk it."));
        pin(panel, section("Starting points"));
        pin(panel, presets());
        pin(panel, section("Who is here"));
        pin(panel, control("Agents", "How many agents share this sandbox.", agents, values.get(agents)));
        pin(panel, section("Wealth"));
        pin(panel, control("Total wealth", "The pool that gets split across the agents.", totalWealth, values.get(totalWealth)));
        pin(panel, control("Inequality", "0 is an even split. 1 gives everything to one agent, unless a limit stops that.", inequality, values.get(inequality)));
        pin(panel, section("Rules"));
        pin(panel, debtControl());
        pin(panel, control("Wealth limit", "The largest share of all wealth one agent may hold.", wealthCap, values.get(wealthCap)));
        pin(panel, control("Resource claim", "The largest share of one resource pile one agent may take.", resourceCap, values.get(resourceCap)));
        pin(panel, section("Movement and cooperation"));
        pin(panel, control("Social mobility", "How much of the gap to a richer place an agent can close in one step.", mobility, values.get(mobility)));
        pin(panel, control("Cooperation", "Extra payoff when agents cooperate. 50% turns a reward of 100 into 150.", cooperation, values.get(cooperation)));
        pin(panel, control("Meetings", "How many meetings each agent starts per step.", meetings, values.get(meetings)));
        pin(panel, section("Resources"));
        for (ResourceType type : ResourceType.values()) {
            String hint = "One unit of " + type.label().toLowerCase() + " covers one agent.";
            pin(panel, control(type.label(), hint, resources.get(type), values.get(resources.get(type))));
        }
        JScrollPane scroll = new JScrollPane(panel);
        scroll.setBorder(null);
        scroll.setPreferredSize(new Dimension(430, 700));
        scroll.getViewport().setBackground(Ui.CANVAS);
        scroll.setHorizontalScrollBarPolicy(JScrollPane.HORIZONTAL_SCROLLBAR_NEVER);
        scroll.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_ALWAYS);
        scroll.getVerticalScrollBar().setUnitIncrement(16);
        return scroll;
    }

    private JPanel preview() {
        JPanel panel = new JPanel(new BorderLayout(0, 12));
        panel.setOpaque(false);
        panel.setBorder(javax.swing.BorderFactory.createEmptyBorder(20, 8, 20, 22));

        Ui.Card story = card();
        story.setLayout(new BoxLayout(story, BoxLayout.Y_AXIS));
        JLabel heading = new JLabel("What this sandbox does");
        heading.setFont(Ui.section());
        heading.setForeground(Ui.TEAL);
        heading.setAlignmentX(Component.LEFT_ALIGNMENT);
        story.add(heading);
        story.add(Box.createVerticalStrut(8));
        for (Ui.WrappingLabel line : new Ui.WrappingLabel[]{wealthLine, rulesLine, mobilityLine, cooperationLine}) {
            line.setAlignmentX(Component.LEFT_ALIGNMENT);
            story.add(line);
            story.add(Box.createVerticalStrut(8));
        }

        Ui.Card wealthCard = card();
        wealthCard.setLayout(new BorderLayout(0, 8));
        JPanel wealthHeader = new JPanel(new BorderLayout());
        wealthHeader.setOpaque(false);
        JLabel wealthTitle = new JLabel("Starting wealth");
        wealthTitle.setFont(Ui.section());
        wealthTitle.setForeground(Ui.INK);
        giniLabel.setFont(Ui.bodyBold());
        giniLabel.setForeground(Ui.TEAL);
        wealthHeader.add(wealthTitle, BorderLayout.WEST);
        wealthHeader.add(giniLabel, BorderLayout.EAST);
        wealthCard.add(wealthHeader, BorderLayout.NORTH);
        wealthCard.add(chart, BorderLayout.CENTER);

        Ui.Card floorCard = card();
        floorCard.setLayout(new BorderLayout());
        JLabel floorTitle = new JLabel("Walking around");
        floorTitle.setFont(Ui.section());
        floorTitle.setForeground(Ui.INK);
        floorTitle.setBorder(javax.swing.BorderFactory.createEmptyBorder(0, 0, 8, 0));
        floorCard.add(floorTitle, BorderLayout.NORTH);
        floorCard.add(floor, BorderLayout.CENTER);

        JPanel visuals = new JPanel(new GridLayout(1, 2, 12, 0));
        visuals.setOpaque(false);
        visuals.add(floorCard);
        visuals.add(wealthCard);

        Ui.Card resourceCard = card();
        resourceCard.setLayout(new BorderLayout(0, 8));
        JLabel resourceTitle = new JLabel("Food and housing");
        resourceTitle.setFont(Ui.section());
        resourceTitle.setForeground(Ui.INK);
        resourceCard.add(resourceTitle, BorderLayout.NORTH);
        JPanel meterRow = new JPanel(new GridLayout(1, ResourceType.values().length, 18, 0));
        meterRow.setOpaque(false);
        for (ResourceType type : ResourceType.values()) {
            meterRow.add(meters.get(type));
        }
        resourceCard.add(meterRow, BorderLayout.CENTER);

        panel.add(story, BorderLayout.NORTH);
        panel.add(visuals, BorderLayout.CENTER);
        panel.add(resourceCard, BorderLayout.SOUTH);
        return panel;
    }

    private JPanel presets() {
        JPanel panel = new JPanel(new GridLayout(2, 2, 8, 8));
        panel.setOpaque(false);
        panel.setAlignmentX(Component.LEFT_ALIGNMENT);
        panel.add(preset("Even wealth", "Everyone starts with the same amount, and movement stays open.", this::evenWealth));
        panel.add(preset("Stuck ranks", "Wealth is very unequal and mobility is closed.", this::stuckRanks));
        panel.add(preset("Scarce food", "There is not enough food for every agent.", this::scarceFood));
        panel.add(preset("Sample", "High inequality, held back by a 40% wealth limit.", () -> apply(EnvironmentParameters.sample())));
        panel.setMaximumSize(new Dimension(Integer.MAX_VALUE, panel.getPreferredSize().height));
        return panel;
    }

    private void evenWealth() {
        apply(EnvironmentParameters.builder()
                .numberOfAgents(12)
                .wealthInequality(0)
                .totalWealth(12_000)
                .rules(new Rules(false, 1, 1))
                .socialMobility(0.60)
                .cooperationIncentive(0.25)
                .interactionFrequency(1)
                .resource(ResourceType.FOOD, 18)
                .resource(ResourceType.HOUSING, 18)
                .build());
    }

    private void stuckRanks() {
        apply(EnvironmentParameters.builder()
                .numberOfAgents(12)
                .wealthInequality(0.90)
                .totalWealth(12_000)
                .rules(new Rules(false, 1, 0.50))
                .socialMobility(0)
                .cooperationIncentive(0)
                .interactionFrequency(0.5)
                .resource(ResourceType.FOOD, 12)
                .resource(ResourceType.HOUSING, 12)
                .build());
    }

    private void scarceFood() {
        apply(EnvironmentParameters.builder()
                .numberOfAgents(12)
                .wealthInequality(0.45)
                .totalWealth(8_000)
                .rules(new Rules(false, 0.50, 0.40))
                .socialMobility(0.30)
                .cooperationIncentive(0.80)
                .interactionFrequency(2)
                .resource(ResourceType.FOOD, 5)
                .resource(ResourceType.HOUSING, 16)
                .build());
    }

    private void apply(EnvironmentParameters parameters) {
        adjusting = true;
        agents.setValue(parameters.getNumberOfAgents());
        inequality.setValue((int) Math.round(parameters.getWealthInequality() * 100));
        totalWealth.setValue((int) Math.round(parameters.getTotalWealth() / 100.0));
        syncWealthCapFloor();
        wealthCap.setValue((int) Math.round(parameters.getRules().getMaxWealthShare() * 100));
        resourceCap.setValue((int) Math.round(parameters.getRules().getMaxResourceShare() * 100));
        mobility.setValue((int) Math.round(parameters.getSocialMobility() * 100));
        cooperation.setValue((int) Math.round(parameters.getCooperationIncentive() * 100));
        meetings.setValue((int) Math.round(parameters.getInteractionFrequency() * 10));
        debt.setSelected(parameters.getRules().isDebtAllowed());
        for (ResourceType type : ResourceType.values()) {
            resources.get(type).setValue((int) Math.round(parameters.getResource(type)));
        }
        adjusting = false;
        refresh();
    }

    private void refresh() {
        if (adjusting) {
            return;
        }
        adjusting = true;
        syncWealthCapFloor();
        adjusting = false;

        Environment environment = new Environment(readParameters());
        Population population = populationFrom(environment);
        double[] wealth = new double[population.getSize()];
        int index = 0;
        for (Agent agent : population.getAgents()) {
            wealth[index++] = agent.getWealth();
        }

        EnvironmentParameters parameters = environment.getParameters();
        double cap = parameters.getRules().getMaxWealthShare() < 1 && parameters.getTotalWealth() > 0
                ? parameters.getRules().getMaxWealthShare() * parameters.getTotalWealth()
                : Double.NaN;
        chart.show(wealth, cap);
        floor.show(
                population.getAgents(),
                parameters.getInteractionFrequency(),
                environment.isScarce(ResourceType.FOOD),
                environment.isScarce(ResourceType.HOUSING));
        giniLabel.setText("Gini " + String.format("%.2f", environment.getRealizedGini()));

        double claimShare = parameters.getRules().getMaxResourceShare();
        for (ResourceType type : ResourceType.values()) {
            meters.get(type).show(type.label(), environment.getResource(type), environment.getNumberOfAgents(), claimShare);
        }

        wealthLine.setMessage(wealthSentence(environment, wealth));
        rulesLine.setMessage(rulesSentence(parameters));
        mobilityLine.setMessage(mobilitySentence(environment, wealth));
        cooperationLine.setMessage(cooperationSentence(environment));
        updateValueLabels();
    }

    private EnvironmentParameters readParameters() {
        EnvironmentParameters.Builder builder = EnvironmentParameters.builder()
                .numberOfAgents(agents.getValue())
                .wealthInequality(inequality.getValue() / 100.0)
                .totalWealth(totalWealth.getValue() * 100.0)
                .rules(new Rules(debt.isSelected(), wealthCap.getValue() / 100.0, resourceCap.getValue() / 100.0))
                .socialMobility(mobility.getValue() / 100.0)
                .cooperationIncentive(cooperation.getValue() / 100.0)
                .interactionFrequency(meetings.getValue() / 10.0);
        for (ResourceType type : ResourceType.values()) {
            builder.resource(type, resources.get(type).getValue());
        }
        return builder.build();
    }

    private void syncWealthCapFloor() {
        int minimum = (int) Math.ceil(100.0 / agents.getValue());
        wealthCap.setMinimum(minimum);
        if (wealthCap.getValue() < minimum) {
            wealthCap.setValue(minimum);
        }
    }

    private void updateValueLabels() {
        values.get(agents).setText(Integer.toString(agents.getValue()));
        values.get(inequality).setText(String.format("%.2f", inequality.getValue() / 100.0));
        values.get(totalWealth).setText(String.format("%,d", totalWealth.getValue() * 100));
        values.get(wealthCap).setText(wealthCap.getValue() + "%");
        values.get(resourceCap).setText(resourceCap.getValue() + "%");
        values.get(mobility).setText(mobility.getValue() + "%");
        values.get(cooperation).setText("+" + cooperation.getValue() + "%");
        values.get(meetings).setText(compact(meetings.getValue() / 10.0));
        for (ResourceType type : ResourceType.values()) {
            JSlider slider = resources.get(type);
            values.get(slider).setText(Integer.toString(slider.getValue()));
        }
        debtValue.setText(debt.isSelected() ? "Allowed" : "Blocked");
    }

    private static Population populationFrom(Environment environment) {
        Population population = new Population();
        double[] wealth = environment.getStartingWealth();
        for (int i = 0; i < environment.getNumberOfAgents(); i++) {
            population.addAgent(new Agent(i + 1, "Agent " + (i + 1), PLACEHOLDER_AGE, wealth[i]));
        }
        return population;
    }

    private static String wealthSentence(Environment environment, double[] wealth) {
        int count = environment.getNumberOfAgents();
        double total = environment.getParameters().getTotalWealth();
        String people = count == 1 ? "1 agent" : count + " agents";
        if (total == 0) {
            return people + " start with no wealth.";
        }
        double target = environment.getParameters().getWealthInequality();
        double realized = environment.getRealizedGini();
        if (realized < 0.02) {
            return people + " share " + money(total) + " evenly, " + money(total / count) + " each. The Gini is 0.00.";
        }
        String spread = people + " share " + money(total) + ". The poorest starts with " + money(wealth[0])
                + " and the richest with " + money(wealth[wealth.length - 1])
                + ". The Gini is " + String.format("%.2f", realized) + ".";
        if (target - realized > 0.03) {
            spread += " The setting was " + String.format("%.2f", target)
                    + ", and the wealth limit pulls the spread down.";
        }
        return spread;
    }

    private static String rulesSentence(EnvironmentParameters parameters) {
        Rules rules = parameters.getRules();
        String debtText = rules.isDebtAllowed()
                ? "Wealth may fall below zero."
                : "Wealth stays at zero or above.";
        String wealthLimit = rules.getMaxWealthShare() >= 1
                ? "An agent may hold the whole wealth pool."
                : "An agent may hold at most " + percent(rules.getMaxWealthShare()) + " of the wealth.";
        String resourceLimit = rules.getMaxResourceShare() >= 1
                ? "An agent may take a whole resource pile."
                : "An agent may take at most " + percent(rules.getMaxResourceShare()) + " of a resource pile.";
        return debtText + " " + wealthLimit + " " + resourceLimit;
    }

    private static String mobilitySentence(Environment environment, double[] wealth) {
        int rate = (int) Math.round(environment.getParameters().getSocialMobility() * 100);
        if (wealth.length < 2) {
            return "With one agent, there is no richer place to move toward.";
        }
        double current = wealth[(wealth.length - 1) / 2];
        double opportunity = wealth[wealth.length - 1];
        if (opportunity - current < 0.5) {
            return "Wealth is already even, so mobility has no gap to close.";
        }
        if (rate == 0) {
            return "Mobility is closed. An agent offered " + money(opportunity) + " stays at " + money(current) + ".";
        }
        double next = environment.projectWealth(current, opportunity);
        return "Mobility is " + rate + "%. The middle agent has " + money(current)
                + " and can reach " + money(next) + " in one step toward " + money(opportunity) + ".";
    }

    private static String cooperationSentence(Environment environment) {
        int bonus = (int) Math.round(environment.getParameters().getCooperationIncentive() * 100);
        double payoff = environment.cooperativePayoff(100);
        String reward = bonus == 0
                ? "Cooperation adds no extra payoff, so a reward of 100 stays 100."
                : "Cooperation adds " + bonus + "%, so a reward of 100 pays " + money(payoff) + ".";
        double frequency = environment.getParameters().getInteractionFrequency();
        double expected = environment.expectedInteractionsPerStep();
        String meeting = frequency == 0
                ? "Agents do not start meetings."
                : "Each agent starts " + meetings(frequency) + " per step, "
                + compact(expected) + " across the population.";
        return reward + " " + meeting;
    }

    private JPanel debtControl() {
        JPanel panel = column();
        JPanel header = new JPanel(new BorderLayout());
        header.setOpaque(false);
        header.add(debt, BorderLayout.WEST);
        header.add(debtValue, BorderLayout.EAST);
        JLabel hintLabel = hint("Turn this on to let wealth fall below zero.");
        hintLabel.setBorder(javax.swing.BorderFactory.createEmptyBorder(0, 0, 12, 0));
        panel.add(header);
        panel.add(hintLabel);
        stretch(header);
        stretch(hintLabel);
        stretch(panel);
        return panel;
    }

    private JPanel control(String title, String hint, JComponent editor, JLabel value) {
        JPanel panel = column();
        JPanel header = new JPanel(new BorderLayout());
        header.setOpaque(false);
        JLabel titleLabel = new JLabel(title);
        titleLabel.setFont(Ui.bodyBold());
        titleLabel.setForeground(Ui.INK);
        header.add(titleLabel, BorderLayout.WEST);
        header.add(value, BorderLayout.EAST);
        JLabel hintLabel = hint(hint);
        hintLabel.setBorder(javax.swing.BorderFactory.createEmptyBorder(0, 0, 12, 0));
        panel.add(header);
        panel.add(editor);
        panel.add(hintLabel);
        stretch(header);
        stretch(editor);
        stretch(hintLabel);
        stretch(panel);
        return panel;
    }

    private JSlider slider(int min, int max, int value, String accessibleName) {
        JSlider slider = new JSlider(min, max, value);
        slider.setOpaque(false);
        slider.getAccessibleContext().setAccessibleName(accessibleName);
        slider.addChangeListener(event -> refresh());
        JLabel valueLabel = valueLabel();
        values.put(slider, valueLabel);
        return slider;
    }

    private static JLabel valueLabel() {
        JLabel label = new JLabel(" ");
        label.setFont(Ui.bodyBold());
        label.setForeground(Ui.TEAL);
        return label;
    }

    private static JButton preset(String name, String tooltip, Runnable action) {
        JButton button = new JButton(name);
        button.setFont(Ui.hint());
        button.setToolTipText(tooltip);
        button.getAccessibleContext().setAccessibleName(name);
        button.addActionListener(event -> action.run());
        return button;
    }

    private static JLabel title(String text) {
        JLabel label = new JLabel(text);
        label.setFont(Ui.title());
        label.setForeground(Ui.INK);
        label.setAlignmentX(Component.LEFT_ALIGNMENT);
        label.setBorder(javax.swing.BorderFactory.createEmptyBorder(0, 0, 4, 0));
        return label;
    }

    private static JLabel section(String text) {
        JLabel label = new JLabel(text.toUpperCase());
        label.setFont(Ui.section());
        label.setForeground(Ui.TEAL);
        label.setAlignmentX(Component.LEFT_ALIGNMENT);
        label.setBorder(javax.swing.BorderFactory.createEmptyBorder(10, 0, 8, 0));
        return label;
    }

    private static JLabel hint(String text) {
        Ui.WrappingLabel label = new Ui.WrappingLabel();
        label.setFont(Ui.hint());
        label.setForeground(Ui.MUTED);
        label.setMessage(text);
        label.setAlignmentX(Component.LEFT_ALIGNMENT);
        return label;
    }

    private static String meetings(double frequency) {
        if (Math.abs(frequency - 1) < 0.05) {
            return "1 meeting";
        }
        return compact(frequency) + " meetings";
    }

    private static Ui.Card card() {
        Ui.Card card = new Ui.Card();
        card.setBorder(javax.swing.BorderFactory.createEmptyBorder(16, 16, 16, 16));
        return card;
    }

    private static JPanel column() {
        JPanel panel = new JPanel();
        panel.setLayout(new BoxLayout(panel, BoxLayout.Y_AXIS));
        panel.setOpaque(false);
        panel.setAlignmentX(Component.LEFT_ALIGNMENT);
        return panel;
    }

    private static void pin(JPanel parent, JComponent child) {
        stretch(child);
        parent.add(child);
    }

    private static void stretch(JComponent component) {
        component.setAlignmentX(Component.LEFT_ALIGNMENT);
        Dimension preferred = component.getPreferredSize();
        component.setMaximumSize(new Dimension(Integer.MAX_VALUE, Math.max(preferred.height, 1)));
    }

    private static String money(double value) {
        if (Math.abs(value - Math.rint(value)) < 0.05) {
            return String.format("%,.0f", value);
        }
        return String.format("%,.2f", value);
    }

    private static String compact(double value) {
        if (Math.abs(value - Math.rint(value)) < 0.05) {
            return String.format("%.0f", value);
        }
        return String.format("%.1f", value);
    }

    private static String percent(double share) {
        return String.format("%.0f%%", share * 100);
    }
}
