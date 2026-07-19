import streamlit as st
from anthropic import Anthropic 
from pydantic import BaseModel, Field
from typing import Literal
import requests

client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# Defining the ask_claude function (pulled from Colab)
def ask_claude(prompt, system="You are a helpful assistant."):
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4000,
        system=system,
        messages=[
            {"role": "user", "content": prompt},
        ]
    )
    return message.content[0].text

#UI
st.title("Welcome to BRIT - Beauty Review Insights Tool")
st.caption("Structured analysis of beauty product reviews from any source.")
st.caption("Built by Lukipuki · Week 2 of AI fluency plan")

# ============================================================
# Schemas
# ============================================================

class FullReviewAnalysis(BaseModel):
    """Structured analysis of a single beauty product review."""

    sentiment: Literal["positive", "mixed", "negative"] = Field(
        description="Overall tone of the review."
    )

    star_rating_inferred: int = Field(
        description="What the reviewer probably would have rated 1-5.",
        ge=1, le=5
    )

    main_themes: list[str] = Field(
        description="Up to 3 short phrases describing what the review is about. E.g. 'texture', 'scent', 'price-to-results ratio'.",
        max_length=3
    )

    pain_points: list[str] = Field(
        description="Specific complaints from the reviewer. Empty list if none. Each phrase under 12 words."
    )

    delight_points: list[str] = Field(
        description="Specific things the reviewer loves. Empty list if none. Each phrase under 12 words."
    )

    price_sensitivity: Literal["concern", "acceptable", "not_mentioned"] = Field(
        description="How the reviewer frames price."
    )

    would_repurchase: Literal["yes", "no", "unclear"] = Field(
        description="Whether the reviewer signals they'd buy again."
    )

    user_suggestion: list[str] = Field(
        description="Specific suggestions for product improvements from the reviewer. Empty list if none. Each phrase under 12 words."
    )

    product_compare: list[str] = Field(
        description="Other brands or products mentioned in the review. Empty list if none. Each phrase under 12 words."
    )

    most_quotable_line: str = Field(
        description="The single most marketing-quotable sentence, verbatim. Empty string if none usable."
    )

    confidence_level: Literal["high", "medium", "low"] = Field(
        description="How confident you are in the sentiment signal analysis. High = unambiguous sentiment, clear opinions, consistent throughout. Medium = some ambiguity, contradictions, or sarcasm. Low = very short, self-contradictory, or sarcastic to the point you can't tell the actual opinion."
    )


class ThemeCluster(BaseModel):
    """A single clustered theme across multiple reviews."""

    theme_name: str = Field(
        description="Short 3-6 word label for this cluster of related mentions. E.g. 'creases under eyes', 'long-lasting formula', 'strong chemical scent'."
    )
    mention_count: int = Field(
        description="How many of the analyzed reviews touched on this theme.",
        ge=1
    )
    top_quote: str = Field(
        description="The single most representative verbatim mention from the reviews, under 25 words. Should feel like a quotable example of this theme."
    )


class ProductSummary(BaseModel):
    """Cross-review executive summary for a single product."""

    overall_sentiment: Literal["positive", "mostly_positive", "mixed", "mostly_negative", "negative"] = Field(
        description="Cross-review sentiment. Not the average of numeric ratings — the qualitative gestalt."
    )

    pain_themes: list[ThemeCluster] = Field(
        description="Top 3 clusters of pain points, ranked by mention_count descending. Cluster similar complaints together (e.g. 'creases' and 'settles into fine lines' are one theme). Max 3.",
        max_length=3
    )

    delight_themes: list[ThemeCluster] = Field(
        description="Top 3 clusters of delight points, ranked by mention_count descending. Cluster similar praise together. Max 3.",
        max_length=3
    )

    strategic_takeaway: str = Field(
        description="2-3 sentences: what does the pattern of feedback mean for the brand? Focus on tension between what customers love and what frustrates them. Not a rehash of the themes — the interpretation."
    )

    recommended_action: str = Field(
        description="1-2 sentences: what should a marketing or product team DO based on this? Should be specific and actionable, not generic ('improve product'). Reference the actual themes."
    )


# ============================================================
# Analysis functions
# ============================================================

def analyze_review(reviews_text):
    """Take a review string, return a FullReviewAnalysis object."""
    response = client.messages.parse(
        model="claude-haiku-4-5",
        max_tokens=1500,
        system="You are a senior consumer insights analyst at a prestige beauty company. Extract structured insight from customer reviews. Be specific. Quote verbatim where the schema asks for it.",
        messages=[
            {"role": "user", "content": f"Analyze this beauty product review:\n\n{reviews_text}"}
        ],
        output_format=FullReviewAnalysis
    )
    return response.parsed_output


def summarize_product_reviews(analyses: list[FullReviewAnalysis]) -> ProductSummary:
    """Take a list of per-review analyses, return an aggregated ProductSummary.
    
    Uses the already-extracted pain_points and delight_points as input rather than
    re-reading raw reviews. Cheaper, and closes the loop on the earlier analysis.
    """
    digest_lines = []
    for i, a in enumerate(analyses, 1):
        line = (
            f"Review {i}: sentiment={a.sentiment}, "
            f"pain={a.pain_points}, "
            f"delight={a.delight_points}, "
            f"repurchase={a.would_repurchase}, "
            f"quote=\"{a.most_quotable_line}\""
        )
        digest_lines.append(line)
    digest = "\n".join(digest_lines)

    response = client.messages.parse(
        model="claude-haiku-4-5",
        max_tokens=2500,
        system=(
            "You are a senior consumer insights analyst preparing a brief for a "
            "prestige beauty brand's marketing team. You cluster mentions across "
            "reviews into themes (not verbatim buckets — semantic ones), rank by "
            "frequency, and translate patterns into strategic implications. Never "
            "invent quotes; only use verbatim quotes present in the input."
        ),
        messages=[
            {"role": "user", "content": (
                f"Here are {len(analyses)} structured analyses of customer reviews "
                f"for one product:\n\n{digest}\n\n"
                "Produce a cross-review executive summary. Cluster similar pain points "
                "into up to 3 themes; same for delight points. For each theme's top_quote, "
                "pick the most representative verbatim line from the actual reviews above. "
                "In strategic_takeaway, focus on the tension between what customers love "
                "and what frustrates them. In recommended_action, be specific and reference "
                "actual themes."
            )}
        ],
        output_format=ProductSummary
    )
    return response.parsed_output


# ============================================================
# Data fetchers
# ============================================================

def is_incentivized(raw_review: dict) -> bool:
    """Check if a Bazaarvoice review was incentivized (e.g. Sephora sample program).
    
    Uses defensive dict access — some older reviews are missing the field entirely.
    Returns False if the field can't be found (safer to include than exclude).
    """
    try:
        value = raw_review["ContextDataValues"]["IncentivizedReview"]["Value"]
        return value is True or (isinstance(value, str) and value.lower() == "true")
    except (KeyError, TypeError):
        return False


def get_bazaarvoice_reviews(product_id: str, limit: int = 20) -> tuple[list[str], int]:
    """Fetch reviews from Sephora's Bazaarvoice endpoint, excluding incentivized ones.

    Returns:
        A tuple of (list of review body text strings, count of excluded incentivized reviews).
        Both empty/zero on any failure.
    """
    base_url = "https://api.bazaarvoice.com/data/reviews.json"
    params = {
        "apiversion": "5.5",
        "passkey": "calXm2DyQVjcCy9agq85vmTJv5ELuuBCF2sdg4BnJzJus",  # <-- paste your passkey from the DevTools URL
        "Filter": f"ProductId:{product_id}",
        "Sort": "SubmissionTime:desc",
        "Limit": limit,
        "Offset": 0,
    }
    try:
        response = requests.get(base_url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"Bazaarvoice returned {response.status_code}")
            return [], 0
        data = response.json()
    except Exception as e:
        print(f"Bazaarvoice request failed: {e}")
        return [], 0

    reviews = []
    excluded_count = 0
    for r in data.get("Results", []):
        if not r.get("ReviewText"):
            continue
        if is_incentivized(r):
            excluded_count += 1
            continue
        reviews.append(r["ReviewText"])

    return reviews, excluded_count


# ============================================================
# Display helpers
# ============================================================

def display_analysis(result):
    """Render one FullReviewAnalysis result as metrics + quotable + pain/delight."""
    col1, col2, col3 = st.columns(3)
    col1.metric("Inferred rating", f"{result.star_rating_inferred}/5")
    col2.metric("Sentiment", result.sentiment)
    col3.metric("Would repurchase?", result.would_repurchase)
    
    if result.most_quotable_line:
        st.write(f'> "{result.most_quotable_line}"')
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.caption("Pain points")
        if result.pain_points:
            for p in result.pain_points:
                st.write(f"- {p}")
        else:
            st.caption("None mentioned.")
    with col_right:
        st.caption("Delight points")
        if result.delight_points:
            for d in result.delight_points:
                st.write(f"- {d}")
        else:
            st.caption("None mentioned.")


def display_product_summary(summary: ProductSummary, analyses: list[FullReviewAnalysis]):
    """Render the cross-review ProductSummary at the top of the tab."""
    n = len(analyses)
    
    positive_count = sum(1 for a in analyses if a.sentiment == "positive")
    repurchase_count = sum(1 for a in analyses if a.would_repurchase == "yes")
    avg_rating = sum(a.star_rating_inferred for a in analyses) / n
    
    st.subheader(f"Product Summary — {n} reviews analyzed")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Overall", summary.overall_sentiment.replace("_", " "))
    col2.metric("% Positive", f"{100 * positive_count / n:.0f}%")
    col3.metric("% Repurchase", f"{100 * repurchase_count / n:.0f}%")
    col4.metric("Avg rating", f"{avg_rating:.1f}/5")
    
    st.markdown("**Strategic takeaway**")
    st.write(summary.strategic_takeaway)
    st.markdown("**Recommended action**")
    st.write(summary.recommended_action)
    
    col_pain, col_delight = st.columns(2)
    
    with col_pain:
        st.markdown("**Top pain themes**")
        if summary.pain_themes:
            for i, theme in enumerate(summary.pain_themes, 1):
                st.write(f"**{i}. {theme.theme_name}** ({theme.mention_count} mentions)")
                st.caption(f'"{theme.top_quote}"')
        else:
            st.caption("No pain themes surfaced.")
    
    with col_delight:
        st.markdown("**Top delight themes**")
        if summary.delight_themes:
            for i, theme in enumerate(summary.delight_themes, 1):
                st.write(f"**{i}. {theme.theme_name}** ({theme.mention_count} mentions)")
                st.caption(f'"{theme.top_quote}"')
        else:
            st.caption("No delight themes surfaced.")


# ============================================================
# Tabs
# ============================================================

tab1, tab2, tab3 = st.tabs([
    "Paste Reviews",
    "Bazaarvoice",
    "Reddit",
])

# ===== Tab 1: paste flow =====
with tab1:
    reviews_input = st.text_area(
        "Paste customer reviews here:",
        height=200,
        placeholder="One review per line, or separate with ---REVIEW---",
        key="paste_input"
    )
    
    if st.button("Analyze", type="primary", key="paste_analyze"):
        if not reviews_input.strip():
            st.warning("Please paste a review to use BRIT.")
        else:
            with st.spinner("Analyzing..."):
                result = analyze_review(reviews_input)
            st.success("Analysis Successfully Completed.")
            display_analysis(result)

# ===== Tab 2: Bazaarvoice (Sephora) flow =====
with tab2:
    st.caption("Find the Product ID in the Sephora URL — e.g. P443563 from Glowy Lip Balm")
    
    product_id = st.text_input(
        "Product ID",
        placeholder="P443563",
        key="sephora_product_id"
    )
    
    n = st.number_input(
        "How many reviews to analyze",
        min_value=1,
        max_value=30,
        value=15,
        key="sephora_limit"
    )
    
    if st.button("Fetch & Analyze", type="primary", key="sephora_analyze"):
        if not product_id.strip():
            st.warning("Please enter a Sephora Product ID.")
        else:
            # Step 1 — fetch (returns tuple: reviews + excluded count)
            with st.spinner(f"Fetching {n} reviews from Bazaarvoice..."):
                reviews, excluded = get_bazaarvoice_reviews(product_id.strip(), limit=n)
            
            if not reviews:
                st.error("No organic reviews returned. Check the Product ID and try again.")
            else:
                # Report exclusion transparently
                if excluded > 0:
                    st.info(
                        f"Excluded {excluded} incentivized review{'s' if excluded != 1 else ''} "
                        f"(Sephora sample program). Analyzing {len(reviews)} organic reviews..."
                    )
                else:
                    st.success(f"Got {len(reviews)} organic reviews. Analyzing individually...")
                
                # Step 2 — analyze each review, collect results
                progress = st.progress(0)
                analyses = []
                paired = []  # (review_text, analysis) pairs for the expander block below
                
                for i, review in enumerate(reviews, 1):
                    try:
                        result = analyze_review(review)
                        analyses.append(result)
                        paired.append((review, result))
                    except Exception as e:
                        st.error(f"Review {i} failed: {e}")
                    progress.progress(i / len(reviews))
                
                if not analyses:
                    st.error("Every review analysis failed. Nothing to summarize.")
                else:
                    # Step 3 — cross-review summary
                    with st.spinner("Generating executive summary..."):
                        try:
                            summary = summarize_product_reviews(analyses)
                            display_product_summary(summary, analyses)
                        except Exception as e:
                            st.error(f"Summary generation failed: {e}")
                    
                    # Step 4 — individual reviews nested in one expander
                    st.divider()
                    with st.expander(f"See all {len(paired)} individual review analyses"):
                        for i, (review_text, result) in enumerate(paired, 1):
                            st.markdown(f"**Review {i} — {result.sentiment} ({result.star_rating_inferred}/5)**")
                            st.caption(review_text[:250] + "..." if len(review_text) > 250 else review_text)
                            display_analysis(result)
                            if i < len(paired):
                                st.divider()

# ===== Tab 3: Reddit (pending approval) =====
with tab3:
    st.caption("Reddit Analysis:")
    st.info("Reddit integration awaits Reddit API approval.")
