import http.server
import socketserver
import json
import random
import os
import urllib.parse
from jinja2 import Environment, FileSystemLoader

# Configuration
PORT = 5001
QUESTIONS_FILE = 'questions.json'
TEMPLATES_DIR = 'templates'

# Load templates
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

# In-memory session store (Mock sessions)
SESSIONS = {}

def load_questions():
    try:
        with open(QUESTIONS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading questions: {e}")
        return []

QUESTIONS = load_questions()

class QuizHandler(http.server.BaseHTTPRequestHandler):
    def get_session_id(self):
        cookies = self.headers.get('Cookie')
        if cookies:
            for cookie in cookies.split(';'):
                if 'session_id=' in cookie:
                    return cookie.split('=')[1].strip()
        return None

    def create_session(self):
        sid = os.urandom(16).hex()
        SESSIONS[sid] = {
            'quiz_questions': [],
            'current_step': 0,
            'user_answers': {}
        }
        return sid

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        sid = self.get_session_id()

        # Always serve the index page and establish session if missing
        if path == '/':
            if not sid or sid not in SESSIONS:
                sid = self.create_session()
                # We'll set the cookie in the send_page call
            
            template = env.get_template('index.html')
            content = template.render(total_questions=len(QUESTIONS))
            self.send_page(content, sid)
            return

        if not sid or sid not in SESSIONS:
            self.redirect('/')
            return
        
        elif path == '/quiz':
            session = SESSIONS[sid]
            if not session['quiz_questions']:
                self.redirect('/')
                return
            
            current_step = session['current_step']
            quiz_questions = session['quiz_questions']
            
            if current_step >= len(quiz_questions):
                self.redirect('/results')
                return
            
            q_id = quiz_questions[current_step]
            question = next((q for q in QUESTIONS if q['id'] == q_id), None)
            progress = int((current_step / len(quiz_questions)) * 100)
            
            template = env.get_template('quiz.html')
            content = template.render(question=question, current=current_step+1, total=len(quiz_questions), progress=progress)
            self.send_page(content)
            
        elif path == '/results':
            session = SESSIONS[sid]
            quiz_questions = session['quiz_questions']
            user_answers = session['user_answers']
            
            results_list = []
            score = 0
            for q_id in quiz_questions:
                q = next((qu for qu in QUESTIONS if qu['id'] == q_id), None)
                u_ans = user_answers.get(str(q_id), [])
                
                # Check answers
                is_correct = sorted(u_ans) == sorted(q['answers'])
                if is_correct: score += 1
                
                results_list.append({
                    'question': q,
                    'user_answer': u_ans,
                    'is_correct': is_correct,
                    'prompt': self.generate_prompt(q) if not is_correct else None
                })
            
            percent = int((score / len(quiz_questions)) * 100) if quiz_questions else 0
            template = env.get_template('results.html')
            content = template.render(results=results_list, score=score, total=len(quiz_questions), percent=percent)
            self.send_page(content)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        sid = self.get_session_id()
        if not sid or sid not in SESSIONS:
            self.redirect('/')
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = urllib.parse.parse_qs(post_data)
        
        path = urllib.parse.urlparse(self.path).path
        
        if path == '/start_quiz':
            num = int(params.get('num_questions', [10])[0])
            indices = random.sample(range(len(QUESTIONS)), min(num, len(QUESTIONS)))
            SESSIONS[sid]['quiz_questions'] = [QUESTIONS[i]['id'] for i in indices]
            SESSIONS[sid]['current_step'] = 0
            SESSIONS[sid]['user_answers'] = {}
            self.redirect('/quiz')
            
        elif path == '/submit_answer':
            q_id = params.get('question_id', [None])[0]
            ans = params.get('answer', []) # List for multi-select
            if q_id:
                SESSIONS[sid]['user_answers'][q_id] = ans
                SESSIONS[sid]['current_step'] += 1
            self.redirect('/quiz')

    def send_page(self, content, sid=None):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        if sid:
            self.send_header('Set-Cookie', f'session_id={sid}')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def redirect(self, location):
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()

    def generate_prompt(self, question):
        topic = question.get('topic', 'unspecified topic')
        text = question.get('text', '')
        correct = [opt['text'] for opt in question['options'] if opt['label'] in question['answers']]
        return f"Study prompt for {topic}:\nQ: {text}\nCorrect: {', '.join(correct)}\nExplain why."

if __name__ == '__main__':
    print(f"Starting server on port {PORT}...")
    with socketserver.TCPServer(("", PORT), QuizHandler) as httpd:
        httpd.serve_forever()
