package com.socialsimulation.ui;

import javax.swing.JPanel;
import java.awt.Dimension;
import java.awt.FontMetrics;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;

/** Shows whether one resource covers every agent. */
public final class ResourceMeter extends JPanel {

    private String name = "";
    private double units;
    private int agents = 1;
    private double maxShare = 1;

    public ResourceMeter() {
        setOpaque(false);
        setPreferredSize(new Dimension(220, 92));
    }

    public void show(String name, double units, int agents, double maxShare) {
        this.name = name;
        this.units = units;
        this.agents = Math.max(agents, 1);
        this.maxShare = maxShare;
        repaint();
    }

    @Override
    protected void paintComponent(Graphics graphics) {
        super.paintComponent(graphics);
        Graphics2D g = (Graphics2D) graphics.create();
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);

        boolean scarce = units < agents;
        String status = scarce ? "Not enough" : "Enough";
        g.setFont(Ui.bodyBold());
        g.setColor(Ui.INK);
        g.drawString(name, 0, 18);

        g.setFont(Ui.hint());
        FontMetrics metrics = g.getFontMetrics();
        int statusWidth = metrics.stringWidth(status);
        g.setColor(scarce ? Ui.SCARCE : Ui.ENOUGH);
        g.drawString(status, getWidth() - statusWidth, 18);

        int barY = 30;
        int barHeight = 10;
        g.setColor(Ui.TRACK);
        g.fillRoundRect(0, barY, getWidth(), barHeight, 8, 8);
        double coverage = Math.min(1, units / agents);
        int fill = (int) Math.round(getWidth() * coverage);
        if (units > 0 && fill < 6) {
            fill = 6;
        }
        g.setColor(scarce ? Ui.SCARCE : Ui.ENOUGH);
        g.fillRoundRect(0, barY, Math.min(getWidth(), fill), barHeight, 8, 8);

        g.setColor(Ui.MUTED);
        g.drawString(compact(units) + " units · " + compact(units / agents) + " each", 0, 60);
        g.drawString("One agent may take " + compact(units * maxShare), 0, 78);
        g.dispose();
    }

    private static String compact(double value) {
        if (Math.abs(value - Math.rint(value)) < 0.05) {
            return String.format("%.0f", value);
        }
        return String.format("%.1f", value);
    }
}
