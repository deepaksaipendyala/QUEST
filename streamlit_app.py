from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import altair as alt
import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from src.observability.dashboard_data import (  # noqa: E402
    RUNS_ROOT,
    gather_recent_llm_calls,
    get_run_summaries,
    load_run_detail,
)


def _format_percent(value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        fval = float(value)
        if fval < 0:
            return "N/A"
        return f"{fval:.2f}%"
    except (ValueError, TypeError):
        return "N/A"


def _format_float(value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return "N/A"


def _format_cost(value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        fval = float(value)
        if fval == 0:
            return "$0.00"
        if fval < 0.0001:
            return f"${fval:.2e}"
        return f"${fval:.6f}"
    except (ValueError, TypeError):
        return "N/A"


def _format_duration(value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.2f}s"
    except (ValueError, TypeError):
        return "N/A"


def _build_runs_table(summaries: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for item in summaries:
        rows.append(
            {
                "Run": item["run_id"],
                "Type": item["kind"],
                "Stages": item.get("stage_count", 0),
                "Coverage": item.get("coverage"),
                "Mutation": item.get("mutation_score"),
                "Cost": item.get("total_cost"),
                "Duration": item.get("total_duration_seconds"),
                "Success": item.get("success"),
                "Status": item.get("status"),
                "Lint issues": item.get("lint_issues"),
                "Last stage": item.get("last_stage"),
                "Updated": item.get("updated_at"),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["Coverage"] = df["Coverage"].apply(lambda x: float(x) if x is not None else None)
        df["Mutation"] = df["Mutation"].apply(lambda x: float(x) if x is not None else None)
    return df


def _line_chart_int_x(
    df: pd.DataFrame,
    y_columns: List[str],
    x_label: str,
    y_label: str,
    *,
    height: int = 260,
) -> None:
    """Render a line chart with integer x-axis (1, 2, 3, ...) using Altair."""
    if df is None or df.empty:
        return

    data = df[y_columns].copy()
    # Bring index (experiment / iteration number) into a column
    data = data.reset_index()
    # Rename index column to a consistent name for plotting
    index_col = data.columns[0]
    data = data.rename(columns={index_col: "iteration"})

    # Long-form for Altair: iteration, metric, value
    data_long = data.melt(
        id_vars=["iteration"],
        value_vars=y_columns,
        var_name="metric",
        value_name="value",
    )

    chart = (
        alt.Chart(data_long)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "iteration:O",
                axis=alt.Axis(title=x_label, labelAngle=0),  # integer experiment/iteration numbers
            ),
            y=alt.Y("value:Q", title=y_label),
            color=alt.Color("metric:N", title="Metric"),
        )
        .properties(height=height)
    )
    st.altair_chart(chart, width="stretch")


def _build_experiments_comparison(summaries: List[Dict[str, Any]], limit: int = 10) -> pd.DataFrame:
    """Build comparison data across recent experiments with coverage, mutation, entropy, avg_logprob."""
    rows = []
    for summary in summaries[:limit]:
        run_id = summary.get("run_id", "")
        
        # Get best metrics from summary
        coverage = summary.get("coverage")
        mutation = summary.get("mutation_score")
        
        # Try to load run detail to get LLM confidence metrics
        entropy_values = []
        logprob_values = []
        
        try:
            detail = load_run_detail(run_id)
            iterations = detail.get("iterations", [])
            
            # Collect entropy and avg_logprob from all iterations
            for record in iterations:
                # Check enhancer LLM metadata
                llm_meta = record.get("llm_metadata")
                if llm_meta:
                    ent = llm_meta.get("entropy")
                    lp = llm_meta.get("avg_logprob")
                    if ent is not None:
                        entropy_values.append(ent)
                    if lp is not None:
                        logprob_values.append(lp)
                
                # Check supervisor LLM metadata (if available)
                supervisor_meta = record.get("supervisor_llm_metadata")
                if supervisor_meta:
                    ent = supervisor_meta.get("entropy")
                    lp = supervisor_meta.get("avg_logprob")
                    if ent is not None:
                        entropy_values.append(ent)
                    if lp is not None:
                        logprob_values.append(lp)
            
            # Use average if multiple values, otherwise use the value
            entropy = sum(entropy_values) / len(entropy_values) if entropy_values else None
            avg_logprob = sum(logprob_values) / len(logprob_values) if logprob_values else None
        except (FileNotFoundError, KeyError, AttributeError, ZeroDivisionError):
            entropy = None
            avg_logprob = None
        
        rows.append({
            "Run": run_id[:20] + "..." if len(run_id) > 20 else run_id,
            "Run ID": run_id,
            "Coverage": float(coverage) if coverage is not None and coverage >= 0 else None,
            "Mutation": float(mutation) if mutation is not None and mutation >= 0 else None,
            "Entropy": float(entropy) if entropy is not None else None,
            "Avg LogProb": float(avg_logprob) if avg_logprob is not None else None,
        })
    
    df = pd.DataFrame(rows)
    return df


def _build_history_chart(history: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(history)
    if df.empty:
        return df
    # Ensure records are ordered by original index if present
    if "index" in df.columns:
        df = df.sort_values("index")
    # Use a clean integer index 1..N so x-axis is experiment/iteration number
    df.insert(0, "experiment", range(1, len(df) + 1))
    df = df.set_index("experiment")
    # Include all metrics: coverage, mutation, entropy, avg_logprob
    chart_cols = ["coverage", "mutation_score", "entropy", "avg_logprob"]
    available_cols = [col for col in chart_cols if col in df.columns]
    return df[available_cols]


def _iteration_table(records: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        rows.append(
            {
                "Stage": record["label"],
                "Coverage": record.get("coverage"),
                "Mutation": record.get("mutation_score"),
                "Success": record.get("success"),
                "Status": record.get("status"),
                "Lint issues": record.get("lint_issues"),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["Coverage"] = df["Coverage"].apply(lambda x: float(x) if x is not None else None)
        df["Mutation"] = df["Mutation"].apply(lambda x: float(x) if x is not None else None)
    return df


def _agent_role(label: str) -> Optional[str]:
    if label.startswith("attempt_"):
        return "Generator" if label == "attempt_0" else "Enhancer"
    return None


def _render_iteration_details(records: List[Dict[str, Any]]) -> None:
    if not records:
        st.info("No iteration data found for this run.")
        return
    previous_critique: Optional[Dict[str, Any]] = None
    for record in records:
        agent_role = _agent_role(record["label"]) if "label" in record else None
        with st.expander(f"{record['label']} • coverage {_format_percent(record.get('coverage'))}"):
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Coverage", _format_percent(record.get("coverage")))
            col2.metric("Mutation", _format_percent(record.get("mutation_score")))
            col3.metric("Lint issues", record.get("lint_issues", 0))
            metrics = record.get("metrics") or {}
            col4.metric("Cost", _format_cost(metrics.get("llm_cost")))
            col5.metric("Duration", _format_duration(metrics.get("runner_duration_seconds")))

            static_metrics = record.get("static_metrics")
            if static_metrics:
                st.caption("Static analysis")
                st.json(static_metrics, expanded=False)

            if record.get("llm_metadata"):
                st.caption("LLM metadata")
                st.json(record["llm_metadata"], expanded=False)
            
            if record.get("supervisor_llm_metadata"):
                st.caption("Supervisor LLM metadata")
                supervisor_meta = record["supervisor_llm_metadata"]
                col1, col2, col3 = st.columns(3)
                with col1:
                    entropy = supervisor_meta.get('entropy')
                    entropy_val = f"{entropy:.3f}" if entropy is not None else "N/A"
                    st.metric("Entropy", entropy_val)
                with col2:
                    avg_logprob = supervisor_meta.get('avg_logprob')
                    logprob_val = f"{avg_logprob:.3f}" if avg_logprob is not None else "N/A"
                    st.metric("Avg LogProb", logprob_val)
                with col3:
                    cost = supervisor_meta.get('estimated_cost', 0) or 0
                    st.metric("Cost", _format_cost(cost))
                
                with st.expander("Full supervisor LLM metadata"):
                    st.json(supervisor_meta, expanded=False)

            if record.get("reliability"):
                st.caption("Reliability (pre / post)")
                st.json(record["reliability"], expanded=False)
            if record.get("critique"):
                st.caption("Supervisor critique")
                critique = record["critique"]
                
                # Display LLM suggestions if available
                llm_suggestions = critique.get("llm_suggestions")
                if llm_suggestions:
                    st.markdown("**LLM Supervisor Analysis:**")
                    
                    # Priority issues
                    if llm_suggestions.get("priority_issues"):
                        st.markdown("🚨 **Priority Issues:**")
                        for issue in llm_suggestions["priority_issues"][:3]:
                            st.markdown(f"- {issue}")
                    
                    # Coverage suggestions
                    if llm_suggestions.get("coverage_suggestions"):
                        st.markdown("📊 **Coverage Improvements:**")
                        for suggestion in llm_suggestions["coverage_suggestions"][:3]:
                            st.markdown(f"- {suggestion}")
                    
                    # Mutation suggestions
                    if llm_suggestions.get("mutation_suggestions"):
                        st.markdown("🧬 **Mutation Score Improvements:**")
                        for suggestion in llm_suggestions["mutation_suggestions"][:3]:
                            st.markdown(f"- {suggestion}")
                    
                    # Next steps
                    if llm_suggestions.get("next_steps"):
                        st.markdown("🎯 **Next Steps:**")
                        for step in llm_suggestions["next_steps"][:3]:
                            st.markdown(f"- {step}")
                    
                    with st.expander("View full LLM analysis"):
                        st.json(llm_suggestions, expanded=False)
                
                # Display full critique in expandable section
                with st.expander("View full supervisor critique"):
                    st.json(critique, expanded=False)

            supervisor_instructions: Optional[List[str]] = None
            if agent_role == "Enhancer" and previous_critique:
                supervisor_instructions = previous_critique.get("instructions")
            if supervisor_instructions:
                st.caption("Instructions fed to enhancer")
                st.markdown(
                    "\n".join(f"- {inst}" for inst in supervisor_instructions if inst),
                    help="Derived from the previous supervisor critique.",
                )

            if record.get("request"):
                caption = "Runner request"
                if agent_role:
                    caption = f"{agent_role} → Runner request"
                st.caption(caption)
                st.json(record["request"], expanded=False)
            if record.get("response"):
                st.caption("Runner response (stdout trimmed)")
                st.json(record["response"], expanded=False)
            if record.get("test_src"):
                caption = "Generated test source"
                if agent_role:
                    caption = f"{agent_role} output (test source)"
                st.caption(caption)
                st.code(record["test_src"], language="python")

        previous_critique = record.get("critique")


def _render_llm_table(rows: List[Dict[str, Any]], title: str) -> None:
    st.caption(title)
    if not rows:
        st.info("No LLM metadata recorded yet.")
        return
    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, width='stretch')


def main() -> None:
    st.set_page_config(page_title="TestGenEval Dashboard", layout="wide")
    st.title("TestGenEval Live Dashboard")
    st.caption(f"Watching artifacts in: `{RUNS_ROOT}`")

    sidebar = st.sidebar
    sidebar.header("Controls")
    auto_refresh = sidebar.checkbox("Auto-refresh", value=True)
    refresh_seconds = sidebar.slider("Refresh interval (seconds)", 2, 30, 5)
    run_limit = sidebar.slider("Runs to display", 5, 50, 15)
    run_types = sidebar.multiselect("Run types", ["pipeline", "orchestrator", "unknown"], default=["pipeline", "orchestrator", "unknown"])

    summaries = [s for s in get_run_summaries(limit=run_limit * 2) if s["kind"] in run_types][:run_limit]
    if not summaries:
        st.warning("No runs detected yet. Execute a pipeline or orchestrator command to generate artifacts.")
        if auto_refresh:
            time.sleep(refresh_seconds)
            st.rerun()
        return

    runs_df = _build_runs_table(summaries)
    st.subheader("Recent runs")
    st.dataframe(runs_df, width='stretch', hide_index=True)

    # Experiments comparison plot
    st.subheader("Experiments Comparison: Coverage, Mutation & LLM Confidence")
    comparison_df = _build_experiments_comparison(summaries, limit=min(10, len(summaries)))
    
    if not comparison_df.empty:
        # Filter out runs with no valid data
        comparison_df_filtered = comparison_df[
            (comparison_df["Coverage"].notna()) | 
            (comparison_df["Mutation"].notna()) |
            (comparison_df["Entropy"].notna()) |
            (comparison_df["Avg LogProb"].notna())
        ].copy()
        
        if not comparison_df_filtered.empty:
            # Set Run as index for charting
            comparison_df_filtered = comparison_df_filtered.set_index("Run")
            
            # Create two vertically stacked plots with same x-axis (experiment numbers)
            st.markdown("**All Metrics Comparison: Coverage, Mutation, Entropy, Avg LogProb**")
            st.caption("Metrics across recent experiments | X-axis: Experiment Number (1, 2, 3, ...)")
            
            # Reset index to get experiment numbers (1, 2, 3, ...)
            chart_data = comparison_df_filtered.reset_index(drop=True)
            chart_data["Experiment"] = chart_data.index + 1
            chart_data = chart_data.set_index("Experiment")
            
            # Top plot: Coverage & Mutation
            st.markdown("**Coverage & Mutation Score (%)**")
            coverage_mutation_cols = ["Coverage", "Mutation"]
            available_cols = [col for col in coverage_mutation_cols if col in chart_data.columns]
            if available_cols:
                chart_data_cm = chart_data[available_cols].dropna(how='all')
                if not chart_data_cm.empty:
                    _line_chart_int_x(
                        chart_data_cm,
                        ["Coverage", "Mutation"],
                        x_label="Experiment Number",
                        y_label="Percentage (%)",
                        height=300,
                    )
                else:
                    st.info("No coverage/mutation data available")
            else:
                st.info("No coverage/mutation data available")
            
            # Bottom plot: LLM Confidence Metrics
            st.markdown("**LLM Confidence Metrics**")
            st.caption("Lower entropy = more confident | Higher abs(logprob) = more confident")
            confidence_df = pd.DataFrame()
            if "Entropy" in chart_data.columns and "Avg LogProb" in chart_data.columns:
                confidence_df = chart_data[["Entropy", "Avg LogProb"]].copy()
                # Drop rows where both are None/NaN
                confidence_df = confidence_df.dropna(how="all")
                if not confidence_df.empty:
                    # Use same transformation as individual experiment graph
                    # (lower entropy = more confident, higher abs(logprob) = more confident)
                    if "Avg LogProb" in confidence_df.columns:
                        confidence_df["logprob_confidence"] = confidence_df["Avg LogProb"].abs()
                        confidence_df = confidence_df[["Entropy", "logprob_confidence"]].rename(
                            columns={"logprob_confidence": "avg_logprob (abs)"}
                        )
                    _line_chart_int_x(
                        confidence_df,
                        ["Entropy", "avg_logprob (abs)"],
                        x_label="Experiment Number",
                        y_label="Confidence Score",
                        height=300,
                    )
                else:
                    st.info("No LLM confidence data")
            else:
                st.info("No LLM confidence data (entropy/logprob)")
            
            # Show data table
            with st.expander("View comparison data table"):
                display_df = comparison_df[["Run", "Coverage", "Mutation", "Entropy", "Avg LogProb"]].copy()
                st.dataframe(display_df, width='stretch', hide_index=True)
        else:
            st.info("No valid metrics available in recent experiments for comparison.")
    else:
        st.info("No experiments data available for comparison.")

    run_options = [summary["run_id"] for summary in summaries]
    selected_run = sidebar.selectbox("Focused run", run_options, index=0)

    try:
        detail = load_run_detail(selected_run)
    except FileNotFoundError:
        st.error(f"Run `{selected_run}` no longer exists. Pick another run.")
        if auto_refresh:
            time.sleep(refresh_seconds)
            st.rerun()
        return

    summary = detail["summary"]
    st.subheader(f"Run {summary['run_id']} • {summary.get('kind', 'unknown').title()}")

    metric_cols = st.columns(6)
    metric_cols[0].metric("Current coverage", _format_percent(summary.get("coverage")))
    metric_cols[1].metric("Current mutation", _format_percent(summary.get("mutation_score")))
    metric_cols[2].metric("Stages completed", summary.get("stage_count", len(detail["iterations"])))
    metric_cols[3].metric("Lint issues (latest)", summary.get("lint_issues", 0))
    metric_cols[4].metric("Total cost", _format_cost(summary.get("total_cost")))
    metric_cols[5].metric("Total duration", _format_duration(summary.get("total_duration_seconds")))

    history_df = _build_history_chart(detail["history"])
    st.markdown("### Coverage, Mutation & LLM Confidence Trend")
    if history_df.empty:
        st.info("Trend data not available yet.")
    else:
        # Create two charts: one for coverage/mutation (percentages), one for entropy/logprob (confidence)
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Coverage & Mutation Score (%)**")
            coverage_mutation_df = history_df[["coverage", "mutation_score"]].copy() if all(col in history_df.columns for col in ["coverage", "mutation_score"]) else pd.DataFrame()
            if not coverage_mutation_df.empty:
                # Filter out negative values (N/A)
                coverage_mutation_df = coverage_mutation_df[coverage_mutation_df["coverage"] >= 0]
                coverage_mutation_df = coverage_mutation_df[coverage_mutation_df["mutation_score"] >= 0]
                if not coverage_mutation_df.empty:
                    _line_chart_int_x(
                        coverage_mutation_df,
                        ["coverage", "mutation_score"],
                        x_label="Iteration Number",
                        y_label="Percentage (%)",
                        height=260,
                    )
                else:
                    st.info("No valid coverage/mutation data")
            else:
                st.info("No coverage/mutation data")
        
        with col2:
            st.markdown("**LLM Confidence Metrics**")
            st.caption("Lower entropy = more confident | Higher abs(logprob) = more confident")
            confidence_df = pd.DataFrame()
            if "entropy" in history_df.columns and "avg_logprob" in history_df.columns:
                confidence_df = history_df[["entropy", "avg_logprob"]].copy()
                # Drop rows where both are None/NaN
                confidence_df = confidence_df.dropna(how="all")
                if not confidence_df.empty:
                    # For visualization: show entropy as-is, and logprob as absolute value
                    # (lower entropy = more confident, higher abs(logprob) = more confident)
                    if "avg_logprob" in confidence_df.columns:
                        confidence_df["logprob_confidence"] = confidence_df["avg_logprob"].abs()
                        confidence_df = confidence_df[["entropy", "logprob_confidence"]].rename(
                            columns={"logprob_confidence": "avg_logprob (abs)"}
                        )
                    _line_chart_int_x(
                        confidence_df,
                        ["entropy", "avg_logprob (abs)"],
                        x_label="Iteration Number",
                        y_label="Confidence Score",
                        height=260,
                    )
                else:
                    st.info("No LLM confidence data")
            else:
                st.info("No LLM confidence data (entropy/logprob)")

    tabs = st.tabs(["Iterations", "Reliability snapshot", "LLM feed", "Events"])
    with tabs[0]:
        st.caption("Per-stage snapshot")
        iter_df = _iteration_table(detail["iterations"])
        if iter_df.empty:
            st.info("No stage information recorded.")
        else:
            st.dataframe(iter_df, width='stretch', hide_index=True)
        _render_iteration_details(detail["iterations"])

    with tabs[1]:
        reliability_rows = []
        for record in detail["iterations"]:
            pre = (record.get("reliability") or {}).get("pre")
            post = (record.get("reliability") or {}).get("post")
            if pre or post:
                reliability_rows.append(
                    {
                        "Stage": record["label"],
                        "Pre level": (pre or {}).get("level"),
                        "Post level": (post or {}).get("level"),
                        "Reasons": ", ".join((post or {}).get("reasons", [])) if post else "",
                        "Entropy": (pre or {}).get("entropy"),
                        "Lint issues": (pre or {}).get("lint", {}).get("issues") if pre else None,
                    }
                )
        if reliability_rows:
            st.dataframe(pd.DataFrame(reliability_rows), hide_index=True, width='stretch')
        else:
            st.info("This run has no reliability metadata yet.")

    with tabs[2]:
        per_run_llm = []
        for record in detail["iterations"]:
            llm = record.get("llm_metadata")
            if not llm:
                continue
            per_run_llm.append(
                {
                    "Stage": record["label"],
                    "Entropy": llm.get("entropy"),
                    "Avg logprob": llm.get("avg_logprob"),
                    "Tokens": llm.get("token_count"),
                }
            )
        _render_llm_table(per_run_llm, f"LLM calls within {summary['run_id']}")
        recent_llm = gather_recent_llm_calls(limit=25)
        _render_llm_table(recent_llm, "Recent LLM calls (all runs)")

    with tabs[3]:
        events = detail["events"]
        if not events:
            st.info("No events log found for this run.")
        else:
            st.code("\n".join(events), language="text")

    sidebar.markdown("---")
    sidebar.write("Use the Streamlit **R** button (top-right) to rerun manually if auto-refresh is disabled.")

    if auto_refresh:
        time.sleep(refresh_seconds)
        st.rerun()


if __name__ == "__main__":
    main()

