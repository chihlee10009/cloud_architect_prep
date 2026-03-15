from flask import Flask, render_template, request, session, redirect, url_for
import json
import random
import os
import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

STATS_FILE = 'stats.json'

# Load questions
def load_questions():
    try:
        with open('questions.json', 'r') as f:
            return json.load(f)
    except Exception:
        return []

def _default_stats():
    return {
        "sessions": [],
        "domain_totals": {},
        "seen_questions": [],
        "incorrect_history": [],
        "correct_counts": {},
        "question_record": {},
        "queued_questions": [],
    }

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE) as f:
                data = json.load(f)
            # Ensure new keys exist for backward compat
            for key, default in _default_stats().items():
                data.setdefault(key, default)
            return data
        except Exception:
            pass
    return _default_stats()

def save_stats(stats):
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

QUESTIONS = load_questions()

# Helper to find a specific question
def get_question_by_id(q_id):
    return next((q for q in QUESTIONS if q['id'] == q_id), None)

@app.route('/')
def index():
    stats = load_stats()
    wrong_count = len(stats.get('incorrect_history', []))
    queued = stats.get('queued_questions', [])
    seen_set = set(stats.get('seen_questions', []))
    unseen_count = len(QUESTIONS) - len(seen_set)
    return render_template('index.html', total_questions=len(QUESTIONS), wrong_count=wrong_count, queued_count=len(queued), unseen_count=unseen_count)

@app.route('/queue_for_quiz', methods=['POST'])
def queue_for_quiz():
    """Task 8: Queue selected wrong questions so they appear in the next regular quiz."""
    selected_ids = request.form.getlist('review_questions')
    if not selected_ids:
        return redirect(url_for('stats'))
    question_ids = [int(qid) for qid in selected_ids]
    valid_ids = [qid for qid in question_ids if get_question_by_id(qid) is not None]
    if valid_ids:
        stats = load_stats()
        # Merge with existing queue (no duplicates)
        existing = set(stats.get('queued_questions', []))
        existing.update(valid_ids)
        stats['queued_questions'] = list(existing)
        save_stats(stats)
    return redirect(url_for('index'))

@app.route('/clear_queue', methods=['POST'])
def clear_queue():
    """Clear the queued questions."""
    stats = load_stats()
    stats['queued_questions'] = []
    save_stats(stats)
    return redirect(url_for('index'))

@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    num_questions = int(request.form.get('num_questions', 10))
    # Task 7: Exclude questions answered correctly 3+ times
    stats = load_stats()
    correct_counts = stats.get('correct_counts', {})
    question_record = stats.get('question_record', {})
    retired_ids = {int(qid) for qid, cnt in correct_counts.items() if cnt >= 3}
    eligible = [q for q in QUESTIONS if q['id'] not in retired_ids]
    if not eligible:
        eligible = list(QUESTIONS)  # fallback if all retired

    # Task 8: Include queued questions first (guaranteed in quiz)
    queued_ids = stats.get('queued_questions', [])
    forced = []
    forced_id_set = set()
    for qid in queued_ids:
        q = get_question_by_id(qid)
        if q and qid not in retired_ids:
            forced.append(q)
            forced_id_set.add(qid)

    # Task 9: Weight previously-incorrect questions more heavily
    incorrect_ids = {item['question_id'] for item in stats.get('incorrect_history', [])}

    # Remove forced questions from the eligible pool
    remaining_eligible = [q for q in eligible if q['id'] not in forced_id_set]
    remaining_weights = []
    for q in remaining_eligible:
        qid_str = str(q['id'])
        rec = question_record.get(qid_str, {})
        if q['id'] in incorrect_ids:
            remaining_weights.append(3.0)
        elif rec.get('incorrect', 0) > 0:
            remaining_weights.append(2.0)
        else:
            remaining_weights.append(1.0)

    # Fill remaining spots with weighted random
    remaining_pick = max(0, num_questions - len(forced))
    remaining_pick = min(remaining_pick, len(remaining_eligible))

    extra_selected = []
    pool = list(remaining_eligible)
    pool_weights = list(remaining_weights)
    for _ in range(remaining_pick):
        if not pool:
            break
        chosen = random.choices(pool, weights=pool_weights, k=1)[0]
        idx = pool.index(chosen)
        extra_selected.append(chosen)
        pool.pop(idx)
        pool_weights.pop(idx)

    selected = forced + extra_selected
    random.shuffle(selected)
    session['quiz_questions'] = [q['id'] for q in selected]
    session['current_step'] = 0
    session['user_answers'] = {}
    session['user_comments'] = {}
    session['results_saved'] = False

    # Clear the queue after starting the quiz
    stats['queued_questions'] = []
    save_stats(stats)

    return redirect(url_for('quiz'))

@app.route('/start_wrong_quiz', methods=['POST'])
def start_wrong_quiz():
    """Task 0: Start a quiz using all questions from incorrect_history."""
    num_questions = int(request.form.get('num_questions', 10))
    stats = load_stats()
    incorrect_history = stats.get('incorrect_history', [])
    if not incorrect_history:
        return redirect(url_for('index'))
    wrong_ids = [item['question_id'] for item in incorrect_history]
    # Validate IDs
    valid_ids = [qid for qid in wrong_ids if get_question_by_id(qid) is not None]
    if not valid_ids:
        return redirect(url_for('index'))
    pick_count = min(num_questions, len(valid_ids))
    selected = random.sample(valid_ids, pick_count)
    random.shuffle(selected)
    session['quiz_questions'] = selected
    session['current_step'] = 0
    session['user_answers'] = {}
    session['user_comments'] = {}
    session['results_saved'] = False
    return redirect(url_for('quiz'))

@app.route('/start_unseen_quiz', methods=['POST'])
def start_unseen_quiz():
    """Task 11: Start a quiz using only unseen questions."""
    num_questions = int(request.form.get('num_questions', 10))
    stats = load_stats()
    seen_set = set(stats.get('seen_questions', []))
    unseen = [q for q in QUESTIONS if q['id'] not in seen_set]
    if not unseen:
        return redirect(url_for('index'))
    pick_count = min(num_questions, len(unseen))
    selected = random.sample(unseen, pick_count)
    random.shuffle(selected)
    session['quiz_questions'] = [q['id'] for q in selected]
    session['current_step'] = 0
    session['user_answers'] = {}
    session['user_comments'] = {}
    session['results_saved'] = False
    return redirect(url_for('quiz'))

@app.route('/start_review_quiz', methods=['POST'])
def start_review_quiz():
    """Task 8: Start a quiz with user-selected wrong questions."""
    selected_ids = request.form.getlist('review_questions')
    if not selected_ids:
        return redirect(url_for('stats'))
    question_ids = [int(qid) for qid in selected_ids]
    # Validate that all IDs are real questions
    valid_ids = [qid for qid in question_ids if get_question_by_id(qid) is not None]
    if not valid_ids:
        return redirect(url_for('stats'))
    random.shuffle(valid_ids)
    session['quiz_questions'] = valid_ids
    session['current_step'] = 0
    session['user_answers'] = {}
    session['user_comments'] = {}
    session['results_saved'] = False
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
    
    saved_answers = session.get('user_answers', {}).get(str(question_id), [])
    saved_comment = session.get('user_comments', {}).get(str(question_id), '')
    
    return render_template('quiz.html', 
                           question=question, 
                           current=current_step + 1, 
                           total=len(quiz_questions),
                           progress=progress,
                           can_go_back=(current_step > 0),
                           saved_answers=saved_answers,
                           saved_comment=saved_comment)

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    question_id = int(request.form.get('question_id'))
    answer = request.form.getlist('answer') # Supports multi-select
    comment = request.form.get('comment', '').strip()
    action = request.form.get('action', 'next')
    
    user_answers = session.get('user_answers', {})
    user_answers[str(question_id)] = answer
    session['user_answers'] = user_answers

    user_comments = session.get('user_comments', {})
    user_comments[str(question_id)] = comment
    session['user_comments'] = user_comments
    
    if action == 'back':
        session['current_step'] = max(0, session.get('current_step', 0) - 1)
    else:
        session['current_step'] = session.get('current_step', 0) + 1
    return redirect(url_for('quiz'))

@app.route('/results')
def results():
    if 'quiz_questions' not in session:
        return redirect(url_for('index'))
    
    quiz_questions = session.get('quiz_questions', [])
    user_answers = session.get('user_answers', {})
    user_comments = session.get('user_comments', {})
    
    results_list = []
    score = 0
    domain_results = {}
    
    for q_id in quiz_questions:
        q = get_question_by_id(q_id)
        u_ans = user_answers.get(str(q_id), [])
        comment = user_comments.get(str(q_id), '')
        
        is_correct = sorted(u_ans) == sorted(q['answers'])
        if is_correct:
            score += 1

        domain = q.get('domain', 'Designing and Planning')
        dr = domain_results.setdefault(domain, {'correct': 0, 'incorrect': 0})
        if is_correct:
            dr['correct'] += 1
        else:
            dr['incorrect'] += 1

        # Build full label+text representations for the template
        opt_map = {o['label']: o['text'] for o in q['options']}
        correct_full = [
            {'label': lbl, 'text': opt_map.get(lbl, '')}
            for lbl in q['answers']
        ]
        user_full = [
            {'label': lbl, 'text': opt_map.get(lbl, '')}
            for lbl in u_ans
        ]
            
        results_list.append({
            'question': q,
            'user_answer': u_ans,
            'user_full': user_full,
            'correct_full': correct_full,
            'comment': comment,
            'domain': domain,
            'is_correct': is_correct,
            'prompt': generate_prompt(q) if not is_correct else None
        })
    
    final_score = (score / len(quiz_questions)) * 100 if quiz_questions else 0
    percent = int(final_score)

    # Persist this session to stats.json (only once per quiz)
    if not session.get('results_saved'):
        stats = load_stats()
        for domain, dr in domain_results.items():
            dt = stats['domain_totals'].setdefault(domain, {'correct': 0, 'incorrect': 0})
            dt['correct'] += dr['correct']
            dt['incorrect'] += dr['incorrect']

        # 3a: Track seen questions
        seen = set(stats.get('seen_questions', []))
        for q_id in quiz_questions:
            seen.add(q_id)
        stats['seen_questions'] = list(seen)

        # Track per-question right/wrong record (Task 4 updated)
        correct_counts = stats.get('correct_counts', {})
        question_record = stats.get('question_record', {})
        incorrect_set = {item['question_id'] for item in stats.get('incorrect_history', [])}
        for r in results_list:
            qid_str = str(r['question']['id'])
            qid_int = r['question']['id']
            # Initialize record if needed
            if qid_str not in question_record:
                question_record[qid_str] = {'correct': 0, 'incorrect': 0}
            if r['is_correct']:
                correct_counts[qid_str] = correct_counts.get(qid_str, 0) + 1
                question_record[qid_str]['correct'] += 1
                # Task 4 + 7: Only remove from incorrect history after 3 consecutive correct answers
                if correct_counts.get(qid_str, 0) >= 3:
                    stats['incorrect_history'] = [
                        item for item in stats['incorrect_history']
                        if item['question_id'] != qid_int
                    ]
                    incorrect_set.discard(qid_int)
            else:
                question_record[qid_str]['incorrect'] += 1
                # Reset consecutive correct count on wrong answer
                correct_counts[qid_str] = 0
                # Add to incorrect history if not already there
                if qid_int not in incorrect_set:
                    stats['incorrect_history'].append({
                        'question_id': qid_int,
                        'number': r['question'].get('number', qid_int),
                        'text': r['question']['text'],
                        'domain': r['domain'],
                    })
                    incorrect_set.add(qid_int)
        stats['correct_counts'] = correct_counts
        stats['question_record'] = question_record

        stats['sessions'].append({
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            'score': score,
            'total': len(quiz_questions),
            'percent': percent,
            'domain_results': domain_results,
        })
        save_stats(stats)
        session['results_saved'] = True
    
    return render_template('results.html', 
                           results=results_list, 
                           score=score, 
                           total=len(quiz_questions),
                           percent=percent,
                           domain_results=domain_results)

@app.route('/stats')
def stats():
    stats_data = load_stats()
    # Compute retired count and mastered questions list for display (Task 10)
    correct_counts = stats_data.get('correct_counts', {})
    mastered_questions = []
    for qid_str, cnt in correct_counts.items():
        if cnt >= 3:
            q = get_question_by_id(int(qid_str))
            if q:
                mastered_questions.append({
                    'number': q.get('number', int(qid_str)),
                    'text': q['text'],
                    'domain': q.get('domain', 'Unknown'),
                })
    mastered_questions.sort(key=lambda x: x['number'])
    retired_count = len(mastered_questions)
    return render_template('stats.html',
                           stats=stats_data,
                           total_questions=len(QUESTIONS),
                           retired_count=retired_count,
                           mastered_questions=mastered_questions)

@app.route('/reset_stats', methods=['POST'])
def reset_stats():
    save_stats(_default_stats())
    return redirect(url_for('stats'))

def generate_prompt(question):
    """
    Generate a prompt for NotebookLM Podcast based on the missed question.
    Creates a study-focused prompt that works well as a NotebookLM source.
    """
    domain = question.get('domain', 'Cloud Architecture')
    text = question.get('text', '')
    explanation = question.get('explanation', '')
    correct_options = [opt['text'] for opt in question['options'] if opt['label'] in question['answers']]
    all_options = [f"{opt['label']}. {opt['text']}" for opt in question['options']]
    correct_labels = ', '.join(question.get('answers', []))

    prompt = (
        f"STUDY GUIDE — Google Cloud Professional Cloud Architect Exam\n"
        f"Domain: {domain}\n\n"
        f"I missed the following exam question and need to deeply understand the concepts behind it.\n\n"
        f"QUESTION:\n{text}\n\n"
        f"OPTIONS:\n" + "\n".join(all_options) + "\n\n"
        f"CORRECT ANSWER: {correct_labels}\n"
        f"Correct option(s): {'; '.join(correct_options)}\n\n"
    )
    if explanation:
        prompt += f"EXPLANATION PROVIDED:\n{explanation}\n\n"
    prompt += (
        "INSTRUCTIONS FOR NOTEBOOKLM PODCAST:\n"
        "Please create an engaging, conversational deep-dive on this topic. Cover:\n"
        "1. The core Google Cloud architectural concepts tested by this question\n"
        "2. Why the correct answer is the best choice and the trade-offs of each option\n"
        "3. Real-world scenarios where these services or patterns apply\n"
        "4. Common mistakes or misconceptions architects should avoid\n"
        "5. Related Google Cloud services and how they fit together\n"
    )
    return prompt

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
