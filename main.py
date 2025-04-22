import streamlit as st
import base64
from response import main

# Streamlit app configuration
st.set_page_config(page_title="Property Chatbot", layout="centered")

# Chatbot title
st.title("Property Chatbot")
st.write("Ask your questions about property issues or tenancy FAQs. Optionally, upload an image for issue detection.")

# Input fields
user_query = st.text_input("Enter your query:", placeholder="Type your question here...")
uploaded_image = st.file_uploader("Upload an image (optional):", type=["jpg", "jpeg", "png"])

# Submit button
if st.button("Submit"):
    if not user_query.strip():
        st.error("Please enter a query.")
    else:
        # Process the uploaded image if provided
        image_data = None
        if uploaded_image:
            image_bytes = uploaded_image.read()
            image_data = base64.b64encode(image_bytes).decode("utf-8")

        # Call the generate_response function
        try:
            response = main(user_query,image_data)
            # if general_flag == 1:
            #     st.warning("The query could not be classified into a specific category.")
            # else:
            st.success("Response:")
            st.write(response)
        except Exception as e:
            st.error(f"An error occurred: {e}")