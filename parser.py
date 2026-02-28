"""
Parser for Cloud Architect Prep App.
Primary source: ref_cloud_architect_qa.md
Each question is tagged with a GCP Professional Cloud Architect exam domain.
"""

import re
import json
import os

QA_FILE = "ref_cloud_architect_qa.md"
OUTPUT  = "questions.json"

# ------------------------------------------------------------------
# Domain classification: maps question numbers to exam domains.
# Based on the Google Cloud Professional Cloud Architect Exam Guide.
# Domains:
#   1. Designing and Planning a Cloud Solution Architecture
#   2. Managing and Provisioning Infrastructure
#   3. Designing for Security and Compliance
#   4. Analyzing and Optimizing Technical and Business Processes
#   5. Managing Implementation
#   6. Ensuring Solution and Operations Reliability
# ------------------------------------------------------------------
DOMAIN_MAP = {
    # Q1  - API versioning / Load Balancing → Design & Plan
    "1":   "Designing and Planning",
    # Q2  - BigQuery for petabyte SQL → Design & Plan
    "2":   "Designing and Planning",
    # Q3  - Migration best practices → Managing Implementation
    "3":   "Managing Implementation",
    # Q4  - App Engine session state → Operations Reliability
    "4":   "Operations Reliability",
    # Q5  - Logging tool selection → Operations Reliability
    "5":   "Operations Reliability",
    # Q6  - Deployment strategies (blue/green, canary) → Managing Implementation
    "6":   "Managing Implementation",
    # Q7  - Cost visibility, VM lifecycle → Optimizing Processes
    "7":   "Optimizing Processes",
    # Q8  - IoT / NoSQL database choice → Designing and Planning
    "8":   "Designing and Planning",
    # Q9  - Load balancer health checks / firewall → Managing Infrastructure
    "9":   "Managing Infrastructure",
    # Q10 - BigQuery access from VM / scopes → Security and Compliance
    "10":  "Security and Compliance",
    # Q11 - SSO / SAML / identity federation → Security and Compliance
    "11":  "Security and Compliance",
    # Q12 - Dataflow batch+stream → Designing and Planning
    "12":  "Designing and Planning",
    # Q13 - App Engine latency investigation → Operations Reliability
    "13":  "Operations Reliability",
    # Q14 - Persistent disk resize with zero downtime → Managing Infrastructure
    "14":  "Managing Infrastructure",
    # Q15 - PCI compliance tokenization → Security and Compliance
    "15":  "Security and Compliance",
    # Q16 - Bigtable for high-throughput click data → Designing and Planning
    "16":  "Designing and Planning",
    # Q17 - GCS lifecycle rules → Optimizing Processes
    "17":  "Optimizing Processes",
    # Q18 - Spark/Hadoop to Dataproc → Managing Infrastructure
    "18":  "Managing Infrastructure",
    # Q19 - Database performance (SSD resize) → Managing Infrastructure
    "19":  "Managing Infrastructure",
    # Q20 - Bigtable for sensor data → Designing and Planning
    "20":  "Designing and Planning",
    # Q21 - Resiliency / chaos testing → Operations Reliability
    "21":  "Operations Reliability",
    # Q22 - Docker build optimization → Managing Implementation
    "22":  "Managing Implementation",
    # Q23 - Canary releases for prod bugs → Managing Implementation
    "23":  "Managing Implementation",
    # Q24 - Stackdriver Trace / distributed tracing → Operations Reliability
    "24":  "Operations Reliability",
    # Q25 - Database failover scheduling → Operations Reliability
    "25":  "Operations Reliability",
    # Q26 - Log retention 5 years → Security and Compliance
    "26":  "Security and Compliance",
    # Q27 - Dedicated Interconnect for large DB → Managing Infrastructure
    "27":  "Managing Infrastructure",
    # Q28 - IAM audit logging export → Security and Compliance
    "28":  "Security and Compliance",
    # Q29 - Secret management → Security and Compliance
    "29":  "Security and Compliance",
    # Q30 - Deployment Manager adoption risks → Optimizing Processes
    "30":  "Optimizing Processes",
    # Q31 - GKE + Jenkins + Helm → Managing Implementation
    "31":  "Managing Implementation",
    # Q32 - Preemptible VM shutdown scripts → Managing Infrastructure
    "32":  "Managing Infrastructure",
    # Q33 - Network tags + firewall rules → Security and Compliance
    "33":  "Security and Compliance",
    # Q34 - Kernel module debugging on GCE → Operations Reliability
    "34":  "Operations Reliability",
    # Q35 - BigQuery + GCS for archival → Designing and Planning
    "35":  "Designing and Planning",
    # Q36 - Rollback via pipeline → Managing Implementation
    "36":  "Managing Implementation",
    # Q37 - Org hierarchy / folders for IAM → Security and Compliance
    "37":  "Security and Compliance",
    # Q38 - App Engine deployment error → Managing Implementation
    "38":  "Managing Implementation",
    # Q39 - PKI message signing → Security and Compliance
    "39":  "Security and Compliance",
    # Q40 - Dedicated Interconnect for DB replication → Managing Infrastructure
    "40":  "Managing Infrastructure",
    # Q41 - DLP API for data sanitization → Security and Compliance
    "41":  "Security and Compliance",
}

# Fallback domain assignment by keywords in question text
KEYWORD_DOMAINS = [
    (["iam", "permission", "role", "audit", "compliance", "pci", "gdpr", "security",
      "encrypt", "secret", "saml", "identity", "access control", "firewall"],
     "Security and Compliance"),
    (["bigquery", "bigtable", "spanner", "datastore", "cloud sql", "database",
      "storage", "dataflow", "dataproc", "spark", "hadoop", "analytics", "data warehouse"],
     "Designing and Planning"),
    (["kubernetes", "gke", "docker", "container", "pod", "helm", "jenkins",
      "ci/cd", "pipeline", "deploy", "rollback", "canary", "blue-green"],
     "Managing Implementation"),
    (["interconnect", "vpn", "vpc", "network", "subnet", "load balancer",
      "ip", "dns", "routing", "nat"],
     "Managing Infrastructure"),
    (["cost", "budget", "billing", "optimiz", "committed use", "sustained use",
      "right-size", "label"],
     "Optimizing Processes"),
    (["monitor", "logging", "trace", "alert", "reliability", "sla", "slo",
      "disaster recovery", "failover", "backup", "incident"],
     "Operations Reliability"),
]


def classify_domain(q_num, text):
    if q_num in DOMAIN_MAP:
        return DOMAIN_MAP[q_num]
    lower = (text or "").lower()
    for keywords, domain in KEYWORD_DOMAINS:
        if any(kw in lower for kw in keywords):
            return domain
    return "Designing and Planning"  # default


def parse_qa_guide(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()

    questions = []
    for block in content.split("---"):
        block = block.strip()
        if not block:
            continue

        num_m = re.search(r"## Question #(\d+)", block)
        if not num_m:
            continue

        q_num = num_m.group(1)
        lines = block.split("\n")

        q_text_lines, options, answers = [], [], []
        parsing_options = False

        for line in lines:
            line = line.strip()
            if not line or line.startswith("## Question"):
                continue

            ans_m = re.search(r"\*\*Correct Answer:\s*(.*?)\*\*", line)
            if ans_m:
                answers = [a.strip() for a in ans_m.group(1).split(",")]
                continue

            opt_m = re.match(r"^\* ([A-F])\.\s+(.*)", line)
            if opt_m:
                parsing_options = True
                options.append({"label": opt_m.group(1), "text": opt_m.group(2).strip()})
                continue

            if not parsing_options and not line.startswith("#"):
                q_text_lines.append(line)

        q_text = "\n".join(q_text_lines).strip()
        domain  = classify_domain(q_num, q_text)

        questions.append({
            "id":          len(questions) + 1,
            "number":      q_num,
            "topic":       "Google Cloud Professional Cloud Architect",
            "domain":      domain,
            "context":     "",
            "text":        q_text,
            "options":     options,
            "answers":     answers,
            "explanation": "Verified correct answer from the QA guide.",
        })

    return questions


def main():
    print(f"Parsing {QA_FILE} …")
    questions = parse_qa_guide(QA_FILE)

    domains = {}
    for q in questions:
        domains[q["domain"]] = domains.get(q["domain"], 0) + 1

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=4, ensure_ascii=False)

    print(f"Done! Saved {len(questions)} questions → {OUTPUT}")
    print("Domain breakdown:")
    for d, count in sorted(domains.items()):
        print(f"  {d}: {count}")


if __name__ == "__main__":
    main()
