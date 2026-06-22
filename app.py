import streamlit as st

st.title("Welcome to BRIT - Beauty Review Insight Tool")
st.caption("Paste in Customer Reviews and Receive a Structured Analysis")
st.caption("Built by Lukipuki · Week 2 of AI fluency plan")

# Input widget — returns whatever the user typed as a string
reviews_input = st.text_area(
    "Paste customer reviews here:",
    height=200,
    placeholder="One review per line, or separate with ---REVIEW---"
)

# Button — returns True only on the run when it was just clicked
if st.button("Analyze", type="primary"):
    if not reviews_input.strip():
        st.warning("Please paste reviews first.")
    else:
        st.success(f"Reviews successfully inputted.")
        st.write("Analysis coming.")
