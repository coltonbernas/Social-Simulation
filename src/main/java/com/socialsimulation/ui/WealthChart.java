package com.socialsimulation.ui;

import javax.swing.JPanel;
import java.awt.Color;
import java.awt.Dimension;
import java.awt.FontMetrics;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.Rectangle;
import java.awt.RenderingHints;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.util.ArrayList;
import java.util.List;

/** One bar per agent, poorest on the left. */
public final class WealthChart extends JPanel {

    private double[] wealth = new double[0];
    private double cap = Double.NaN;
    private final List<Rectangle> bars = new ArrayList<>();

    public WealthChart() {
        setOpaque(false);
        setPreferredSize(new Dimension(480, 260));
        setToolTipText("");
        addMouseMotionListener(new MouseAdapter() {
            @Override
            public void mouseMoved(MouseEvent event) {
                int index = indexAt(event.getX(), event.getY());
                if (index < 0) {
                    setToolTipText(null);
                    return;
                }
                setToolTipText("Agent " + (index + 1) + " starts with " + money(wealth[index]));
            }
        });
    }

    public void show(double[] wealth, double cap) {
        this.wealth = wealth == null ? new double[0] : wealth.clone();
        this.cap = cap;
        repaint();
    }

    @Override
    protected void paintComponent(Graphics graphics) {
        super.paintComponent(graphics);
        Graphics2D g = (Graphics2D) graphics.create();
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
        bars.clear();

        int left = 8;
        int right = getWidth() - 8;
        int top = 22;
        int bottom = getHeight() - 28;
        if (right <= left || bottom <= top) {
            g.dispose();
            return;
        }

        g.setFont(Ui.hint());
        g.setColor(Ui.MUTED);
        g.drawString("Each bar is one agent. Poorest on the left.", left, getHeight() - 8);

        if (wealth.length == 0) {
            g.dispose();
            return;
        }

        double peak = 0;
        for (double value : wealth) {
            peak = Math.max(peak, value);
        }
        if (peak <= 0) {
            g.drawString("No wealth to split yet.", left, top + 16);
            g.dispose();
            return;
        }

        FontMetrics metrics = g.getFontMetrics();
        String low = money(wealth[0]);
        String high = money(wealth[wealth.length - 1]);
        boolean atCap = !Double.isNaN(cap) && Math.abs(wealth[wealth.length - 1] - cap) <= Math.max(0.5, cap * 0.001);
        String tag = atCap ? "at cap" : "";
        int tagWidth = tag.isEmpty() ? 0 : metrics.stringWidth(tag) + 8;
        g.drawString(low, left, 14);
        g.drawString(high, right - metrics.stringWidth(high) - tagWidth, 14);
        if (atCap) {
            g.setColor(Ui.SCARCE);
            g.drawString(tag, right - metrics.stringWidth(tag), 14);
        }

        int gap = wealth.length > 24 ? 2 : 4;
        int plotWidth = right - left;
        int barWidth = Math.max(2, (plotWidth - gap * (wealth.length - 1)) / wealth.length);
        int used = wealth.length * barWidth + gap * (wealth.length - 1);
        int x = left + Math.max(0, (plotWidth - used) / 2);
        int plotHeight = bottom - top;

        for (int i = 0; i < wealth.length; i++) {
            int barHeight = (int) Math.round(plotHeight * (wealth[i] / peak));
            if (wealth[i] > 0) {
                barHeight = Math.max(barHeight, 3);
            }
            int y = bottom - barHeight;
            float mix = wealth.length == 1 ? 1f : i / (float) (wealth.length - 1);
            g.setColor(mix(Ui.BAR_LOW, Ui.BAR_HIGH, mix));
            g.fillRoundRect(x, y, barWidth, barHeight, 6, 6);
            bars.add(new Rectangle(x, top, barWidth, bottom - top));
            x += barWidth + gap;
        }
        g.dispose();
    }

    private int indexAt(int x, int y) {
        for (int i = 0; i < bars.size(); i++) {
            if (bars.get(i).contains(x, y)) {
                return i;
            }
        }
        return -1;
    }

    private static String money(double value) {
        if (Math.abs(value - Math.rint(value)) < 0.05) {
            return String.format("%,.0f", value);
        }
        return String.format("%,.2f", value);
    }

    private static Color mix(Color low, Color high, float amount) {
        float t = Math.max(0f, Math.min(1f, amount));
        return new Color(
                blend(low.getRed(), high.getRed(), t),
                blend(low.getGreen(), high.getGreen(), t),
                blend(low.getBlue(), high.getBlue(), t));
    }

    private static int blend(int from, int to, float amount) {
        return Math.round(from + (to - from) * amount);
    }
}
