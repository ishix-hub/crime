"""Registered Crime vs Reality - dashboard (crimes against women and SC atrocities, India).
Data: NCRB Crime in India 2023 (Vol I, II), NFHS-6 (2023-24) with NFHS-5 (2019-21) comparison, exploratory survey.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import fisher_exact

st.set_page_config(page_title="Registered Crime vs Reality", layout="wide")
DATA = Path(__file__).parent
BLUE, ORANGE, GREY = "#2E5E8C", "#D9822B", "#8A8A8A"


@st.cache_data
def load():
    df = pd.read_csv(DATA / "state_data.csv")
    geo = json.load(open(DATA / "india_states.geojson"))
    sv = pd.read_csv(DATA / "survey.csv")
    return df, geo, sv


df, geo, sv = load()


def india_map(frame, col, title, scale="YlOrRd", fmt=":.1f"):
    fig = px.choropleth(
        frame, geojson=geo, locations="state", featureidkey="properties.state",
        color=col, color_continuous_scale=scale, hover_name="state",
        hover_data={"state": False, col: fmt},
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=520, title=title,
                      coloraxis_colorbar=dict(title=""))
    return fig


st.title("Registered crime vs reality")
st.caption("Does a high NCRB rate mean more violence, or easier access to police? "
           "And where does the justice process break down? Crimes against women and SC atrocities, India.")
with st.expander("Data sources and how to read this"):
    st.markdown(
        "- **NCRB Crime in India 2023** counts *registered* cases, not true incidence. NCRB itself says states "
        "should not be compared purely on crime figures. Women's rates use projected population; SC rates use the "
        "2011 Census SC population.\n"
        "- **NFHS-6 (2023-24)** gives survey-reported spousal violence (ever-married women 18-49), with NFHS-5 "
        "(2019-21) shown for comparison. Manipur is not in the NFHS-6 file. NFHS-5 and NFHS-6 may not be strictly comparable.\n"
        "- **Funnel stages** are NCRB stock and flow figures (some include earlier years' cases), not a single cohort followed over time.\n"
        "- The survey is a small convenience sample and is exploratory only."
    )

tab1, tab2, tab3, tab4 = st.tabs(
    ["1. Registered vs reality", "2. Where justice breaks", "3. Court backlog simulator", "4. Survey: who would report?"]
)

# ------------------------------------------------------------------ TAB 1
with tab1:
    c0, c1 = st.columns([1, 1])
    survey_round = c0.radio("NFHS round", ["NFHS-6 (2023-24)", "NFHS-5 (2019-21)"], horizontal=True)
    ncol = "spousal_nfhs6" if survey_round.startswith("NFHS-6") else "spousal_nfhs5"
    d = df.copy()
    d["ratio"] = np.where(d[ncol] > 0, d["cruelty_rate_2023"] / d[ncol], np.nan)
    metric = c1.radio(
        "Map shows", ["Registered rate: cruelty by husband/relatives (NCRB 2023)",
                      "Survey prevalence: spousal violence (NFHS)",
                      "Registration-to-survey ratio"], horizontal=False)
    left, right = st.columns([1, 1])
    with left:
        if metric.startswith("Registered"):
            st.plotly_chart(india_map(d, "cruelty_rate_2023", "Registered cases per lakh women (498A)"),
                            width="stretch")
        elif metric.startswith("Survey"):
            st.plotly_chart(india_map(d.dropna(subset=[ncol]), ncol, "Women reporting spousal violence in survey (%)",
                                      scale="Purples"), width="stretch")
        else:
            st.plotly_chart(india_map(d.dropna(subset=["ratio"]), "ratio",
                                      "Registered per lakh women per survey % point (high = registers more than survey implies)",
                                      scale="RdBu_r", fmt=":.2f"), width="stretch")
    with right:
        s = d.dropna(subset=[ncol, "cruelty_rate_2023"]).copy()
        rho = s[["cruelty_rate_2023", ncol]].corr(method="spearman").iloc[0, 1]
        fig = px.scatter(s, x=ncol, y="cruelty_rate_2023", size="w_pop_lakh", hover_name="state",
                         labels={ncol: "Survey: spousal violence (%)", "cruelty_rate_2023": "Registered 498A per lakh women"},
                         size_max=40, color_discrete_sequence=[BLUE])
        label = s[s.state.isin(["Delhi", "Haryana", "Rajasthan", "Telangana", "Bihar", "Tamil Nadu",
                                "Uttar Pradesh", "West Bengal", "Jharkhand", "Kerala"])]
        fig.add_trace(go.Scatter(x=label[ncol], y=label["cruelty_rate_2023"], mode="text", text=label.state,
                                 textposition="top center", showlegend=False, textfont=dict(size=10)))
        fig.update_layout(height=520, margin=dict(l=0, r=0, t=30, b=0),
                          title=f"Registered vs survey-reported (Spearman rho = {rho:.2f}, n = {len(s)})")
        st.plotly_chart(fig, width="stretch")
    st.caption("A weak link between the two means registration is shaped by more than the underlying violence. "
               "Bubble size = women's population.")
    min_pop = st.slider("Rank states with at least this many women (lakh), to avoid tiny-number noise", 0, 150, 30, 10)
    r = d[d.w_pop_lakh >= min_pop].dropna(subset=["ratio"]).sort_values("ratio")
    cols = ["state", "cruelty_rate_2023", ncol, "ratio"]
    names = {"state": "State", "cruelty_rate_2023": "Registered 498A / lakh women", ncol: "Survey %", "ratio": "Ratio"}
    a, b = st.columns(2)
    a.markdown("**Registers far less than the survey implies**")
    a.dataframe(r.head(6)[cols].rename(columns=names).round(2), hide_index=True, width="stretch")
    b.markdown("**Registers far more than the survey implies**")
    b.dataframe(r.tail(6)[cols].iloc[::-1].rename(columns=names).round(2), hide_index=True, width="stretch")

# ------------------------------------------------------------------ TAB 2
with tab2:
    group = st.radio("Group", ["Women (police stage)", "SC atrocities (police and court)"], horizontal=True)
    if group.startswith("Women"):
        l, r_ = st.columns([1, 1])
        with l:
            st.plotly_chart(india_map(df, "w_cs_rate_2023", "Chargesheeting rate, crimes against women, 2023 (%)",
                                      scale="Blues"), width="stretch")
        with r_:
            opts = ["India"] + sorted(df.state.tolist())
            pick = st.selectbox("State", opts, key="wstate")
            row = df.sum(numeric_only=True) if pick == "India" else df[df.state == pick].iloc[0]
            stages = [("Reported in 2023", row.w_reported), ("Cases for investigation", row.w_total_inv),
                      ("Chargesheeted", row.w_chargesheeted), ("Pending investigation at year-end", row.w_pend_inv_end)]
            fig = go.Figure(go.Bar(y=[x for x, _ in stages][::-1], x=[v for _, v in stages][::-1], orientation="h",
                                   marker_color=BLUE, text=[f"{int(v):,}" for _, v in stages][::-1], textposition="outside"))
            fig.update_layout(height=380, margin=dict(l=0, r=40, t=30, b=0), title=f"Police stage: {pick}")
            st.plotly_chart(fig, width="stretch")
        st.markdown("**Court stage is only available nationally for women (NCRB Table 3A.7, 2023):**")
        k1, k2 = st.columns(2)
        k1.metric("Conviction rate, all IPC crimes against women", "19.2%",
                  help="27,479 convicted vs 6,228 discharged and 109,546 acquitted")
        k2.metric("Conviction rate, cruelty by husband or relatives (498A)", "14.6%",
                  help="8,858 convicted vs 2,144 discharged and 49,670 acquitted")
    else:
        l, r_ = st.columns([1, 1])
        with l:
            mm = st.radio("Map shows", ["Conviction rate (% of completed trials)", "Court pendency (% of cases for trial)",
                                        "Chargesheeting rate (%)"], horizontal=False)
            colmap = {"Conviction": "sc_conv_rate", "Court": "sc_court_pend_pct", "Chargesheeting": "sc_cs_rate_2023"}
            col = colmap[mm.split()[0]]
            st.plotly_chart(india_map(df.dropna(subset=[col]), col, mm, scale="Oranges" if "Conviction" not in mm else "Greens"),
                            width="stretch")
            st.caption("States with no SC atrocity cases or no completed trials are left blank.")
        with r_:
            opts = ["India"] + sorted(df[df.sc_2023 > 0].state.tolist())
            pick = st.selectbox("State", opts, key="scstate")
            row = df.sum(numeric_only=True) if pick == "India" else df[df.state == pick].iloc[0]
            stages = [("Registered 2023", row.sc_2023), ("Chargesheeted", row.sc_chargesheeted),
                      ("Cases before court for trial", row.sc_total_trial), ("Trials completed", row.sc_trials_completed),
                      ("Convicted", row.sc_convicted)]
            fig = go.Figure(go.Bar(y=[x for x, _ in stages][::-1], x=[v for _, v in stages][::-1], orientation="h",
                                   marker_color=ORANGE, text=[f"{int(v):,}" for _, v in stages][::-1], textposition="outside"))
            fig.update_layout(height=380, margin=dict(l=0, r=60, t=30, b=0), title=f"SC atrocity cases: {pick}")
            st.plotly_chart(fig, width="stretch")
            if row.sc_total_trial > 0:
                st.caption(f"Convicted = {row.sc_convicted / row.sc_total_trial:.1%} of all cases before the courts; "
                           f"{row.sc_pend_trial_end / row.sc_total_trial:.0%} still pending at year-end.")
        sc = df[df.sc_2023 >= 100]
        fig = px.scatter(sc, x="sc_cs_rate_2023", y="sc_conv_rate", size="sc_2023", hover_name="state", text="state",
                         labels={"sc_cs_rate_2023": "Chargesheeting rate (%)", "sc_conv_rate": "Conviction rate (%)"},
                         color_discrete_sequence=[ORANGE], size_max=35)
        fig.update_traces(textposition="top center", textfont=dict(size=9))
        fig.update_layout(height=450, margin=dict(l=0, r=0, t=40, b=0),
                          title="Police stage vs court stage (states with 100+ cases): good police numbers do not guarantee convictions")
        st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------------ TAB 3
with tab3:
    st.markdown("**What would it take to clear the SC atrocity court backlog?** A simple mechanical projection from NCRB 2023 "
                "figures. It is illustrative, not a forecast.")
    scope_opts = ["India"] + sorted(df[df.sc_total_trial >= 5000].state.tolist())
    scope = st.selectbox("Scope", scope_opts)
    row = df.sum(numeric_only=True) if scope == "India" else df[df.state == scope].iloc[0]
    pending0, inflow0, disposed0 = row.sc_pend_trial_end, row.sc_trial_new, row.sc_court_disposed
    c1, c2, c3 = st.columns(3)
    mult = c1.slider("Court disposal capacity (x today's)", 1.0, 6.0, 1.0, 0.1)
    growth = c2.slider("Change in new cases sent to trial per year (%)", -20, 20, 0, 1)
    years = c3.slider("Years to project", 5, 20, 10)
    base, scen = [pending0], [pending0]
    for t in range(1, years + 1):
        base.append(max(0.0, base[-1] + inflow0 - disposed0))
        scen.append(max(0.0, scen[-1] + inflow0 * (1 + growth / 100) ** t - disposed0 * mult))
    x = list(range(years + 1))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=base, name="Today's pace", line=dict(color=GREY, dash="dash")))
    fig.add_trace(go.Scatter(x=x, y=scen, name="Your scenario", line=dict(color=ORANGE, width=3)))
    fig.update_layout(height=420, xaxis_title="Years from 2023", yaxis_title="Cases pending trial",
                      margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")
    cleared = next((t for t, v in zip(x, scen) if v == 0 and t > 0), None)
    m1, m2, m3 = st.columns(3)
    m1.metric("Pending at end of 2023", f"{int(pending0):,}")
    m2.metric("Break-even capacity", f"{inflow0 / disposed0:.1f}x" if disposed0 else "n/a",
              help="Disposal capacity multiple at which new inflow equals disposals, so the backlog stops growing")
    m3.metric("Backlog cleared in", f"{cleared} years" if cleared else f"not within {years} years")
    st.caption(f"At today's pace the courts disposed of about {int(disposed0):,} cases against {int(inflow0):,} new cases sent to trial "
               "in 2023. Disposals include acquittals, convictions and other disposals, so faster disposal is not the same as more convictions.")

# ------------------------------------------------------------------ TAB 4
with tab4:
    n = len(sv)
    st.markdown(f"**Exploratory survey, n = {n}** (convenience sample; two randomly alternated versions of the same story). "
                "Respondents rated how likely 'Meena' is to go to the police when the abuser is **her husband (A)** or **a male neighbour (B)**. "
                "This measures *perceived* likelihood, not actual reporting.")
    sv["form_label"] = sv.form.map({"A": "A: husband", "B": "B: male neighbour"})
    sh = sv.groupby("form_label").q1_likely.mean().mul(100).reset_index()
    ct = pd.crosstab(sv.form, sv.q1_likely).reindex(index=["A", "B"], columns=[True, False], fill_value=0)
    p = fisher_exact(ct.values)[1]
    a, b = st.columns(2)
    fig = px.bar(sh, x="form_label", y="q1_likely", text=sh.q1_likely.round(0).astype(int).astype(str) + "%",
                 labels={"form_label": "", "q1_likely": "% saying likely / very likely to report"},
                 color="form_label", color_discrete_sequence=[ORANGE, BLUE])
    fig.update_layout(showlegend=False, height=380, yaxis_range=[0, 100], margin=dict(l=0, r=0, t=40, b=0),
                      title=f"Would she report? (Fisher exact p = {p:.3f})")
    a.plotly_chart(fig, width="stretch")
    bar = pd.crosstab(sv.q2_main_barrier, sv.form_label, normalize="columns").mul(100).round(0).reset_index().melt(
        id_vars="q2_main_barrier", var_name="Version", value_name="pct")
    fig = px.bar(bar, y="q2_main_barrier", x="pct", color="Version", barmode="group", orientation="h",
                 color_discrete_sequence=[ORANGE, BLUE], labels={"q2_main_barrier": "", "pct": "% of respondents"})
    fig.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0), title="Biggest reason someone might not report",
                      legend=dict(orientation="h", y=-0.25))
    b.plotly_chart(fig, width="stretch")
    k1, k2, k3 = st.columns(3)
    k1.metric("Heard of Women Helpline 181", f"{(sv.q4_heard_helpline_181 == 'Yes').mean():.0%}")
    k2.metric("Heard of the SC/ST Atrocities Act", f"{(sv.q5_heard_sc_st_act == 'Yes').mean():.0%}")
    k3.metric("Trust in local police (1-5)", f"{sv.q3_num.mean():.1f}")
    st.caption("Small sample, so treat differences by version as a pattern worth testing, not a finding. "
               "If you or someone you know needs help: Women Helpline 181, Emergency 112.")
