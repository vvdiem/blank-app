import streamlit as st
from groq import Groq

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ── EMAILS ───────────────────────────────────────────
EMAILS = [
    {"id": 1, "from": "sarah.kim@techcorp.com", "subject": "Account login not working", "body": "I've been locked out for 2 hours and have a presentation tomorrow. Please help ASAP!"},
    {"id": 2, "from": "billing@acmecorp.com", "subject": "Invoice #4821 overdue — final notice", "body": "This is a final notice. Invoice for $3,450 is 45 days past due. Pay within 5 days or service will be suspended."},
    {"id": 3, "from": "james.wu@gmail.com", "subject": "Question about enterprise plan", "body": "Hi, I'm evaluating options for my team of 50. Could you send pricing info? No rush."},
    {"id": 4, "from": "ops@clientco.com", "subject": "Schedule Q3 review meeting", "body": "We're available Tuesday or Thursday next week 2-4pm EST. Please confirm and send a calendar invite."},
    {"id": 5, "from": "dev@startup.io", "subject": "API rate limit hit — service degraded", "body": "URGENT: We've been hitting rate limits since 3am. Our service is down for all users. Please help immediately."},
]

# ── HELPER ───────────────────────────────────────────
def ask(prompt):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()
# ── AGENTS ───────────────────────────────────────────
def agent_classify(email):
    return ask(f"Classify this email into one of: Customer Inquiry, Scheduling Request, Billing, Technical Support, General. Reply with ONLY the category name.\n\nSubject: {email['subject']}\nBody: {email['body']}")

def agent_priority(email, category):
    import json
    raw = ask(f"Assign a priority (High, Medium, or Low) to this email. Reply in JSON only: {{\"priority\": \"...\", \"reason\": \"one sentence\"}}\n\nCategory: {category}\nSubject: {email['subject']}\nBody: {email['body']}")
    return json.loads(raw.replace("```json","").replace("```","").strip())

def agent_draft(email, category, priority):
    return ask(f"Write a 2-3 sentence professional reply to this email. Reply with the email text only.\n\nCategory: {category}, Priority: {priority}\nSubject: {email['subject']}\nBody: {email['body']}")

def agent_review(draft, category, priority):
    import json
    raw = ask(f"Review this draft reply. Reply in JSON only: {{\"approved\": true or false, \"note\": \"one sentence\"}}\n\nCategory: {category}, Priority: {priority}\nDraft: {draft}")
    return json.loads(raw.replace("```json","").replace("```","").strip())

# ── PIPELINE ─────────────────────────────────────────
def run_pipeline(email):
    results = {}
    with st.status("Running pipeline...", expanded=True) as status:
        st.write("Agent 1 — Classifying...")
        results["category"] = agent_classify(email)
        st.write(f"→ {results['category']}")

        st.write("Agent 2 — Prioritizing...")
        p = agent_priority(email, results["category"])
        results["priority"] = p["priority"]
        results["reason"] = p["reason"]
        st.write(f"→ {results['priority']}")

        st.write("Agent 3 — Drafting response...")
        results["draft"] = agent_draft(email, results["category"], results["priority"])
        st.write("→ Draft ready")

        st.write("Agent 4 — Reviewing...")
        review = agent_review(results["draft"], results["category"], results["priority"])
        results["approved"] = review["approved"]
        results["review_note"] = review["note"]
        st.write(f"→ {'Approved' if review['approved'] else 'Needs revision'}")

        status.update(label="Done!", state="complete")
    return results

# ── SESSION STATE ─────────────────────────────────────
if "results" not in st.session_state:
    st.session_state.results = {}

# ── UI ────────────────────────────────────────────────
st.title("Email Triage Assistant")
st.caption("4-agent pipeline: Classify → Priority → Draft → Review")
st.divider()

col1, col2 = st.columns(2)
with col1:
    if st.button("Run All Emails", type="primary", use_container_width=True):
        for email in EMAILS:
            if email["id"] not in st.session_state.results:
                st.session_state.results[email["id"]] = run_pipeline(email)
        st.rerun()
with col2:
    if st.button("Reset", use_container_width=True):
        st.session_state.results = {}
        st.rerun()

st.divider()

selected = st.selectbox("Or pick one email to process", [e["subject"] for e in EMAILS])
email = next(e for e in EMAILS if e["subject"] == selected)

st.write(f"**From:** {email['from']}")
st.write(f"**Body:** {email['body']}")

if email["id"] not in st.session_state.results:
    if st.button("Run Pipeline", type="primary"):
        st.session_state.results[email["id"]] = run_pipeline(email)
        st.rerun()
else:
    r = st.session_state.results[email["id"]]
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Category", r["category"])
    c2.metric("Priority", r["priority"])
    c3.metric("Reviewer", "Approved" if r["approved"] else "Flagged")
    st.write(f"**Reason:** {r['reason']}")
    st.write(f"**Reviewer note:** {r['review_note']}")
    st.info(r["draft"])

st.divider()
st.write("**Inbox summary**")
for e in EMAILS:
    r = st.session_state.results.get(e["id"])
    if r:
        icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(r["priority"], "⚪")
        st.write(f"{icon} {e['subject']} · {r['category']} · {r['priority']}")
    else:
        st.write(f"⬜ {e['subject']} — not processed")