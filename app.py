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
st.caption("Paste in Customer Reviews and Receive a Structured Analysis.")
st.caption("Built by Lukipuki · Week 2 of AI fluency plan")

# Input widget — returns whatever the user typed as a string
reviews_input = st.text_area(
    "Paste customer reviews here:",
    height=200,
    placeholder="One review per line, or separate with ---REVIEW---"
)
#Pydantic Class
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

#Analysis Function
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

#testanalysis
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
            
tab1, tab2, tab3 = st.tabs([
    "Paste Reviews",
    "Bazaarvoice",
    "Reddit",
])

#Execution Function
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
            with st.spinner(f"Fetching {n} reviews from Bazaarvoice..."):
                reviews = get_bazaarvoice_reviews(product_id.strip(), limit=n)
            
            if not reviews:
                st.error("No reviews returned. Check the Product ID and try again.")
            else:
                st.success(f"Got {len(reviews)} reviews. Analyzing...")
                progress = st.progress(0)
                
                for i, review in enumerate(reviews, 1):
                    try:
                        result = analyze_review(review)
                        header = f"Review {i} — {result.sentiment} ({result.star_rating_inferred}/5)"
                        with st.expander(header):
                            st.caption(review[:250] + "..." if len(review) > 250 else review)
                            display_analysis(result)
                    except Exception as e:
                        st.error(f"Review {i} failed: {e}")
                    progress.progress(i / len(reviews))
                
                st.success(f"Done — analyzed {len(reviews)} reviews.")



with tab3:
    st.caption("Reddit Analysis:")
    st.info("Reddit integration awaits Reddit API approval.")
