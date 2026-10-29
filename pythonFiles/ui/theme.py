# ---------------------------------------------------------------- 1. theme
BG, PANEL, CARD, BORDER = "#0b1220", "#111a2e", "#1a263d", "#26344f"
TEXT, MUTED, ACCENT = "#e2e8f0", "#8b9bb4", "#38bdf8"
FONT = "Segoe UI"

# building type -> (fill colour, label)
BUILDINGS = {
    1: ("#f59e0b", "W1"), 2: ("#10b981", "W2"), 3: ("#3b82f6", "SCH"),
    4: ("#ef4444", "GRO"), 5: ("#a855f7", "HOS"), 6: ("#d4a373", "H1"),
    7: ("#f472b6", "H2"),
}
# what an agent is doing -> dot colour
STATUS_COLORS = {
    "Hospitalized": "#c084fc", "Sick": "#f87171", "Hungry": "#fb923c",
    "In school": "#60a5fa", "Employed": "#4ade80", "Unemployed": "#e2e8f0",
}
# log category -> text colour
LOG_COLORS = {
    "jobs": "#fbbf24", "health": "#f87171", "social": "#f472b6",
    "money": "#4ade80", "life": "#38bdf8", "info": "#cbd5e1",
}
# One subtle background tint per region (same order as the regions in config.json).
REGION_TINTS = ("#15294a", "#2a1f4a", "#123b36", "#3b2d17")
MAX_LOG_LINES = 2000