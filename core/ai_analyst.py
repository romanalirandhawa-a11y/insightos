"""AI analyst utilities for InsightOS.

Phase 6: builds a factual context from pandas KPI results and answers
user questions via OpenRouter or Gemini (both OpenAI-compatible).
The AI never calculates numbers - it only explains the facts it is given.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

# Load environment variables from .env (never print or log the key).
load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_PROVIDER = "openrouter"
DEFAULT_MODEL = "openrouter/free"

# Speed settings.
MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "1500"))
TEMPERATURE = 0.2


def _fmt_change(change: float) -> str:
    """Format a numeric change with an explicit sign, e.g. +$611.66 or -$571.42."""
    sign = "+" if change >= 0 else "-"
    return f"{sign}${abs(change):,.2f}"


def _strip_reasoning(text: str) -> str:
    """Remove reasoning blocks from model output.

    Strips any `<think>...</think>` section and trims whitespace. The
    final answer content is what remains.
    """
    import re

    open_tag = chr(60) + "think" + chr(62)
    close_tag = chr(60) + "/" + "think" + chr(62)
    pattern = re.escape(open_tag) + ".*?" + re.escape(close_tag)
    text = re.sub(pattern, "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove any leading "reasoning:" or "analysis:" preamble lines.
    text = re.sub(
        r"^(reasoning|analysis|think|internal monologue):\s*\n?",
        "",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return text.strip()


def _extract_reasoning_content(chunk) -> str | None:
    """Extract reasoning_content from a stream chunk if present.

    Returns the reasoning text or None.
    """
    try:
        delta = chunk.choices[0].delta
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            return delta.reasoning_content
    except Exception:  # noqa: BLE001 - defensive
        pass
    return None


def _is_blank(text: str | None) -> bool:
    """Return True if the text is None or blank/whitespace-only."""
    return not text or not text.strip()



def _driver_lines(df, metric: str, drivers: dict, label: str) -> list[str]:
    """Build the driver section lines for a metric (Profit or Sales).

    Only entries with a positive change appear under "Top positive ...";
    only entries with a negative change appear under "... with decline";
    "None" is written when there are no entries of that kind. Changes
    always carry an explicit sign.

    Args:
        df: Cleaned sales DataFrame.
        metric: Column name ("Profit" or "Sales").
        drivers: Output of core.kpi.driver_analysis(df, metric).
        label: "Profit" or "Sales" used in the header.

    Returns:
        List of context lines for this driver section.
    """
    lines = []
    prev = drivers["previous_month"]
    curr = drivers["latest_month"]

    if drivers["latest_month"] is None:
        lines.append("Not enough months for driver analysis.")
        return lines

    lines.append(
        f"{curr} vs {prev}: "
        f"{label} change {_fmt_change(drivers['total_change_abs'])} "
        f"({drivers['total_change_pct']}%)"
    )

    # Build explicit per-entity month values.
    entity_monthly = (
        df.groupby(["Product", "Month"])[metric]
        .sum()
        .reset_index()
        .pivot(index="Product", columns="Month", values=metric)
        .fillna(0)
    )
    entity_monthly["change"] = entity_monthly[curr] - entity_monthly[prev]
    entity_changes = entity_monthly["change"].sort_values(ascending=False)

    pos_products = [
        p for p in entity_changes.index if entity_changes[p] > 0
    ]
    neg_products = [
        p for p in entity_changes.index if entity_changes[p] < 0
    ]
    # Sort positives largest-first; negatives most-negative-first.
    pos_products = sorted(pos_products, key=lambda p: entity_changes[p], reverse=True)
    neg_products = sorted(neg_products, key=lambda p: entity_changes[p])

    lines.append("Top positive products:")
    if pos_products:
        for product in pos_products[:3]:
            p = entity_monthly.loc[product]
            lines.append(
                f"  Product {product}: {metric} {prev} = ${p[prev]:,.2f}, "
                f"{curr} = ${p[curr]:,.2f}, change = {_fmt_change(p['change'])}"
            )
    else:
        lines.append("  None")

    lines.append(f"Products with {label.lower()} decline:")
    if neg_products:
        for product in neg_products[:3]:
            p = entity_monthly.loc[product]
            lines.append(
                f"  Product {product}: {metric} {prev} = ${p[prev]:,.2f}, "
                f"{curr} = ${p[curr]:,.2f}, change = {_fmt_change(p['change'])}"
            )
    else:
        lines.append("  None")

    # Regions.
    reg_monthly = (
        df.groupby(["Region", "Month"])[metric]
        .sum()
        .reset_index()
        .pivot(index="Region", columns="Month", values=metric)
        .fillna(0)
    )
    reg_monthly["change"] = reg_monthly[curr] - reg_monthly[prev]
    reg_changes = reg_monthly["change"].sort_values(ascending=False)

    pos_regions = [r for r in reg_changes.index if reg_changes[r] > 0]
    neg_regions = [r for r in reg_changes.index if reg_changes[r] < 0]
    # Sort positives largest-first; negatives most-negative-first.
    pos_regions = sorted(pos_regions, key=lambda r: reg_changes[r], reverse=True)
    neg_regions = sorted(neg_regions, key=lambda r: reg_changes[r])

    lines.append("Top positive regions:")
    if pos_regions:
        for region in pos_regions[:3]:
            r = reg_monthly.loc[region]
            lines.append(
                f"  Region {region}: {metric} {prev} = ${r[prev]:,.2f}, "
                f"{curr} = ${r[curr]:,.2f}, change = {_fmt_change(r['change'])}"
            )
    else:
        lines.append("  None")

    lines.append(f"Regions with {label.lower()} decline:")
    if neg_regions:
        for region in neg_regions[:3]:
            r = reg_monthly.loc[region]
            lines.append(
                f"  Region {region}: {metric} {prev} = ${r[prev]:,.2f}, "
                f"{curr} = ${r[curr]:,.2f}, change = {_fmt_change(r['change'])}"
            )
    else:
        lines.append("  None")

    return lines


def _get_provider() -> str:
    """Return the AI provider from env (default: openrouter)."""
    return os.getenv("AI_PROVIDER", DEFAULT_PROVIDER)


def _get_client(provider: str) -> OpenAI | None:
    """Return an OpenAI client configured for the given provider, or None
    if the required API key is missing.

    Args:
        provider: "openrouter" or "gemini".

    The API key is read from the matching environment variable and is
    never printed or logged.
    """
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        base_url = GEMINI_BASE_URL
        model_env = "GEMINI_MODEL"
        model_default = "gemini-1.5-flash"
    else:
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = OPENROUTER_BASE_URL
        model_env = "OPENROUTER_MODEL"
        model_default = DEFAULT_MODEL

    if not api_key:
        return None

    model = os.getenv(model_env, model_default)
    if not model:
        return None

    return OpenAI(base_url=base_url, api_key=api_key), model


def _other_provider(provider: str) -> str:
    """Return the opposite provider name."""
    return "gemini" if provider == "openrouter" else "openrouter"


def _get_client_and_model(provider: str):
    """Try to get a client + model for the given provider.

    Returns:
        (client, model) tuple, or (None, None) if unavailable.
    """
    result = _get_client(provider)
    if result is None:
        return None, None
    return result


def _friendly_error(exc: Exception, provider: str) -> str:
    """Convert an API exception into a friendly user-facing message.

    Args:
        exc: The exception from the API call.
        provider: The provider that raised it ("openrouter" or "gemini").

    Returns:
        A short, friendly message. Never exposes the API key.
    """
    msg = str(exc)
    key_env = "GEMINI_API_KEY" if provider == "gemini" else "OPENROUTER_API_KEY"

    if "429" in msg or "rate limit" in msg.lower():
        return (
            f"The {provider} AI service is rate-limited. Please try again "
            "in a moment."
        )
    if "401" in msg or "403" in msg:
        return (
            f"Authentication failed for {provider}. Please check your "
            f"{key_env}."
        )
    if "network" in msg.lower() or "connection" in msg.lower():
        return (
            f"Unable to reach the {provider} AI service. Please check "
            "your internet connection and try again."
        )
    if "model" in msg.lower() and "not found" in msg.lower():
        return (
            f"The model is not available on {provider}. Please check "
            f"your model setting."
        )
    return (
        f"Sorry, the {provider} AI Analyst encountered an error. "
        "Please try again later."
    )


def compute_rankings(df) -> dict:
    """Compute explicit highest/lowest rankings using pandas.

    All numbers come from the DataFrame - the helper never asks the AI
    to rank anything.

    Args:
        df: Cleaned sales DataFrame.

    Returns:
        dict with keys for regions, products, and categories, each
        containing highest/lowest for revenue, profit, and margin.
    """
    def _highest_lowest(grouped_df, name_col):
        """Return (highest_row, lowest_row) by Revenue from a grouped df."""
        if grouped_df.empty:
            return None, None
        sorted_df = grouped_df.sort_values("Revenue", ascending=False)
        return sorted_df.iloc[0], sorted_df.iloc[-1]

    regions = (
        df.groupby("Region")
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"))
        .reset_index()
    )
    regions["Margin %"] = regions.apply(
        lambda r: round(
            r["Profit"] / r["Revenue"] * 100 if r["Revenue"] != 0 else 0.0, 1
        ),
        axis=1,
    )

    products = (
        df.groupby("Product")
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"))
        .reset_index()
    )
    products["Margin %"] = products.apply(
        lambda r: round(
            r["Profit"] / r["Revenue"] * 100 if r["Revenue"] != 0 else 0.0, 1
        ),
        axis=1,
    )

    categories = (
        df.groupby("Category")
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"))
        .reset_index()
    )
    categories["Margin %"] = categories.apply(
        lambda r: round(
            r["Profit"] / r["Revenue"] * 100 if r["Revenue"] != 0 else 0.0, 1
        ),
        axis=1,
    )

    def _rev_hi_lo(frame):
        return _highest_lowest(frame, "Name")

    def _by_col(frame, col):
        if frame.empty:
            return None, None
        sorted_df = frame.sort_values(col, ascending=False)
        return sorted_df.iloc[0], sorted_df.iloc[-1]

    return {
        "regions": regions,
        "products": products,
        "categories": categories,
        "_by_col": _by_col,
    }


def _build_messages(question: str, context: str, history=None) -> list[dict]:
    """Build the message list for the chat completion.

    Args:
        question: The user's question.
        context: Factual summary string from build_context().
        history: Optional list of prior chat messages.

    Returns:
        A list of message dicts for the OpenAI-compatible API.
    """
    system_prompt = (
        "You are a business analyst. Answer ONLY using the facts "
        "provided in the context. Never invent or calculate new "
        "numbers. Never rank or compare numbers yourself. For any "
        "'highest', 'lowest', 'best', or 'worst' claim, copy it from "
        "the RANKINGS section. Always quote the exact number from the "
        "facts next to each claim. If the facts do not contain the "
        "answer, say so. Keep answers short, clear, balanced: mention "
        "at least one positive point and consider margin, not only "
        "month-over-month change. When a region or product shows a "
        "decline in one metric but growth in another (for example "
        "sales down but profit up), mention that contrast. Do not show "
        "your reasoning or analysis steps. Reply with only the final "
        "answer in this format: 2 to 4 short sentences, each with "
        "exact numbers from the facts, then one line starting with "
        "'Recommendation:'."
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.append(
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}"}
    )

    if history:
        for msg in history[-6:]:
            messages.insert(-1, msg)

    return messages


def _call_provider(
    client: OpenAI, model: str, messages: list[dict], provider: str = "openrouter"
) -> tuple[str, str, bool]:
    """Make a single chat completion call and return the answer text.

    Args:
        client: OpenAI client instance.
        model: Model name.
        messages: Message list.
        provider: Provider name ("openrouter" or "gemini") for
            reasoning_effort handling.

    Returns:
        (answer_text, finish_reason, is_cut_off) tuple. The answer text
        has reasoning blocks stripped.
    """
    extra_body = {}
    if provider == "gemini":
        extra_body["reasoning_effort"] = "low"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            extra_body=extra_body if extra_body else None,
        )
    except Exception as exc:  # noqa: BLE001 - retry without reasoning_effort
        if provider == "gemini" and "reasoning_effort" in str(exc).lower():
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
        else:
            raise

    choice = response.choices[0]
    content = choice.message.content or ""
    content = _strip_reasoning(content)
    finish_reason = getattr(choice, "finish_reason", None) or "stop"
    is_cut_off = finish_reason == "length"
    return content.strip(), finish_reason, is_cut_off


def _call_provider_stream(
    client: OpenAI, model: str, messages: list[dict], provider: str = "openrouter"
) -> tuple[str, str, bool]:
    """Stream a chat completion and return the full answer text.

    Args:
        client: OpenAI client instance.
        model: Model name.
        messages: Message list.
        provider: Provider name ("openrouter" or "gemini") for
            reasoning_effort handling.

    Returns:
        (full_text, finish_reason, is_cut_off) tuple. Reasoning blocks
        and reasoning_content are stripped from the output.
    """
    extra_body = {}
    if provider == "gemini":
        extra_body["reasoning_effort"] = "low"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=True,
            extra_body=extra_body if extra_body else None,
        )
    except Exception as exc:  # noqa: BLE001 - retry without reasoning_effort
        if provider == "gemini" and "reasoning_effort" in str(exc).lower():
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                stream=True,
            )
        else:
            raise

    full_text = ""
    finish_reason = "stop"
    for chunk in response:
        delta = chunk.choices[0].delta
        # Ignore reasoning_content field entirely.
        _ = _extract_reasoning_content(chunk)
        if delta and delta.content:
            full_text += delta.content
        chunk_finish = getattr(chunk.choices[0], "finish_reason", None)
        if chunk_finish:
            finish_reason = chunk_finish

    full_text = _strip_reasoning(full_text)
    is_cut_off = finish_reason == "length"
    return full_text.strip(), finish_reason, is_cut_off


def _try_providers(question: str, context: str, history=None) -> tuple[str, str]:
    """Try the primary provider, then fall back to the other on failure.

    Args:
        question: The user's question.
        context: Factual summary string.
        history: Optional prior chat messages.

    Returns:
        (answer, provider_name) tuple. If both providers fail, returns
        a friendly error message and the last attempted provider name.
    """
    primary = _get_provider()
    secondary = _other_provider(primary)

    messages = _build_messages(question, context, history)

    def _finalize(answer: str, is_cut_off: bool, provider_name: str) -> str:
        if is_cut_off:
            answer = answer + " (answer was cut off, try again)"
        return answer

    # Try primary provider.
    client, model = _get_client_and_model(primary)
    if client is not None:
        try:
            answer, finish_reason, is_cut_off = _call_provider(
                client, model, messages, primary
            )
            if _is_blank(answer):
                raise ValueError("empty answer from provider")
            return _finalize(answer, is_cut_off, primary), primary
        except Exception as exc:  # noqa: BLE001 - fall through to secondary
            primary_error = _friendly_error(exc, primary)
    else:
        primary_error = (
            f"{primary} is not configured. Please set its API key in .env."
        )

    # Try secondary provider if its key exists.
    client2, model2 = _get_client_and_model(secondary)
    if client2 is not None:
        try:
            answer, finish_reason, is_cut_off = _call_provider(
                client2, model2, messages, secondary
            )
            if _is_blank(answer):
                raise ValueError("empty answer from provider")
            return _finalize(answer, is_cut_off, secondary), secondary
        except Exception as exc:  # noqa: BLE001 - return friendly error
            return _friendly_error(exc, secondary), secondary

    # Neither provider worked.
    return primary_error, primary


def _try_providers_stream(question: str, context: str, history=None):
    """Stream from the primary provider, falling back to secondary.

    Args:
        question: The user's question.
        context: Factual summary string.
        history: Optional prior chat messages.

    Yields:
        Text chunks as they arrive. If the final answer is blank or both
        providers fail, yields a friendly error message instead.
    """
    primary = _get_provider()
    secondary = _other_provider(primary)

    messages = _build_messages(question, context, history)

    def _is_blank(text: str) -> bool:
        return not text or not text.strip()

    # Try primary provider.
    client, model = _get_client_and_model(primary)
    full_text = ""
    finish_reason = "stop"
    provider_used = primary
    provider_error = None

    if client is not None:
        try:
            full_text, finish_reason, _ = _call_provider_stream(
                client, model, messages, primary
            )
        except Exception as exc:  # noqa: BLE001 - fall through to secondary
            provider_error = _friendly_error(exc, primary)
            full_text = ""
    else:
        provider_error = (
            f"{primary} is not configured. Please set its API key in .env."
        )

    # If primary failed or returned blank, try secondary.
    if _is_blank(full_text) and provider_error is not None:
        client2, model2 = _get_client_and_model(secondary)
        if client2 is not None:
            try:
                full_text, finish_reason, _ = _call_provider_stream(
                    client2, model2, messages, secondary
                )
                provider_used = secondary
                provider_error = None
            except Exception as exc:  # noqa: BLE001 - return friendly error
                provider_error = _friendly_error(exc, secondary)
                provider_used = secondary
        else:
            if provider_error is None:
                provider_error = (
                    f"{secondary} is not configured. Please set its API "
                    "key in .env."
                )

    full_text = _strip_reasoning(full_text)

    if _is_blank(full_text):
        if provider_error:
            yield provider_error
        else:
            provider_name, model_name = get_provider_info()
            yield (
                f"The AI returned an empty answer. Try again or switch "
                f"model in .env (provider: {provider_name}, model: "
                f"{model_name})."
            )
        return

    is_cut_off = finish_reason == "length"
    if is_cut_off:
        full_text = full_text + " (answer was cut off, try again)"

    # Yield the answer in small chunks so it appears to stream.
    for i in range(0, len(full_text), 40):
        yield full_text[i : i + 40]


@st.cache_data
def _cached_build_context(df) -> str:
    """Cache the factual context so it is not rebuilt on every question.

    Args:
        df: Cleaned sales DataFrame.

    Returns:
        A multi-line string with key facts about the business.
    """
    from core.kpi import (
        calculate_core_kpis,
        calculate_growth,
        category_performance,
        driver_analysis,
        monthly_trend,
        regional_performance,
        top_customers,
        top_products,
        worst_products,
    )

    kpis = calculate_core_kpis(df)
    growth = calculate_growth(df)
    trend = monthly_trend(df)
    top_prod = top_products(df, n=5)
    worst_prod = worst_products(df, n=5)
    regions = regional_performance(df)
    cats = category_performance(df)
    customers = top_customers(df, n=5)
    drivers_profit = driver_analysis(df, metric="Profit")
    drivers_sales = driver_analysis(df, metric="Sales")

    rankings = compute_rankings(df)
    regions_df = rankings["regions"]
    products_df = rankings["products"]
    categories_df = rankings["categories"]

    def _rev_name(frame):
        if frame.empty:
            return None, None
        sorted_df = frame.sort_values("Revenue", ascending=False)
        return sorted_df.iloc[0], sorted_df.iloc[-1]

    def _col_hi_lo(frame, col):
        if frame.empty:
            return None, None
        sorted_df = frame.sort_values(col, ascending=False)
        return sorted_df.iloc[0], sorted_df.iloc[-1]

    lines = []
    lines.append("=== KEY METRICS ===")
    lines.append(f"Total Revenue: ${kpis['total_revenue']:,.2f}")
    lines.append(f"Total Profit: ${kpis['total_profit']:,.2f}")
    lines.append(f"Profit Margin: {kpis['profit_margin_pct']:.1f}%")
    lines.append(f"Total Orders: {kpis['total_orders']}")
    lines.append(f"Avg Order Value: ${kpis['avg_order_value']:,.2f}")
    lines.append(f"Total Customers: {kpis['total_customers']}")
    lines.append(f"Total Quantity: {kpis['total_quantity']}")

    lines.append("")
    lines.append("=== MONTH-OF-MONTH GROWTH ===")
    if growth["latest_month"] is None:
        lines.append("Not enough months to calculate growth.")
    else:
        lines.append(
            f"Latest Month: {growth['latest_month']} "
            f"(Previous: {growth['previous_month']})"
        )
        lines.append(f"Revenue Growth: {growth['revenue_growth_pct']}%")
        lines.append(f"Profit Growth: {growth['profit_growth_pct']}%")

    lines.append("")
    lines.append("=== MONTHLY TREND ===")
    for _, row in trend.iterrows():
        lines.append(
            f"{row['Month']}: Revenue ${row['Revenue']:,.2f}, "
            f"Profit ${row['Profit']:,.2f}, Orders {row['Orders']}"
        )

    lines.append("")
    lines.append("=== TOP PRODUCTS (by Revenue) ===")
    for _, row in top_prod.iterrows():
        lines.append(
            f"{row['Product']}: Revenue ${row['Revenue']:,.2f}, "
            f"Profit ${row['Profit']:,.2f}, Qty {row['Quantity']}, "
            f"Margin {row['Margin %']}%"
        )

    lines.append("")
    lines.append("=== WORST PRODUCTS (by Revenue) ===")
    for _, row in worst_prod.iterrows():
        lines.append(
            f"{row['Product']}: Revenue ${row['Revenue']:,.2f}, "
            f"Profit ${row['Profit']:,.2f}, Qty {row['Quantity']}, "
            f"Margin {row['Margin %']}%"
        )

    lines.append("")
    lines.append("=== REGIONAL PERFORMANCE ===")
    for _, row in regions.iterrows():
        lines.append(
            f"{row['Region']}: Revenue ${row['Revenue']:,.2f}, "
            f"Profit ${row['Profit']:,.2f}, Margin {row['Margin %']}%, "
            f"Orders {row['Orders']}, Share {row['Revenue Share %']}%"
        )

    lines.append("")
    lines.append("=== CATEGORY PERFORMANCE ===")
    for _, row in cats.iterrows():
        lines.append(
            f"{row['Category']}: Revenue ${row['Revenue']:,.2f}, "
            f"Profit ${row['Profit']:,.2f}, Margin {row['Margin %']}%, "
            f"Orders {row['Orders']}, Share {row['Revenue Share %']}%"
        )

    lines.append("")
    lines.append("=== TOP CUSTOMERS ===")
    for _, row in customers.iterrows():
        lines.append(
            f"{row['Customer']}: Revenue ${row['Revenue']:,.2f}, "
            f"Profit ${row['Profit']:,.2f}, Orders {row['Orders']}"
        )

    # ===== RANKINGS SECTION =====
    lines.append("")
    lines.append("=== RANKINGS ===")

    # Regions
    rev_hi, rev_lo = _rev_name(regions_df)
    prof_hi, prof_lo = _col_hi_lo(regions_df, "Profit")
    mar_hi, mar_lo = _col_hi_lo(regions_df, "Margin %")
    if rev_hi is not None:
        lines.append(
            f"Highest revenue region: {rev_hi['Region']} "
            f"(${rev_hi['Revenue']:,.2f})"
        )
    if rev_lo is not None:
        lines.append(
            f"Lowest revenue region: {rev_lo['Region']} "
            f"(${rev_lo['Revenue']:,.2f})"
        )
    if prof_hi is not None:
        lines.append(
            f"Highest profit region: {prof_hi['Region']} "
            f"(${prof_hi['Profit']:,.2f})"
        )
    if prof_lo is not None:
        lines.append(
            f"Lowest profit region: {prof_lo['Region']} "
            f"(${prof_lo['Profit']:,.2f})"
        )
    if mar_hi is not None:
        lines.append(
            f"Highest margin region: {mar_hi['Region']} "
            f"({mar_hi['Margin %']}%)"
        )
    if mar_lo is not None:
        lines.append(
            f"Lowest margin region: {mar_lo['Region']} "
            f"({mar_lo['Margin %']}%)"
        )

    # Biggest profit/sales decline for regions.
    if drivers_profit["latest_month"] is not None:
        neg_reg = drivers_profit["top_negative_regions"]
        if neg_reg:
            lines.append(
                f"Biggest profit decline region: {neg_reg[0][0]} "
                f"({_fmt_change(neg_reg[0][1])})"
            )
        else:
            lines.append("Biggest profit decline region: None")
    if drivers_sales["latest_month"] is not None:
        neg_reg = drivers_sales["top_negative_regions"]
        if neg_reg:
            lines.append(
                f"Biggest sales decline region: {neg_reg[0][0]} "
                f"({_fmt_change(neg_reg[0][1])})"
            )
        else:
            lines.append("Biggest sales decline region: None")

    # Products
    rev_hi, rev_lo = _rev_name(products_df)
    prof_hi, prof_lo = _col_hi_lo(products_df, "Profit")
    mar_hi, mar_lo = _col_hi_lo(products_df, "Margin %")
    if rev_hi is not None:
        lines.append(
            f"Highest revenue product: {rev_hi['Product']} "
            f"(${rev_hi['Revenue']:,.2f})"
        )
    if rev_lo is not None:
        lines.append(
            f"Lowest revenue product: {rev_lo['Product']} "
            f"(${rev_lo['Revenue']:,.2f})"
        )
    if prof_hi is not None:
        lines.append(
            f"Highest profit product: {prof_hi['Product']} "
            f"(${prof_hi['Profit']:,.2f})"
        )
    if prof_lo is not None:
        lines.append(
            f"Lowest profit product: {prof_lo['Product']} "
            f"(${prof_lo['Profit']:,.2f})"
        )
    if mar_hi is not None:
        lines.append(
            f"Highest margin product: {mar_hi['Product']} "
            f"({mar_hi['Margin %']}%)"
        )
    if mar_lo is not None:
        lines.append(
            f"Lowest margin product: {mar_lo['Product']} "
            f"({mar_lo['Margin %']}%)"
        )

    # Biggest profit/sales decline for products.
    if drivers_profit["latest_month"] is not None:
        neg_prod = drivers_profit["top_negative_products"]
        if neg_prod:
            lines.append(
                f"Biggest profit decline product: {neg_prod[0][0]} "
                f"({_fmt_change(neg_prod[0][1])})"
            )
        else:
            lines.append("Biggest profit decline product: None")
    if drivers_sales["latest_month"] is not None:
        neg_prod = drivers_sales["top_negative_products"]
        if neg_prod:
            lines.append(
                f"Biggest sales decline product: {neg_prod[0][0]} "
                f"({_fmt_change(neg_prod[0][1])})"
            )
        else:
            lines.append("Biggest sales decline product: None")

    # Categories
    rev_hi, rev_lo = _rev_name(categories_df)
    prof_hi, prof_lo = _col_hi_lo(categories_df, "Profit")
    mar_hi, mar_lo = _col_hi_lo(categories_df, "Margin %")
    if rev_hi is not None:
        lines.append(
            f"Highest revenue category: {rev_hi['Category']} "
            f"(${rev_hi['Revenue']:,.2f})"
        )
    if rev_lo is not None:
        lines.append(
            f"Lowest revenue category: {rev_lo['Category']} "
            f"(${rev_lo['Revenue']:,.2f})"
        )
    if prof_hi is not None:
        lines.append(
            f"Highest profit category: {prof_hi['Category']} "
            f"(${prof_hi['Profit']:,.2f})"
        )
    if prof_lo is not None:
        lines.append(
            f"Lowest profit category: {prof_lo['Category']} "
            f"(${prof_lo['Profit']:,.2f})"
        )
    if mar_hi is not None:
        lines.append(
            f"Highest margin category: {mar_hi['Category']} "
            f"({mar_hi['Margin %']}%)"
        )
    if mar_lo is not None:
        lines.append(
            f"Lowest margin category: {mar_lo['Category']} "
            f"({mar_lo['Margin %']}%)"
        )

    lines.append("")
    lines.append(f"=== PROFIT DRIVERS ({drivers_profit['previous_month']} vs {drivers_profit['latest_month']}) ===")
    lines.extend(_driver_lines(df, "Profit", drivers_profit, "Profit"))

    lines.append("")
    lines.append(f"=== SALES DRIVERS ({drivers_sales['previous_month']} vs {drivers_sales['latest_month']}) ===")
    lines.extend(_driver_lines(df, "Sales", drivers_sales, "Sales"))

    return "\n".join(lines)


def build_context(df) -> str:
    """Build a compact text summary of facts from the cleaned DataFrame.

    The result is cached with st.cache_data so it is not rebuilt on
    every question.

    Args:
        df: Cleaned sales DataFrame.

    Returns:
        A multi-line string with key facts about the business.
    """
    return _cached_build_context(df)


def ask_analyst(question: str, context: str, history=None) -> tuple[str, str]:
    """Answer a business question using the configured AI provider.

    Tries the primary provider first, then falls back to the other
    provider on failure. Never exposes API keys.

    Args:
        question: The user's question.
        context: Factual summary string from build_context().
        history: Optional list of prior chat messages.

    Returns:
        (answer, provider_name) tuple.
    """
    return _try_providers(question, context, history)


def ask_analyst_stream(question: str, context: str, history=None):
    """Stream an answer from the AI provider.

    Args:
        question: The user's question.
        context: Factual summary string from build_context().
        history: Optional list of prior chat messages.

    Yields:
        Text chunks as they arrive.
    """
    yield from _try_providers_stream(question, context, history)


def get_provider_info() -> tuple[str, str]:
    """Return the active provider name and model (names only, no keys).

    Returns:
        (provider_name, model_name) tuple.
    """
    provider = _get_provider()
    client, model = _get_client_and_model(provider)
    if client is None:
        # Try to report what would be used if configured.
        if provider == "gemini":
            model = os.getenv("GEMINI_MODEL", "not set")
        else:
            model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
        return provider, model
    return provider, model
