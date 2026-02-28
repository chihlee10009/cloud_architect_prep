from flask import Flask, render_template, request, session, redirect, url_for
import json
import random
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Load questions
def load_questions():
    try:
        with open('questions.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

QUESTIONS = load_questions()

# Helper to find a specific question
def get_question_by_id(q_id):
    return next((q for q in QUESTIONS if q['id'] == q_id), None)

@app.route('/')
def index():
    return render_template('index.html', total_questions=len(QUESTIONS))

@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    num_questions = int(request.form.get('num_questions', 10))
    # Shuffle and pick a subset
    selected_indices = random.sample(range(len(QUESTIONS)), min(num_questions, len(QUESTIONS)))
    session['quiz_questions'] = [QUESTIONS[i]['id'] for i in selected_indices]
    session['current_step'] = 0
    session['user_answers'] = {}
    return redirect(url_for('quiz'))

@app.route('/quiz')
def quiz():
    if 'quiz_questions' not in session:
        return redirect(url_for('index'))
    
    current_step = session.get('current_step', 0)
    quiz_questions = session.get('quiz_questions', [])
    
    if current_step >= len(quiz_questions):
        return redirect(url_for('results'))
    
    question_id = quiz_questions[current_step]
    question = get_question_by_id(question_id)
    
    progress = int((current_step / len(quiz_questions)) * 100)
    
    return render_template('quiz.html', 
                           question=question, 
                           current=current_step + 1, 
                           total=len(quiz_questions),
                           progress=progress)

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    question_id = int(request.form.get('question_id'))
    answer = request.form.getlist('answer') # Supports multi-select
    
    user_answers = session.get('user_answers', {})
    user_answers[str(question_id)] = answer
    session['user_answers'] = user_answers
    
    session['current_step'] = session.get('current_step', 0) + 1
    return redirect(url_for('quiz'))

@app.route('/results')
def results():
    if 'quiz_questions' not in session:
        return redirect(url_for('index'))
    
    quiz_questions = session.get('quiz_questions', [])
    user_answers = session.get('user_answers', {})
    
    results_list = []
    score = 0
    
    for q_id in quiz_questions:
        q = get_question_by_id(q_id)
        u_ans = user_answers.get(str(q_id), [])
        
        # Simple string comparison for now (needs sorting for multi-select)
        is_correct = sorted(u_ans) == sorted(q['answers'])
        if is_correct:
            score += 1
            
        results_list.append({
            'question': q,
            'user_answer': u_ans,
            'is_correct': is_correct,
            # Generate NotebookLM prompt if incorrect
            'prompt': generate_prompt(q) if not is_correct else None
        })
    
    final_score = (score / len(quiz_questions)) * 100 if quiz_questions else 0
    
    return render_template('results.html', 
                           results=results_list, 
                           score=score, 
                           total=len(quiz_questions),
                           percent=int(final_score))

def generate_prompt(question):
    """
    Generate a prompt for NotebookLM based on the missed question.
    """
    topic = question.get('topic', 'unspecified topic')
    text = question.get('text', '')
    correct_options = [opt['text'] for opt in question['options'] if opt['label'] in question['answers']]
    
    prompt = f"I am studying for the Google Cloud Professional Cloud Architect exam. I specifically missed a question about {topic}.\n\n"
    prompt += f"The question was: '{text}'\n\n"
    prompt += f"The correct answer(s) involved: {', '.join(correct_options)}.\n\n"
    prompt += "Can you explain the underlying architectural concepts here and why these are the recommended Google Cloud solutions? Also, please provide a deep dive into any related services mentioned."
    
    return prompt

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
