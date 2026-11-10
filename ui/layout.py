"""Layout and navigation components for InsightOS.

Sidebar navigation with four pages. Tracks the current page in
st.session_state. Provides all shared CSS for the colorful SaaS analytics look.
"""

import os

import streamlit as st

PAGES = [
    "Upload Data",
    "Dashboard",
    "AI Analyst",
    "What-If Simulator",
]

PAGE_ICONS = {
    "Upload Data": "\U0001F4C2",
    "Dashboard": "\U0001F4CA",
    "AI Analyst": "\U0001F916",
    "What-If Simulator": "\U0001F527",
}

# Per-KPI color identities for cards and charts.
KPI_COLORS = {
    "Revenue": "#6366F1",      # indigo
    "Profit": "#22C55E",       # green
    "Orders": "#22D3EE",       # cyan
    "Growth": "#F59E0B",       # amber
    "Margin": "#A855F7",       # violet
    "Avg Order Value": "#EC4899",  # pink
    "Customers": "#14B8A6",    # teal
}

# Shared CSS block injected once on every page. Defines the full design
# system as CSS variables so it can be edited in one place.
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --ink-bg: #0B0F1A;
  --ink-surface: rgba(18, 24, 38, 0.7);
  --ink-border: rgba(99, 102, 241, 0.25);
  --ink-accent-start: #6366F1;
  --ink-accent-end: #22D3EE;
  --ink-positive: #22C55E;
  --ink-negative: #EF4444;
  --ink-muted: #94A3B8;
  --ink-text: #F8FAFC;
  --ink-radius: 14px;
}

/* ---- Background: layered dark gradient with soft colored glows ---- */
.stApp {
  background:
    radial-gradient(circle at 15% 20%, rgba(99, 102, 241, 0.15), transparent 40%),
    radial-gradient(circle at 85% 30%, rgba(168, 85, 247, 0.12), transparent 40%),
    radial-gradient(circle at 50% 80%, rgba(34, 211, 238, 0.10), transparent 40%),
    #0B0F1A;
  background-attachment: fixed;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  color: var(--ink-text);
}

/* ---- TASK 1: Do NOT hide the whole header. Keep sidebar expand/collapse controls visible. */
header[data-testid="stHeader"] {
  background: transparent !important;
  border-bottom: none !important;
}
header[data-testid="stHeader"] * {
  visibility: hidden !important;
}
/* Reveal only the sidebar expand/collapse controls in the top-left */
button[data-testid="stSidebarCollapsedControl"],
button[data-testid="stExpandSidebarButton"],
button[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stExpandSidebarButton"] {
  visibility: visible !important;
  background: var(--ink-accent-start) !important;
  border: none !important;
  border-radius: 8px !important;
  width: 34px !important;
  height: 34px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  margin-left: 0.5rem !important;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.4) !important;
}
/* Make the icon inside the expand/collapse button visible */
button[data-testid="stSidebarCollapsedControl"] *,
button[data-testid="stExpandSidebarButton"] *,
button[data-testid="stSidebarCollapseButton"] *,
[data-testid="collapsedControl"] *,
[data-testid="stSidebarCollapseButton"] *,
[data-testid="stExpandSidebarButton"] * {
  visibility: visible !important;
  color: var(--ink-bg) !important;
  font-size: 16px !important;
  font-weight: 700 !important;
}

/* Hide Streamlit chrome that isn't the sidebar control */
footer { display: none !important; }
#MainMenu { display: none !important; }
.stDeployButton { display: none !important; }
.stAppDeployButton { display: none !important; }

/* ---- Base page ---- */
.block-container {
  padding-top: 1rem;
  padding-bottom: 3rem;
  max-width: 1280px;
}

/* Hide the default Streamlit title decoration on pages that render their own */
h1.st-emotion-cache-1avyp0d, h1.e1t0n5z0 { display: none; }

/* Muted text */
.text-muted { color: var(--ink-muted) !important; font-size: 0.875rem; }

/* ---- Hero header (Upload page) - large gradient banner ---- */
.hero-banner {
  height: 250px;
  border-radius: var(--ink-radius);
  background:
    linear-gradient(135deg, #6366F1 0%, #A855F7 45%, #22D3EE 100%);
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  margin-bottom: 2rem;
  animation: heroFadeIn 1.1s ease-out both;
}
.hero-banner::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 25% 30%, rgba(255,255,255,0.18), transparent 45%),
    radial-gradient(circle at 75% 70%, rgba(168, 85, 247, 0.15), transparent 45%);
}
.hero-banner::after {
  content: "";
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(255,255,255,0.04) 1px, transparent 1px);
  background-size: 20px 20px;
  opacity: 0.35;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.9rem;
  border-radius: 999px;
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.25);
  color: #FFFFFF;
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: 1rem;
  backdrop-filter: blur(8px);
}
.hero-title {
  margin: 0 0 0.6rem 0;
  font-size: 60px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #FFFFFF;
  line-height: 1.05;
  text-shadow: 0 2px 12px rgba(99, 102, 241, 0.35);
}
.hero-tagline {
  margin: 0 0 1.4rem 0;
  font-size: 20px;
  font-weight: 500;
  color: rgba(255,255,255,0.85);
  line-height: 1.4;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}
.hero-pills {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
}
.hero-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.28rem 0.8rem;
  border-radius: 999px;
  background: rgba(255,255,255,0.10);
  border: 1px solid rgba(255,255,255,0.20);
  color: #FFFFFF;
  font-size: 0.8rem;
  font-weight: 500;
  backdrop-filter: blur(6px);
}
.hero-pill .pill-icon {
  font-size: 0.85rem;
}

/* Fade-in animation */
@keyframes heroFadeIn {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ---- Page header (other pages) - smaller, left-aligned gradient ---- */
.page-header {
  padding: 0.85rem 0 0.6rem 0;
  margin-bottom: 1.5rem;
  border-radius: var(--ink-radius);
  background: linear-gradient(135deg, #6366F1 0%, #A855F7 45%, #22D3EE 100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.page-header h1 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #FFFFFF;
  line-height: 1.1;
}
.page-header .tagline {
  color: rgba(255,255,255,0.85);
  font-size: 0.95rem;
  margin-top: 0.25rem;
}
.page-header .status {
  color: rgba(255,255,255,0.7);
  font-size: 0.8rem;
  font-weight: 500;
  margin-top: 0.5rem;
}

/* ---- Responsive ---- */
@media (max-width: 640px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; }
  .features-row { flex-direction: column; gap: 1rem; }
  .hero-banner { height: auto; padding: 2rem 1rem; }
  .hero-title { font-size: 36px; }
  .hero-tagline { font-size: 18px; }
  .hero-pills { gap: 0.4rem; }
  .hero-pill { font-size: 0.75rem; padding: 0.25rem 0.7rem; }
  .page-header { padding: 0.7rem 0; }
  .page-header h1 { font-size: 1.5rem; }
}</style>
"""


def render_css() -> None:
    """Inject the shared CSS block into the page."""
    st.markdown(_CSS, unsafe_allow_html=True)


def render_hero_header() -> None:
    """Render the hero header for the Upload page with gradient banner."""
    st.markdown(
        '<div class="hero-banner">'
        '<div class="hero-badge">AI Business Intelligence Platform</div>'
        '<h1 class="hero-title">\u269B\uFE0F InsightOS</h1>'
        '<div class="hero-tagline">Turn raw business data into decisions.</div>'
        '<div class="hero-pills">'
        '<div class="hero-pill"><span class="pill-icon">\U0001F4C2</span>Upload</div>'
        '<div class="hero-pill"><span class="pill-icon">\U0001F4CA</span>Explore</div>'
        '<div class="hero-pill"><span class="pill-icon">\U0001F916</span>Decide</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_header(rows: int = 0, date_range: str = "") -> None:
    """Render the app header with name, tagline, and optional status line.

    Args:
        rows: Number of data rows loaded (0 if none).
        date_range: Human-readable date range string (empty if none).
    """
    status_html = ""
    if rows > 0 and date_range:
        status_html = (
            f'<div class="status">\U0001F4C6 {rows:,} rows loaded  \u2022  {date_range}</div>'
        )
    st.markdown(
        '<div class="page-header">'
        '<h1>\u269B\uFE0F InsightOS</h1>'
        '<div class="tagline">Turn raw business data into decisions.</div>'
        f'{status_html}'
        '</div>',
        unsafe_allow_html=True,
    )


def render_feature_cards() -> None:
    """Render the 3 feature cards (Upload, Explore, Decide) on the upload page."""
    st.markdown('<div class="features-row">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            '<div class="feature-card feature-upload">'
            '<div class="icon">\U0001F4C2</div>'
            '<h4>Upload</h4>'
            '<p>Bring in your sales data via CSV or Excel.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            '<div class="feature-card feature-explore">'
            '<div class="icon">\U0001F4CA</div>'
            '<h4>Explore</h4>'
            '<p>KPIs, charts, filters, and what-if simulation.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            '<div class="feature-card feature-decide">'
            '<div class="icon">\U0001F916</div>'
            '<h4>Decide</h4>'
            '<p>Ask the AI Analyst questions about your business.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)


def render_kpi_card(label: str, value: str, delta: str | None = None, kpi_type: str = "revenue") -> None:
    """Render a styled SaaS KPI card with per-KPI color identity.

    Args:
        label: KPI label shown above the value.
        value: Main KPI value (formatted string).
        delta: Optional delta string like "+12.5%" or "-5.0%".
        kpi_type: One of revenue, profit, orders, growth, margin, avg_order_value, customers.
    """
    delta_html = ""
    if delta:
        kind = "positive" if delta.startswith("+") else ("negative" if delta.startswith("-") else "neutral")
        delta_html = f'<div class="delta-pill {kind}">{delta}</div>'
    css_class = kpi_type.lower().replace(" ", "-")
    st.markdown(
        f'<div class="metric-card {css_class}">'
        f'<div class="accent-line"></div>'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        f'{delta_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_empty_state(title: str, message: str) -> None:
    """Render a friendly empty-state block.

    Args:
        title: Large heading text.
        message: Explanatory body text.
    """
    st.markdown(
        f'<div class="empty-state">'
        f'<h2>{title}</h2>'
        f'<p>{message}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_sidebar() -> str:
    """Render the sidebar navigation and return the selected page.

    The current page is tracked in st.session_state["current_page"].

    Returns:
        The name of the currently selected page.
    """
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-wordmark">'
            '<span class="glyph">\U0001F4CA</span>'
            '<h2>InsightOS</h2>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sidebar-nav-label">Navigate</div>', unsafe_allow_html=True)

        # Inject dynamic CSS to highlight the active nav button with a gradient pill.
        active_index = PAGES.index(st.session_state.get("current_page", PAGES[0]))
        # Sidebar elements before buttons: wordmark(1) + nav-label(1) = 2, so button offset is +3 (1-based nth-child).
        button_nth = active_index + 3
        st.markdown(
            f'<style>'
            f'section[data-testid="stSidebar"] button:nth-of-type({button_nth}) {{'
            f'  background: linear-gradient(135deg, var(--ink-accent-start), var(--ink-accent-end)) !important;'
            f'  color: var(--ink-bg) !important;'
            f'  border: none !important;'
            f'  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4) !important;'
            f'}}'
            f'</style>',
            unsafe_allow_html=True,
        )

        for page in PAGES:
            icon = PAGE_ICONS.get(page, "")
            label = f"{icon} {page}"
            if st.button(label, key=f"nav_{page}", use_container_width=True):
                st.session_state.current_page = page

        st.markdown(
            '<div class="sidebar-about">'
            "InsightOS v1.0  \n\n"
            "AI Business Intelligence Platform  \n\n"
            "<a href='https://github.com/romanalirandhawa-a11y/insightos' "
            "target='_blank' rel='noopener'>View on GitHub</a>"
            '</div>',
            unsafe_allow_html=True,
        )

    return st.session_state.current_page
