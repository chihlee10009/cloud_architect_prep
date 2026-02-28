import re
import json
import os

def parse_qa_guide(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by the horizontal rule separator used in the QA guide
    blocks = content.split("---")
    questions = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Extract Question Number
        num_match = re.search(r"## Question #(\d+)", block)
        if not num_match:
            continue
        
        q_num = num_match.group(1)
        
        # Extract Question Text and Options
        # Logic: Everything between the header and the first option is question text.
        # Options start with "* A.", "* B.", etc.
        lines = block.split('\n')
        q_text_lines = []
        options = []
        answers = []
        
        is_parsing_options = False
        
        for line in lines:
            line = line.strip()
            if not line or "## Question #" in line:
                continue
            
            # Check for Correct Answer marker
            ans_match = re.search(r"\*\*Correct Answer:\s*(.*)\*\*", line)
            if ans_match:
                ans_str = ans_match.group(1)
                answers = [a.strip() for a in ans_str.split(",")]
                continue

            # Check for options
            option_match = re.match(r"^\* ([A-F])\.\s+(.*)", line)
            if option_match:
                is_parsing_options = True
                options.append({
                    "label": option_match.group(1),
                    "text": option_match.group(2).strip()
                })
                continue
            
            if not is_parsing_options:
                # Still in question body
                if not line.startswith("#"):
                    q_text_lines.append(line)

        # Assemble question object
        questions.append({
            "id": len(questions) + 1,
            "number": q_num,
            "topic": "Google Cloud Professional Cloud Architect (QA Guide)",
            "context": "", # QA guide usually embeds context in the question text
            "text": "\n".join(q_text_lines).strip(),
            "options": options,
            "answers": answers,
            "explanation": "Verified correct answer from the official QA guide."
        })

    return questions

def main():
    QA_FILE = "ref_cloud_architect_qa.md"
    OUTPUT_FILE = "questions.json"
    
    if not os.path.exists(QA_FILE):
        print(f"Error: {QA_FILE} not found.")
        return

    print(f"Parsing {QA_FILE}...")
    question_data = parse_qa_guide(QA_FILE)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(question_data, f, indent=4)
        
    print(f"Successfully generated {len(question_data)} questions from the QA guide.")

if __name__ == "__main__":
    main()
