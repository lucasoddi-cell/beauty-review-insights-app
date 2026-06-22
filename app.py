import streamlit as st
from anthropic import Anthropic 

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

if st.button("Analyze", type="primary"):
    if not reviews_input.strip():
        st.warning("Please paste a review to use BRIT.")
    else:
        with st.spinner("Analyzing..."):
            response = ask_claude(
                prompt=f"You are a senior consumer insights analyst. Extract structured insight from customer reviews. Be specific. Quote verbatim where You are a senior consumer insights analyst at a prestige beauty company. Extract structured insight from customer reviews. Be specific. Quote verbatim where the schema asks for it..:\n\n{reviews_input}",
                system="You are a senior consumer insights analyst."
            )
        st.success("Reviews successfully inputted.")
        st.caption("BRIT Analysis:")
        st.write(response)





