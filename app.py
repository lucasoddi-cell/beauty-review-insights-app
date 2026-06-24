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

#Execution Function
if st.button("Analyze", type="primary"):
    if not reviews_input.strip():
        st.warning("Please paste a review to use BRIT.")
    else:
        with st.spinner("Analyzing..."):
            result = analyze_review(reviews_input)
        st.success("Analysis Successfully Completed.")
        st.caption("BRIT Analysis:")
        
        # === The headline metrics ===
        st.subheader("At a glance")
        col1, col2, col3 = st.columns(3)
        col1.metric("Inferred rating", f"{result.star_rating_inferred}/5")
        col2.metric("Sentiment", result.sentiment)
        col3.metric("Would repurchase?", result.would_repurchase)
        
        # === The quotable line (its own moment) ===
        st.subheader("Most quotable line")
        st.write(f'> "{result.most_quotable_line}"')
        
        # === Pain points and delight points side by side ===
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("Pain points")
            if result.pain_points:
                for p in result.pain_points:
                    st.write(f"- {p}")
            else:
                st.caption("None mentioned.")
        with col_right:
            st.subheader("Delight points")
            if result.delight_points:
                for d in result.delight_points:
                    st.write(f"- {d}")
            else:
                st.caption("None mentioned.")
        
        # === The full debug view (collapsed by default) ===
        with st.expander("See full structured output"):
            st.json(result.model_dump())

# Take your URL and append .json (no trailing slash)
thread_url = "https://www.reddit.com/r/MakeupAddiction/comments/1rrpr5p/some_makeup_reviews/.json"
headers = {"User-Agent": "BRIT-ReviewInsights/0.1 by [your reddit username]"}

# Take your URL and append .json (no trailing slash)
thread_url = "https://www.reddit.com/r/MakeupAddiction/comments/1rrpr5p/some_makeup_reviews/.json"
headers = {"User-Agent": "BRIT-ReviewInsights/0.1 by [your reddit username]"}

response = requests.get(thread_url, headers=headers)
print(f"Status: {response.status_code}")  # Want 200

data = response.json()
print(f"Top-level structure: list of {len(data)} items")
# data[0] is the post, data[1] is the comments

# Walk into the comments
comments_data = data[1]['data']['children']
print(f"Found {len(comments_data)} comment entries")

# Each entry has 'kind' and 'data'. 'kind' = 't1' means it's a comment.
# Extract just the body text from real comments, skip deleted/removed ones.
comments = [
    c['data']['body']
    for c in comments_data
    if c['kind'] == 't1'
    and c['data'].get('body')
    and c['data']['body'] not in ['[deleted]', '[removed]']
]

print(f"\nGot {len(comments)} usable comments\n")

# Peek at the first few
for i, c in enumerate(comments[:3], 1):
    print(f"--- Comment {i} ({len(c)} chars) ---")
    print(c[:300])
    print()





