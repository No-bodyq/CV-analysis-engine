# CV Engine – Job Scraper (Person 5)
Chrome Extension | Groq AI-powered | Part of the CV Rating Engine Group Project

---

## What this does
- Adds a popup button to Chrome
- On any job listing page, click it to scrape the job text
- Sends the text to Groq AI for structured extraction
- Returns clean JSON: { title, skills[], qualifications[] }
- Can copy JSON to clipboard OR automatically send it to the group's Streamlit/Flask app

---

## How to install (Chrome)

1. Open Chrome and go to: chrome://extensions/
2. Turn ON Developer Mode (toggle, top-right)
3. Click "Load unpacked"
4. Select the cv-scraper-extension/ folder
5. Pin it by clicking the puzzle piece icon and clicking the pin next to CV Engine

---

## How to get your free Groq API Key

1. Go to https://console.groq.com/keys
2. Sign up / log in with your Google account
3. Click "Create API Key"
4. Copy the key (starts with gsk_...)
5. Paste it into the extension's API Key field and click Save

Groq is 100% free — no credit card needed, no quota issues.

---

## How to use the extension

1. Click the CV Engine icon in your Chrome toolbar
2. Paste your Groq API key and hit Save
3. Navigate to any job listing page (LinkedIn, Indeed, Jobberman, etc.)
4. Click "Scrape This Job Page"
5. The extracted job data appears — job title, skills in purple, qualifications in amber
6. Use one of the two buttons:
   - Copy JSON  → copies the data to clipboard (paste into WhatsApp or the app manually)
   - Send to App → automatically sends JSON to the group's running app at localhost:5000

---

## Output JSON format

{
  "title": "Software Engineer",
  "skills": ["Python", "REST APIs", "Docker", "Git", "NodeJS"],
  "qualifications": ["Bachelor's Degree", "3+ years experience", "Strong communication"]
}

---
---
---

# FOR PERSON 1 AND PERSON 3 — READ THIS

---

## How to receive data from Person 5's extension

When Person 5 clicks "Send to App" in the Chrome extension, it sends the scraped
job JSON automatically to your app at:

    POST http://localhost:5000/api/job-data

To receive it, you need to add a Flask endpoint to your app.
Here is exactly what to add:

---

## Step 1 — Install Flask (if not already installed)

Open your terminal and run:

    pip install flask

---

## Step 2 — Add this code to your app

Create a file called receiver.py in your project folder and paste this in:

    import json
    import os
    from flask import Flask, request

    app = Flask(__name__)

    @app.route('/api/job-data', methods=['POST'])
    def receive_job():
        data = request.json

        # Make sure the shared folder exists
        os.makedirs('shared', exist_ok=True)

        # Save the job data to a shared JSON file
        with open('shared/job_data.json', 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Job data received: {data.get('title', 'Unknown')}")
        return {"status": "ok"}

    if __name__ == '__main__':
        app.run(port=5000)

---

## Step 3 — Run the receiver alongside your Streamlit app

Open TWO terminals side by side:

Terminal 1 — run the receiver:
    python receiver.py

Terminal 2 — run your Streamlit app:
    streamlit run your_app.py

---

## Step 4 — Read the job data in your Streamlit page

Once Person 5 clicks "Send to App", the JSON is saved to shared/job_data.json.
Read it in your Streamlit page like this:

    import json
    import os

    if os.path.exists('shared/job_data.json'):
        with open('shared/job_data.json', 'r') as f:
            job_data = json.load(f)

        job_title = job_data['title']
        required_skills = job_data['skills']
        qualifications = job_data['qualifications']

        st.success(f"Job loaded: {job_title}")
        st.write("Required skills:", required_skills)
        st.write("Qualifications:", qualifications)
    else:
        st.info("Waiting for job data from Person 5's extension...")

---

## What each person does with the data

Person 1 (CV Generator):
- Use job_data['title'] and job_data['skills'] to tailor the CV generation prompt
- Example prompt: "Generate a CV for a {job_title} role highlighting these skills: {skills}"

Person 3 (Job Match Calculator):
- Use job_data['skills'] as the list of required job skills
- Compare them against the candidate's CV skills to calculate the match percentage

---

## If the app is hosted online (Streamlit Cloud)

If your app is deployed online instead of running locally, Person 5 will use the
"Copy JSON" button instead and paste the JSON directly into your app's input box.
Make sure you add a text input as a fallback like this:

    import streamlit as st
    import json

    st.subheader("Paste Job Data from Extension")
    job_json = st.text_area("Paste JSON from CV Engine Chrome Extension here")

    if job_json:
        try:
            job_data = json.loads(job_json)
            st.success(f"Job loaded: {job_data['title']}")
            st.write("Skills:", job_data['skills'])
            st.write("Qualifications:", job_data['qualifications'])
        except:
            st.error("Invalid JSON — make sure you copied it correctly from the extension")

---

## Project file structure (when everything is merged)

cv-engine-app/
├── app.py                     (main Streamlit entry point)
├── receiver.py                (Flask endpoint — run separately on port 5000)
├── pages/
│   ├── 1_cv_generator.py      (Person 1)
│   ├── 2_suggestions.py       (Person 2)
│   ├── 3_job_match.py         (Person 3 — reads from shared/job_data.json)
│   └── 4_dashboard.py         (Person 4)
└── shared/
    └── job_data.json          (written by receiver.py when extension sends data)

---

## Summary for the group

Person 1 — gets job title + skills for CV tailoring via shared/job_data.json or paste JSON
Person 3 — gets required skills for match % via shared/job_data.json or paste JSON
Person 4 — gets job title stored per session for analytics from the same JSON file

---

Built with Groq AI (llama-3.3-70b-versatile) — free tier, no credit card needed.
