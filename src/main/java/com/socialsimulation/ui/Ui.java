package com.socialsimulation.ui;

import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.SwingUtilities;
import javax.swing.text.View;
import java.awt.Color;
import java.awt.Container;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.Insets;
import java.awt.RenderingHints;

/** Shared colors, type, and the rounded cards used by the environment window. */
public final class Ui {

    public static final Color CANVAS = new Color(0xF3F0E8);
    public static final Color CARD = Color.WHITE;
    public static final Color INK = new Color(0x1F2933);
    public static final Color MUTED = new Color(0x62635F);
    public static final Color TEAL = new Color(0x0F6E56);
    public static final Color BAR_LOW = new Color(0xE4D3B8);
    public static final Color BAR_HIGH = new Color(0x0F6E56);
    public static final Color SCARCE = new Color(0x9A3412);
    public static final Color ENOUGH = new Color(0x047857);
    public static final Color TRACK = new Color(0xE7E2D8);
    public static final Color LINE = new Color(0xE4DED2);

    private Ui() {
    }

    public static Font title() {
        return new Font(Font.SANS_SERIF, Font.BOLD, 26);
    }

    public static Font section() {
        return new Font(Font.SANS_SERIF, Font.BOLD, 13);
    }

    public static Font body() {
        return new Font(Font.SANS_SERIF, Font.PLAIN, 14);
    }

    public static Font bodyBold() {
        return new Font(Font.SANS_SERIF, Font.BOLD, 14);
    }

    public static Font hint() {
        return new Font(Font.SANS_SERIF, Font.PLAIN, 12);
    }

    public static final class Card extends JPanel {

        public Card() {
            setOpaque(false);
        }

        @Override
        protected void paintComponent(Graphics graphics) {
            Graphics2D g = (Graphics2D) graphics.create();
            g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g.setColor(CARD);
            g.fillRoundRect(0, 0, getWidth() - 1, getHeight() - 1, 18, 18);
            g.setColor(LINE);
            g.drawRoundRect(0, 0, getWidth() - 1, getHeight() - 1, 18, 18);
            g.dispose();
            super.paintComponent(graphics);
        }
    }

    /** A label that wraps inside its parent instead of running past the edge. */
    public static final class WrappingLabel extends JLabel {

        private String message = "";
        private int laidOutWidth = -1;

        public WrappingLabel() {
            setFont(body());
            setForeground(INK);
        }

        public void setMessage(String message) {
            this.message = message == null ? "" : message;
            setText("<html>" + escape(this.message) + "</html>");
        }

        @Override
        public Dimension getPreferredSize() {
            View view = (View) getClientProperty("html");
            Insets insets = getInsets();
            int width = wrapWidth();
            if (view == null) {
                return super.getPreferredSize();
            }
            int textWidth = Math.max(40, width - insets.left - insets.right);
            view.setSize(textWidth, 0);
            int height = (int) Math.ceil(view.getPreferredSpan(View.Y_AXIS));
            return new Dimension(width, Math.max(1, height) + insets.top + insets.bottom);
        }

        @Override
        public Dimension getMaximumSize() {
            return new Dimension(Integer.MAX_VALUE, getPreferredSize().height);
        }

        @Override
        public void setBounds(int x, int y, int width, int height) {
            super.setBounds(x, y, width, height);
            if (width <= 0 || width == laidOutWidth) {
                return;
            }
            laidOutWidth = width;
            int preferredHeight = getPreferredSize().height;
            Container parent = getParent();
            if (parent != null && Math.abs(preferredHeight - height) > 2) {
                SwingUtilities.invokeLater(parent::revalidate);
            }
        }

        private int wrapWidth() {
            if (getWidth() > 40) {
                return getWidth();
            }
            Container parent = getParent();
            if (parent != null && parent.getWidth() > 40) {
                Insets insets = parent.getInsets();
                return Math.max(160, parent.getWidth() - insets.left - insets.right);
            }
            return 320;
        }

        private static String escape(String text) {
            return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
        }
    }
}
