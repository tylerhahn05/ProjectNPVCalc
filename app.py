"""NPV Studio — an interactive capital budgeting dashboard built with Streamlit."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------
# 1. Page setup and visual design
# ------------------------------------------------------------
st.set_page_config(
    page_title="NPV Studio | Project Valuation",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at 88% 0%, #182c46 0%, #0d1727 38%, #090f1a 85%);
        color: #e8eef8;
    }
    [data-testid="stHeader"] {background: transparent;}
    .block-container {max-width: 1260px; padding-top: 2.3rem; padding-bottom: 3rem;}
    h1, h2, h3, p {color: #e8eef8;}
    .eyebrow {color: #65e3c1; letter-spacing: .18em; font-size: .74rem; font-weight: 750;}
    .subtitle {color: #99abc1; font-size: 1.03rem; margin: -.4rem 0 1.3rem;}
    .section-title {color: #eef4ff; font-size: 1.03rem; font-weight: 720; margin: .15rem 0 .55rem;}
    .muted {color: #91a4bb; font-size: .88rem;}
    .npv-card {
        border: 1px solid #30445d; border-radius: 19px;
        padding: 1.55rem 1.7rem; margin: .25rem 0 1.2rem;
        background: linear-gradient(135deg, #172a40, #111e30);
    }
    .npv-card.negative {border-color: #805263; background: linear-gradient(135deg, #332334, #172135);}
    .npv-card.positive {border-color: #286e66; background: linear-gradient(135deg, #153c3a, #152538);}
    .npv-label {font-size: .8rem; color: #bac8d8; font-weight: 700; letter-spacing: .1em;}
    .npv-value {font-size: clamp(2.2rem, 4.3vw, 3.5rem); font-weight: 790; letter-spacing: -.045em; margin: .35rem 0;}
    .npv-value.negative {color: #fda4af;}
    .npv-value.positive {color: #6ee7b7;}
    .npv-value.neutral {color: #e2e8f0;}
    .status {font-weight: 730; font-size: .88rem; margin-top: .45rem;}
    .status.negative {color: #fda4af;}
    .status.positive {color: #6ee7b7;}
    .status.neutral {color: #e2e8f0;}
    div[data-testid="stVerticalBlockBorderWrapper"] {border-color: #314157;}
    div[data-testid="stMetric"] {border: 1px solid #304056; padding: 1rem; border-radius: 12px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# 2. Finance logic (pure Python, independent of the UI)
# ------------------------------------------------------------
def calculate_npv(initial_cost: float, annual_rate_pct: float, cash_flows: list[float]):
    """Discount each end-of-year cash flow and subtract the time-zero cost."""
    rate = annual_rate_pct / 100.0
    present_values = [
        cash_flow / ((1 + rate) ** year)
        for year, cash_flow in enumerate(cash_flows, start=1)
    ]
    npv = sum(present_values) - initial_cost

    # Start at -initial_cost, then add each year's discounted cash flow.
    cumulative = [-initial_cost]
    for pv in present_values:
        cumulative.append(cumulative[-1] + pv)
    return npv, present_values, cumulative


def money(amount: float) -> str:
    """Display negative amounts as -$1,234.56 instead of $-1,234.56."""
    return f"-${abs(amount):,.2f}" if amount < 0 else f"${amount:,.2f}"


# ------------------------------------------------------------
# 3. Session state: number of years and the Add year button
# ------------------------------------------------------------
MAX_YEARS = 30
if "years" not in st.session_state:
    st.session_state["years"] = 5


def add_year():
    """The callback runs BEFORE Streamlit redraws the year input."""
    st.session_state["years"] = min(st.session_state["years"] + 1, MAX_YEARS)


# ------------------------------------------------------------
# 4. Heading
# ------------------------------------------------------------
st.markdown('<div class="eyebrow">CAPITAL BUDGETING / DECISION TOOLS</div>', unsafe_allow_html=True)
st.title("NPV Studio")
st.markdown(
    '<p class="subtitle">Evaluate a project using discounted cash flows — with a clear investment decision.</p>',
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# 5. Editable inputs
# ------------------------------------------------------------
inputs_column, results_column = st.columns([1.05, 0.95], gap="large")

with inputs_column:
    with st.container(border=True):
        st.markdown('<div class="section-title">Project assumptions</div>', unsafe_allow_html=True)
        a, b = st.columns(2, gap="medium")
        with a:
            initial_cost = st.number_input(
                "Initial investment ($)",
                min_value=0.0,
                value=100000.0,
                step=1000.0,
                format="%.2f",
                help="Enter the project's initial cash outflow as a positive amount.",
            )
        with b:
            discount_rate = st.number_input(
                "Discount rate (%)",
                min_value=0.0,
                max_value=100.0,
                value=10.0,
                step=0.5,
                format="%.2f",
                help="The annual required rate of return, expressed as a percentage.",
            )

        year_col, add_col = st.columns([1.4, 1], vertical_alignment="bottom")
        with year_col:
            years = st.number_input(
                "Number of years",
                min_value=1,
                max_value=MAX_YEARS,
                step=1,
                key="years",
            )
        with add_col:
            st.button(
                "+ Add year",
                on_click=add_year,
                disabled=years >= MAX_YEARS,
                width="stretch",
            )

    with st.container(border=True):
        st.markdown('<div class="section-title">Annual future cash flows</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="muted">Enter the net cash flow received at the end of each year. '
            'Use a negative value for a future net outflow.</div>',
            unsafe_allow_html=True,
        )
        cash_flows = []
        cash_flow_columns = st.columns(2, gap="medium")
        for year in range(1, years + 1):
            # Distinct keys retain inputs across normal app reruns.
            key = f"cash_flow_{year}"
            if key not in st.session_state:
                st.session_state[key] = 20000.0
            with cash_flow_columns[(year - 1) % 2]:
                cash_flow = st.number_input(
                    f"Year {year} cash flow ($)",
                    step=1000.0,
                    format="%.2f",
                    key=key,
                )
                cash_flows.append(cash_flow)

# ------------------------------------------------------------
# 6. Compute the project's NPV and recommendation
# ------------------------------------------------------------
npv, discounted_flows, cumulative_npv = calculate_npv(
    initial_cost, discount_rate, cash_flows
)

# Tolerance avoids classifying tiny floating-point rounding as profit/loss.
if npv > 0.005:
    status, css_status = "POSITIVE NPV · ACCEPT", "positive"
    interpretation = "The project is expected to create value at the required return."
elif npv < -0.005:
    status, css_status = "NEGATIVE NPV · REJECT", "negative"
    interpretation = "The discounted future cash flows do not cover the initial investment."
else:
    status, css_status = "ZERO NPV · BREAK EVEN", "neutral"
    interpretation = "The project approximately earns the required return."

# ------------------------------------------------------------
# 7. Results, headline KPI, and discounted cash-flow chart
# ------------------------------------------------------------
with results_column:
    st.markdown('<div class="section-title">Valuation result</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="npv-card {css_status}">
            <div class="npv-label">NPV OF PROJECT</div>
            <div class="npv-value {css_status}">{money(npv)}</div>
            <div class="status {css_status}">{status}</div>
            <div class="muted" style="margin-top:.5rem">{interpretation}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_a, metric_b = st.columns(2)
    with metric_a:
        st.metric("PV of future cash flows", f"{money(sum(discounted_flows))}")
    with metric_b:
        st.metric("Initial cost", f"{money(initial_cost)}")

    st.markdown('<div class="section-title" style="margin-top:1.4rem">Discounted cash flows by year</div>', unsafe_allow_html=True)
    bar_chart = go.Figure()
    bar_chart.add_trace(
        go.Bar(
            x=[f"Year {year}" for year in range(1, years + 1)],
            y=discounted_flows,
            marker_color=["#53dcc3" if value >= 0 else "#fb7185" for value in discounted_flows],
            marker_line_width=0,
            hovertemplate="%{x}<br>Present value: $%{y:,.2f}<extra></extra>",
        )
    )
    bar_chart.update_layout(
        height=285,
        margin=dict(l=8, r=8, t=14, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#aebed1"),
        showlegend=False,
        xaxis=dict(showgrid=False, linecolor="#405168", tickfont=dict(size=11)),
        yaxis=dict(gridcolor="rgba(150,170,195,.13)", tickprefix="$", tickformat=",.0f"),
    )
    st.plotly_chart(bar_chart, width="stretch", theme=None, config={"displayModeBar": False})

# ------------------------------------------------------------
# 8. Cumulative NPV line chart and calculation breakdown
# ------------------------------------------------------------
st.divider()
st.markdown("### Value creation over time")
st.caption("Starts with the initial investment at Year 0 and adds each year's discounted cash flow.")

line_chart = go.Figure()
line_chart.add_hline(y=0, line_color="#b4c1d1", line_dash="dash", opacity=0.7)
line_chart.add_trace(
    go.Scatter(
        x=list(range(0, years + 1)),
        y=cumulative_npv,
        mode="lines+markers",
        line=dict(color="#75a7ff", width=3),
        marker=dict(size=8, color="#75a7ff"),
        hovertemplate="Year %{x}<br>Cumulative NPV: $%{y:,.2f}<extra></extra>",
    )
)
line_chart.update_layout(
    height=310,
    margin=dict(l=10, r=10, t=10, b=10),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#aebed1"),
    xaxis=dict(title="Year", dtick=1, showgrid=False),
    yaxis=dict(title="Cumulative NPV ($)", tickprefix="$", tickformat=",.0f", gridcolor="rgba(150,170,195,.13)"),
    showlegend=False,
)
st.plotly_chart(line_chart, width="stretch", theme=None, config={"displayModeBar": False})

with st.expander("View step-by-step NPV calculation", expanded=False):
    st.latex(r"NPV = -C_0 + \sum_{t=1}^{N}\frac{CF_t}{(1+r)^t}")
    st.write(f"Initial investment at Year 0: **-{money(initial_cost)}**")
    rows = [
        {
            "Year": year,
            "Cash flow": f"{money(cash_flow)}",
            "Discount factor": f"{1 / (1 + discount_rate / 100) ** year:.6f}",
            "Present value": f"{money(pv)}",
            "Cumulative NPV": f"{money(cumulative_npv[year])}",
        }
        for year, (cash_flow, pv) in enumerate(zip(cash_flows, discounted_flows), start=1)
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.markdown(f"**NPV = {money(sum(discounted_flows))} − {money(initial_cost)} = {money(npv)}**")

st.caption("Assumption: each annual cash flow occurs at year-end. Analysis is based on NPV only; it excludes qualitative and capital-rationing considerations.")
