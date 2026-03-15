"""
Script to update questions_draft.json for the 2026 Google Cloud Professional 
Cloud Architect exam by:
1. Removing questions about deprecated/legacy technologies
2. Updating renamed service names throughout
3. Re-numbering question IDs
"""

import json
import re
import os

DRAFT_FILE = 'questions_draft.json'
FINAL_FILE = 'questions.json'

with open(DRAFT_FILE, 'r', encoding='utf-8') as f:
    questions = json.load(f)

print(f"Starting with {len(questions)} questions")

# ── Questions to REMOVE ──────────────────────────────────────────────────────
# Reasons: broken image refs, deprecated services as correct answer, fundamentally
# outdated technology that wouldn't appear on the 2026 exam
REMOVE_IDS = {
    # Broken image references (question can't be answered without the image)
    4,   # App Engine code screenshot ![][image1]
    22,  # Dockerfile screenshot ![][image2] + "Google Container Engine"
    38,  # App Engine Java stack trace ![][image3]
    120, # Network diagram ![][image4]

    # VM access scopes as correct answer – IAM roles on service accounts is the
    # modern approach; scopes are legacy
    10,

    # Cloud Deployment Manager – being sunset in favor of Terraform/IaC Manager
    30,

    # Cloud Datalab – deprecated, replaced by Vertex AI Workbench / Colab Enterprise
    48,

    # Cloud Datastore indexes via gcloud datastore – now Firestore
    51,

    # Cloud ML Engine – replaced by Vertex AI
    58,

    # Cloud Datastore batch get – now Firestore
    64,

    # Memcache backed by Cloud Datastore – both legacy/deprecated
    86,

    # Cloud Machine Learning Engine performance metrics – replaced by Vertex AI
    92,

    # App Engine Memcache service – deprecated
    99,

    # Cloud Run for Anthos – rebranded to Cloud Run / GKE
    106,

    # GKE On-Prem – rebranded to GKE Enterprise
    110,

    # Anthos clusters + Anthos Config Management + Anthos Service Mesh old naming
    124,

    # Cloud Debugger – deprecated
    139,

    # kubemci – deprecated tool, replaced by Multi Cluster Gateway
    154,

    # Google Cloud Datastore + Google Container Engine – legacy names, 
    # entire question framed around legacy
    168,
}

# Filter out removed questions
filtered = [q for q in questions if q['id'] not in REMOVE_IDS]
print(f"After removing {len(REMOVE_IDS)} legacy questions: {len(filtered)} remain")

# ── Service Name Replacements ────────────────────────────────────────────────
# These are the rebranding changes that happened over the years
REPLACEMENTS = [
    # Stackdriver → Cloud Operations suite
    ("Stackdriver Trace", "Cloud Trace"),
    ("Stackdriver Logging", "Cloud Logging"),
    ("Stackdriver Monitoring", "Cloud Monitoring"),
    ("Stackdriver Debugger", "Cloud Debugger (deprecated)"),
    ("Stackdriver", "Cloud Operations"),    # catch-all for remaining refs
    ("Google StackDriver", "Cloud Operations"),
    ("Google Stackdriver", "Cloud Operations"),

    # Sunset/Deprecated Services
    ("Cloud IoT Core", "Cloud IoT Core (deprecated)"),
    ("Cloud Datalab", "Vertex AI Workbench"),

    # Google Container Engine → GKE
    ("Google Container Engine", "Google Kubernetes Engine"),
    ("Container Engine", "Kubernetes Engine"),

    # G Suite → Google Workspace
    ("G Suite", "Google Workspace"),

    # Data Platform
    # Cloud Datastore → Firestore (where appropriate, keep if in option text)
    ("Cloud Datastore", "Firestore in Datastore mode"),

    # Data Studio → Looker Studio
    ("Google Data Studio", "Looker Studio"),
    ("Data Studio", "Looker Studio"),

    # Security & Identity
    # Cloud Data Loss Prevention API → Sensitive Data Protection
    ("Cloud Data Loss Prevention API", "Sensitive Data Protection API"),
    ("Cloud Data Loss Prevention (Cloud DLP) API", "Sensitive Data Protection (formerly DLP) API"),
    ("Cloud Data Loss Prevention (DLP) API", "Sensitive Data Protection API"),
    ("the DLP API", "the Sensitive Data Protection API"),

    # Container Registry → Artifact Registry
    ("Container Registry", "Artifact Registry"),

    # Migration
    # Migrate for Compute Engine → Migrate to Virtual Machines
    ("Migrate for Compute Engine", "Migrate to Virtual Machines"),
    # Migrate for Anthos -> Migrate to Containers
    ("Migrate for Anthos", "Migrate to Containers"),

    # General Service Name Consistency (Google Cloud X -> Cloud X)
    # Cloud Pub/Sub consistency (minor)
    ("Google Cloud Pub/Sub", "Cloud Pub/Sub"),

    # Anthos rebranding
    ("Anthos clusters (formerly Anthos GKE)", "GKE Enterprise clusters"),
    ("Anthos GKE", "GKE Enterprise"),
    ("Cloud Run for Anthos", "Cloud Run on GKE"),
    ("Anthos Service Mesh", "Cloud Service Mesh"),
    ("Anthos Config Management", "Config Management"),

    # Networking consistency
    ("Google Cloud Armor", "Cloud Armor"),
    ("Google Cloud DNS", "Cloud DNS"),
    ("Google Cloud Router", "Cloud Router"),
    ("Google Cloud VPN", "Cloud VPN"),
    ("Google Cloud Interconnect", "Cloud Interconnect"),
    ("Google Cloud Load Balancing", "Cloud Load Balancing"),
    ("Cloud CDN", "Cloud CDN"),

    # GCP Console
    ("GCP Console", "Google Cloud Console"),
    ("Cloud Platform Console", "Google Cloud Console"),

    # Storage & Database consistency
    ("Google Cloud Storage", "Cloud Storage"),
    ("Cloud Filestore", "Filestore"),
    ("Cloud Memorystore", "Memorystore"),

    # gcloud alpha container → gcloud container (now GA)
    ("gcloud alpha container clusters", "gcloud container clusters"),
]

def apply_replacements(text):
    """Apply all service name replacements to a string."""
    if not text:
        return text
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    return text

def update_question(q):
    """Update all text fields in a question dict."""
    q['text'] = apply_replacements(q.get('text', ''))
    q['context'] = apply_replacements(q.get('context', ''))
    q['explanation'] = apply_replacements(q.get('explanation', ''))
    for opt in q.get('options', []):
        opt['text'] = apply_replacements(opt.get('text', ''))
    return q

# Apply replacements to all remaining questions
for q in filtered:
    update_question(q)

# ── Specific question rewrites ───────────────────────────────────────────────

# Q3: Update "Stackdriver Debugger" reference in the migration practices question
# Already handled by replacements above, but let's verify the explanation
for q in filtered:
    if q['number'] == '3':
        q['explanation'] = q['explanation'].replace(
            "Instrumenting with Cloud Debugger (deprecated)",
            "Instrumenting with Cloud Monitoring/Logging"
        )
    
    # Q5: Update option A about "StackDriver logging agent"
    if q['number'] == '5':
        for opt in q['options']:
            if opt['label'] == 'A':
                opt['text'] = "Direct them to download and install the Cloud Logging agent (Ops Agent)"
    
    # Q11: Already handled by G Suite → Google Workspace replacement
    
    # Q13: Already handled by Stackdriver → Cloud Operations replacements
    
    # Q17: Update gsutil reference to mention gcloud storage as alternative
    if q['number'] == '17':
        q['explanation'] = q['explanation'].replace(
            "A lifecycle management rule in JSON pushed with gsutil (B)",
            "A lifecycle management rule in JSON pushed with gsutil or gcloud storage (B)"
        )
    
    # Q24: Already handled by Stackdriver → Cloud Trace/Monitoring replacements
    
    # Q26: Already handled
    
    # Q34: Already handled
    
    # Q66: Already handled (Stackdriver + Data Studio)
    
    # Q69: Already handled
    
    # Q73: Already handled
    
    # Q75: Already handled
    
    # Q84: Update to prefer Terraform over Deployment Manager
    if q['number'] == '84':
        for opt in q['options']:
            if opt['label'] == 'B':
                opt['text'] = "Create a custom VM image with all OS package dependencies. Use Terraform to create the managed instance group with the VM image."
        q['explanation'] = "Using a pre-baked custom image with all dependencies pre-installed (B) minimizes startup time. Terraform (or similar IaC) automates the MIG creation. Startup scripts (A) install packages at boot, adding significant delay. Puppet (C) and Ansible (D) are configuration management tools that also add startup overhead."
    
    # Q96: Update Deployment Manager reference
    if q['number'] == '96':
        for opt in q['options']:
            if 'Deployment Manager' in opt.get('text', ''):
                opt['text'] = opt['text'].replace('Deployment Manager', 'Terraform')
        q['explanation'] = q['explanation'].replace('Deployment Manager', 'Terraform')
    
    # Q100: App Engine Cron → Cloud Scheduler
    if q['number'] == '100':
        q['text'] = q['text'].replace(
            "Leveraging Google best practices, what should you do?",
            "Leveraging Google-recommended practices, what should you do?"
        )
        for opt in q['options']:
            if 'Cron service provided by App Engine' in opt.get('text', ''):
                opt['text'] = opt['text'].replace(
                    'Cron service provided by App Engine',
                    'Cloud Scheduler'
                )
            if 'Cron service provided by Google Kubernetes Engine (GKE)' in opt.get('text', ''):
                opt['text'] = opt['text'].replace(
                    'Cron service provided by GKE',
                    'Cron service provided by Google Kubernetes Engine (GKE)'
                )
    
    # Q126: Container Registry → Artifact Registry (already handled by replacements)
    
    # Q167: gcloud alpha → gcloud (already handled by replacements)

# ── Re-number IDs sequentially ───────────────────────────────────────────────
for i, q in enumerate(filtered, start=1):
    q['id'] = i

# ── Save ─────────────────────────────────────────────────────────────────────
with open(FINAL_FILE, 'w', encoding='utf-8') as f:
    json.dump(filtered, f, indent=4, ensure_ascii=False)

print(f"\nSaved {len(filtered)} updated questions to {FINAL_FILE}")
print("\nRemoved questions (by original number):")
for q_id in sorted(REMOVE_IDS):
    print(f"  - Original Q#{q_id}")
print("\nService name updates applied:")
for old, new in REPLACEMENTS:
    print(f"  '{old}' → '{new}'")
