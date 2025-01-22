import os
import re
import streamlit as st
import pdfplumber
from fuzzywuzzy import fuzz
from sklearn.metrics.pairwise import cosine_similarity
import spacy

# Load SpaCy model for NLP processing
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Function to extract structured details
def extract_details(text):
    email_regex = r"[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+"
    phone_regex = r"\b\d{10}\b"
    name_regex = r"(?i)(name[:\- ]*)([A-Z][a-z]+(?: [A-Z][a-z]+)?)"
    
    email = re.search(email_regex, text)
    phone = re.search(phone_regex, text)
    name = re.search(name_regex, text)
    
    # NLP-based entity extraction
    doc = nlp(text)
    education = " ".join([ent.text for ent in doc.ents if ent.label_ == "EDUCATION"])
    experience = " ".join([ent.text for ent in doc.ents if ent.label_ == "DATE"])
    skills = " ".join([ent.text for ent in doc.ents if ent.label_ == "SKILL"])

    details = {
        "name": name.group(2) if name else "Unknown",
        "phone": phone.group(0) if phone else "Unknown",
        "email": email.group(0) if email else "Unknown",
        "education": education,
        "experience": experience,
        "skills": skills,
    }
    return details

# Function to compute matching scores
def compute_matching_score(resume_details, required_criteria):
    score = 0
    
    # Compare Education
    score += fuzz.token_set_ratio(resume_details["education"], required_criteria["education"]) / 100
    
    # Compare Skills
    resume_skills = resume_details["skills"].split(", ")
    for skill in required_criteria["skills"]:
        max_skill_match_score = max([fuzz.token_set_ratio(skill, rs) for rs in resume_skills] + [0])
        score += max_skill_match_score / 100
    
    # Compare Experience
    resume_experience = resume_details["experience"]
    required_experience = required_criteria["experience"]

    if resume_experience and required_experience:
        # Convert experience to vectors
        resume_experience_vector = nlp(resume_experience).vector
        required_experience_vector = nlp(required_experience).vector
        
        # Ensure vectors are non-empty
        if resume_experience_vector.any() and required_experience_vector.any():
            score += cosine_similarity([resume_experience_vector], [required_experience_vector])[0][0]
    else:
        score += 0  # No experience to compare
    
    return score

# Function to filter and save resumes
def process_and_filter_resumes(uploaded_files, required_criteria, top_n):
    resume_scores = []

    for uploaded_file in uploaded_files:
        # Extract text from the PDF
        with pdfplumber.open(uploaded_file) as pdf:
            text = "".join(page.extract_text() for page in pdf.pages)
            if not text.strip():
                continue
            
            # Extract details and compute score
            details = extract_details(text)
            score = compute_matching_score(details, required_criteria)
            details["score"] = score
            
            resume_scores.append((details, uploaded_file))
    
    # Sort and filter resumes
    filtered_resumes = sorted(resume_scores, key=lambda x: x[0]["score"], reverse=True)[:top_n]
    
    # Save filtered resumes
    saved_files = []
    for details, uploaded_file in filtered_resumes:
        output_filename = f"{details['name']}_{details['phone']}_{details['email']}.pdf"
        output_filepath = os.path.join("./", output_filename)

        with open(output_filepath, "wb") as output_file:
            output_file.write(uploaded_file.read())
        saved_files.append((output_filepath, details["score"]))

    return saved_files

# Main function for Streamlit app
def main():
    st.title("Advanced Resume Filtering App")

    # Input file uploader
    uploaded_files = st.file_uploader("Upload Resumes", type=["pdf"], accept_multiple_files=True)

    # Input matching criteria
    required_education = st.text_input("Required Education")
    required_skills = st.text_input("Required Skills (comma-separated)")
    required_experience = st.text_input("Required Experience")
    top_n = st.number_input("Number of Top Resumes to Display", min_value=1, step=1, value=3)

    if st.button("Filter Resumes"):
        if uploaded_files and required_education and required_skills and required_experience:
            # Prepare criteria
            required_criteria = {
                "education": required_education,
                "skills": [skill.strip() for skill in required_skills.split(",")],
                "experience": required_experience,
            }
            # Process resumes
            matched_resumes = process_and_filter_resumes(uploaded_files, required_criteria, top_n)

            if matched_resumes:
                st.success(f"Found {len(matched_resumes)} matching resumes!")
                st.subheader("Download Filtered Resumes:")
                for filepath, score in matched_resumes:
                    st.write(f"Score: {score:.2f}")
                    st.download_button(
                        label=f"Download {os.path.basename(filepath)}",
                        data=open(filepath, "rb").read(),
                        file_name=os.path.basename(filepath),
                        mime="application/pdf",
                    )
            else:
                st.warning("No resumes matched the criteria.")
        else:
            st.error("Please upload resumes and provide matching criteria.")

if __name__ == "__main__":
    main()
