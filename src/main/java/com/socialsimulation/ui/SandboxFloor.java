package com.socialsimulation.ui;

import com.socialsimulation.agent.Agent;

import javax.swing.JPanel;
import javax.swing.Timer;
import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Dimension;
import java.awt.FontMetrics;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.awt.geom.Ellipse2D;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * The floor of the sandbox. Agents walk, pair up when meetings are allowed,
 * and gather at a resource that does not cover everyone.
 */
public final class SandboxFloor extends JPanel {

    private enum Mode {
        WANDER,
        SEEK,
        TALK
    }

    private static final double FOOD_X = 0.22;
    private static final double FOOD_Y = 0.62;
    private static final double HOUSING_X = 0.78;
    private static final double HOUSING_Y = 0.62;
    private static final double WANDER_SPEED = 0.008;
    private static final double SEEK_SPEED = 0.014;

    private final List<Walker> walkers = new ArrayList<>();
    private final Random random = new Random();
    private final Timer timer = new Timer(32, event -> step());

    private double meetingsPerAgent;
    private boolean foodScarce;
    private boolean housingScarce;

    public SandboxFloor() {
        setOpaque(false);
        setPreferredSize(new Dimension(420, 300));
        setToolTipText("");
        addMouseMotionListener(new MouseAdapter() {
            @Override
            public void mouseMoved(MouseEvent event) {
                Walker walker = walkerAt(event.getX(), event.getY());
                if (walker == null) {
                    setToolTipText(null);
                    return;
                }
                setToolTipText("Agent " + walker.id + " · wealth " + money(walker.wealth));
            }
        });
    }

    public void show(List<Agent> agents, double meetingsPerAgent, boolean foodScarce, boolean housingScarce) {
        this.meetingsPerAgent = Math.max(0, meetingsPerAgent);
        this.foodScarce = foodScarce;
        this.housingScarce = housingScarce;
        int count = agents == null ? 0 : agents.size();
        while (walkers.size() > count) {
            walkers.remove(walkers.size() - 1);
        }
        while (walkers.size() < count) {
            walkers.add(newWalker());
        }
        for (int i = 0; i < count; i++) {
            Agent agent = agents.get(i);
            Walker walker = walkers.get(i);
            walker.id = agent.getId();
            walker.wealth = agent.getWealth();
        }
        for (int i = 0; i < walkers.size(); i++) {
            Walker walker = walkers.get(i);
            int partner = walker.partner;
            if (partner < 0 || partner >= walkers.size() || walkers.get(partner).partner != i) {
                walker.partner = -1;
                walker.mode = Mode.WANDER;
                walker.talkTicks = 0;
            }
        }
        repaint();
    }

    @Override
    public void addNotify() {
        super.addNotify();
        if (!timer.isRunning()) {
            timer.start();
        }
    }

    @Override
    public void removeNotify() {
        timer.stop();
        super.removeNotify();
    }

    private void step() {
        if (walkers.isEmpty() || getWidth() <= 0) {
            return;
        }
        for (Walker walker : walkers) {
            move(walker);
        }
        startMeetings();
        repaint();
    }

    private void move(Walker walker) {
        if (walker.mode == Mode.TALK) {
            walker.talkTicks--;
            if (walker.talkTicks <= 0) {
                release(walker);
            }
            return;
        }
        if (walker.mode == Mode.SEEK) {
            Walker partner = partnerOf(walker);
            if (partner == null) {
                release(walker);
                return;
            }
            walker.targetX = clamp((walker.x + partner.x) / 2);
            walker.targetY = clamp((walker.y + partner.y) / 2);
            stepToward(walker, SEEK_SPEED);
            if (distance(walker, partner) < 0.075) {
                walker.mode = Mode.TALK;
                walker.talkTicks = 55;
                partner.mode = Mode.TALK;
                partner.talkTicks = 55;
            }
            return;
        }
        if (distanceToTarget(walker) < 0.03) {
            chooseTarget(walker);
        }
        stepToward(walker, WANDER_SPEED);
    }

    private void startMeetings() {
        if (meetingsPerAgent <= 0 || walkers.size() < 2) {
            return;
        }
        double chance = Math.min(0.15, meetingsPerAgent / 60.0);
        for (int i = 0; i < walkers.size(); i++) {
            Walker walker = walkers.get(i);
            if (walker.mode != Mode.WANDER || random.nextDouble() > chance) {
                continue;
            }
            int partnerIndex = idlePartner(i);
            if (partnerIndex < 0) {
                return;
            }
            walker.mode = Mode.SEEK;
            walker.partner = partnerIndex;
            Walker partner = walkers.get(partnerIndex);
            partner.mode = Mode.SEEK;
            partner.partner = i;
        }
    }

    private int idlePartner(int self) {
        int choices = 0;
        int picked = -1;
        for (int i = 0; i < walkers.size(); i++) {
            if (i != self && walkers.get(i).mode == Mode.WANDER) {
                choices++;
                if (random.nextInt(choices) == 0) {
                    picked = i;
                }
            }
        }
        return picked;
    }

    private void chooseTarget(Walker walker) {
        double roll = random.nextDouble();
        if (foodScarce && roll < (housingScarce ? 0.42 : 0.62)) {
            walker.targetX = clamp(FOOD_X + (random.nextDouble() - 0.5) * 0.16);
            walker.targetY = clamp(FOOD_Y + (random.nextDouble() - 0.5) * 0.16);
            return;
        }
        if (housingScarce && roll < 0.75) {
            walker.targetX = clamp(HOUSING_X + (random.nextDouble() - 0.5) * 0.16);
            walker.targetY = clamp(HOUSING_Y + (random.nextDouble() - 0.5) * 0.16);
            return;
        }
        walker.targetX = 0.08 + random.nextDouble() * 0.84;
        walker.targetY = 0.1 + random.nextDouble() * 0.72;
    }

    private void stepToward(Walker walker, double speed) {
        double dx = walker.targetX - walker.x;
        double dy = walker.targetY - walker.y;
        double remaining = Math.hypot(dx, dy);
        if (remaining < 0.0001) {
            return;
        }
        double step = Math.min(speed, remaining);
        walker.x += dx / remaining * step;
        walker.y += dy / remaining * step;
    }

    private void release(Walker walker) {
        Walker partner = partnerOf(walker);
        walker.partner = -1;
        walker.mode = Mode.WANDER;
        walker.talkTicks = 0;
        chooseTarget(walker);
        if (partner != null) {
            partner.partner = -1;
            partner.mode = Mode.WANDER;
            partner.talkTicks = 0;
            chooseTarget(partner);
        }
    }

    private Walker newWalker() {
        Walker walker = new Walker();
        walker.x = 0.12 + random.nextDouble() * 0.76;
        walker.y = 0.12 + random.nextDouble() * 0.6;
        chooseTarget(walker);
        return walker;
    }

    private Walker partnerOf(Walker walker) {
        if (walker.partner < 0 || walker.partner >= walkers.size()) {
            return null;
        }
        return walkers.get(walker.partner);
    }

    @Override
    protected void paintComponent(Graphics graphics) {
        super.paintComponent(graphics);
        Graphics2D g = (Graphics2D) graphics.create();
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);

        int left = 4;
        int top = 4;
        int width = Math.max(1, getWidth() - 8);
        int height = Math.max(1, getHeight() - 28);
        g.setColor(new Color(0xF7F4EE));
        g.fillRoundRect(left, top, width, height, 16, 16);

        drawPlace(g, left, top, width, height, FOOD_X, FOOD_Y, "Food", foodScarce);
        drawPlace(g, left, top, width, height, HOUSING_X, HOUSING_Y, "Housing", housingScarce);
        drawMeetings(g, left, top, width, height);
        drawWalkers(g, left, top, width, height);

        g.setFont(Ui.hint());
        g.setColor(Ui.MUTED);
        String caption = meetingsPerAgent <= 0
                ? "Meetings are off, so agents only wander."
                : "Bigger dots are richer. Lines are meetings.";
        g.drawString(caption, 4, getHeight() - 8);
        g.dispose();
    }

    private void drawPlace(Graphics2D g, int left, int top, int width, int height,
                           double nx, double ny, String name, boolean scarce) {
        int x = left + (int) Math.round(nx * width);
        int y = top + (int) Math.round(ny * height);
        Color tone = scarce ? Ui.SCARCE : Ui.ENOUGH;
        g.setColor(new Color(tone.getRed(), tone.getGreen(), tone.getBlue(), scarce ? 70 : 40));
        g.fillOval(x - 30, y - 30, 60, 60);
        g.setColor(tone);
        g.fillOval(x - 6, y - 6, 12, 12);
        g.setFont(Ui.hint());
        FontMetrics metrics = g.getFontMetrics();
        int labelWidth = metrics.stringWidth(name);
        g.drawString(name, x - labelWidth / 2, y + 22);
    }

    private void drawMeetings(Graphics2D g, int left, int top, int width, int height) {
        g.setStroke(new BasicStroke(2f));
        for (Walker walker : walkers) {
            if (walker.partner <= indexOf(walker) || walker.mode == Mode.WANDER) {
                continue;
            }
            Walker partner = partnerOf(walker);
            if (partner == null) {
                continue;
            }
            int x1 = left + (int) Math.round(walker.x * width);
            int y1 = top + (int) Math.round(walker.y * height);
            int x2 = left + (int) Math.round(partner.x * width);
            int y2 = top + (int) Math.round(partner.y * height);
            int alpha = walker.mode == Mode.TALK ? 180 : 90;
            g.setColor(new Color(Ui.TEAL.getRed(), Ui.TEAL.getGreen(), Ui.TEAL.getBlue(), alpha));
            g.drawLine(x1, y1, x2, y2);
        }
    }

    private void drawWalkers(Graphics2D g, int left, int top, int width, int height) {
        double peak = 0;
        for (Walker walker : walkers) {
            peak = Math.max(peak, walker.wealth);
        }
        for (int i = 0; i < walkers.size(); i++) {
            Walker walker = walkers.get(i);
            float mix = walkers.size() == 1 ? 1f : i / (float) (walkers.size() - 1);
            double scale = peak <= 0 ? 0.45 : walker.wealth / peak;
            int radius = 7 + (int) Math.round(8 * scale);
            int x = left + (int) Math.round(walker.x * width);
            int y = top + (int) Math.round(walker.y * height);
            g.setColor(new Color(0, 0, 0, 28));
            g.fillOval(x - radius + 1, y - radius + 2, radius * 2, radius * 2);
            g.setColor(mix(Ui.BAR_LOW, Ui.BAR_HIGH, mix));
            g.fillOval(x - radius, y - radius, radius * 2, radius * 2);
            if (walkers.size() <= 18 && radius >= 10) {
                String label = Integer.toString(walker.id);
                g.setFont(Ui.hint());
                FontMetrics metrics = g.getFontMetrics();
                g.setColor(mix > 0.55f ? Color.WHITE : Ui.INK);
                g.drawString(label, x - metrics.stringWidth(label) / 2, y + metrics.getAscent() / 2 - 1);
            }
        }
    }

    private Walker walkerAt(int x, int y) {
        double peak = 0;
        for (Walker walker : walkers) {
            peak = Math.max(peak, walker.wealth);
        }
        int left = 4;
        int top = 4;
        int width = Math.max(1, getWidth() - 8);
        int height = Math.max(1, getHeight() - 28);
        for (int i = walkers.size() - 1; i >= 0; i--) {
            Walker walker = walkers.get(i);
            double scale = peak <= 0 ? 0.45 : walker.wealth / peak;
            int radius = 7 + (int) Math.round(8 * scale);
            int cx = left + (int) Math.round(walker.x * width);
            int cy = top + (int) Math.round(walker.y * height);
            if (new Ellipse2D.Double(cx - radius, cy - radius, radius * 2, radius * 2).contains(x, y)) {
                return walker;
            }
        }
        return null;
    }

    private int indexOf(Walker walker) {
        return walkers.indexOf(walker);
    }

    private static double distance(Walker a, Walker b) {
        return Math.hypot(a.x - b.x, a.y - b.y);
    }

    private static double distanceToTarget(Walker walker) {
        return Math.hypot(walker.targetX - walker.x, walker.targetY - walker.y);
    }

    private static double clamp(double value) {
        return Math.max(0.06, Math.min(0.94, value));
    }

    private static Color mix(Color low, Color high, float amount) {
        float t = Math.max(0f, Math.min(1f, amount));
        return new Color(
                Math.round(low.getRed() + (high.getRed() - low.getRed()) * t),
                Math.round(low.getGreen() + (high.getGreen() - low.getGreen()) * t),
                Math.round(low.getBlue() + (high.getBlue() - low.getBlue()) * t));
    }

    private static String money(double value) {
        if (Math.abs(value - Math.rint(value)) < 0.05) {
            return String.format("%,.0f", value);
        }
        return String.format("%,.2f", value);
    }

    private static final class Walker {
        private int id;
        private double wealth;
        private double x;
        private double y;
        private double targetX;
        private double targetY;
        private int partner = -1;
        private Mode mode = Mode.WANDER;
        private int talkTicks;
    }
}
