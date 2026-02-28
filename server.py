import http.server
import socketserver
import json
import random
import os
import urllib.parse
import datetime
from jinja2 import Environment, FileSystemLoader

PORT           = 5002
QUESTIONS_FILE = 'questions.json'
STATS_FILE     = 'stats.json'
TEMPLATES_DIR  = 'templates'

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
SESSIONS = {}


# ── Data loading ──────────────────────────────────────────────────────────────
def load_questions():
    try:
        with open(QUESTIONS_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading questions: {e}")
        return []


def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "sessions": [],      # list of {date, score, total, percent, domain_results}
        "domain_totals": {}  # {domain: {correct: N, incorrect: N}}
    }


def save_stats(stats):
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)


QUESTIONS = load_questions()


# ── HTTP Handler ───────────────────────────────────────────────────────────────
class QuizHandler(http.server.BaseHTTPRequestHandler):

    def get_session_id(self):
        cookies = self.headers.get('Cookie', '')
        for cookie in cookies.split(';'):
            if 'session_id=' in cookie:
                return cookie.split('=', 1)[1].strip()
        return None

    def create_session(self):
        sid = os.urandom(16).hex()
        SESSIONS[sid] = {
            'quiz_questions': [],
            'current_step':  0,
            'user_answers':  {},   # {str(q_id): [labels]}
            'user_comments': {},   # {str(q_id): "text"}
        }
        return sid

    def session(self):
        sid = self.get_session_id()
        if sid and sid in SESSIONS:
            return sid, SESSIONS[sid]
        return None, None

    # ── GET ───────────────────────────────────────────────────────────────────
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        sid  = self.get_session_id()

        # Home – always accessible, creates session lazily
        if path == '/':
            if not sid or sid not in SESSIONS:
                sid = self.create_session()
            tmpl    = env.get_template('index.html')
            content = tmpl.render(total_questions=len(QUESTIONS))
            self.send_page(content, sid)
            return

        # Stats dashboard – accessible without an active quiz session
        if path == '/stats':
            stats   = load_stats()
            tmpl    = env.get_template('stats.html')
            content = tmpl.render(stats=stats)
            self.send_page(content)
            return

        sid, sess = self.session()
        if not sess:
            self.redirect('/')
            return

        if path == '/quiz':
            quiz_qs = sess['quiz_questions']
            if not quiz_qs:
                self.redirect('/')
                return

            step = sess['current_step']
            if step >= len(quiz_qs):
                self.redirect('/results')
                return

            q_id     = quiz_qs[step]
            question = next((q for q in QUESTIONS if q['id'] == q_id), None)
            progress = int(step / len(quiz_qs) * 100)

            tmpl    = env.get_template('quiz.html')
            content = tmpl.render(
                question=question,
                current=step + 1,
                total=len(quiz_qs),
                progress=progress,
                can_go_back=(step > 0),
                saved_answers=sess['user_answers'].get(str(q_id), []),
                saved_comment=sess['user_comments'].get(str(q_id), ''),
            )
            self.send_page(content)

        elif path == '/results':
            quiz_qs      = sess['quiz_questions']
            user_answers = sess['user_answers']
            user_comments= sess['user_comments']

            results_list = []
            score        = 0
            domain_results = {}   # {domain: {correct, incorrect}}

            for q_id in quiz_qs:
                q      = next((qu for qu in QUESTIONS if qu['id'] == q_id), None)
                u_ans  = user_answers.get(str(q_id), [])
                comment= user_comments.get(str(q_id), '')

                is_correct = sorted(u_ans) == sorted(q['answers'])
                if is_correct:
                    score += 1

                domain = q.get('domain', 'Designing and Planning')
                dr = domain_results.setdefault(domain, {'correct': 0, 'incorrect': 0})
                if is_correct:
                    dr['correct'] += 1
                else:
                    dr['incorrect'] += 1

                # Build full label+text representations
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
                    'question':      q,
                    'user_answer':   u_ans,
                    'user_full':     user_full,
                    'correct_full':  correct_full,
                    'comment':       comment,
                    'is_correct':    is_correct,
                    'domain':        domain,
                    'prompt':        self._generate_prompt(q) if not is_correct else None,
                })

            percent = int(score / len(quiz_qs) * 100) if quiz_qs else 0

            # Persist this session to stats.json
            stats = load_stats()
            for domain, dr in domain_results.items():
                dt = stats['domain_totals'].setdefault(domain, {'correct': 0, 'incorrect': 0})
                dt['correct']   += dr['correct']
                dt['incorrect'] += dr['incorrect']

            stats['sessions'].append({
                'date':           datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
                'score':          score,
                'total':          len(quiz_qs),
                'percent':        percent,
                'domain_results': domain_results,
            })
            save_stats(stats)

            tmpl    = env.get_template('results.html')
            content = tmpl.render(
                results=results_list,
                score=score,
                total=len(quiz_qs),
                percent=percent,
                domain_results=domain_results,
            )
            self.send_page(content)

        else:
            self.send_error(404, 'Not Found')

    # ── POST ──────────────────────────────────────────────────────────────────
    def do_POST(self):
        sid, sess = self.session()
        if not sess:
            self.redirect('/')
            return

        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length).decode('utf-8')
        params = urllib.parse.parse_qs(body)
        path   = urllib.parse.urlparse(self.path).path

        if path == '/start_quiz':
            num     = int(params.get('num_questions', [10])[0])
            indices = random.sample(range(len(QUESTIONS)), min(num, len(QUESTIONS)))
            sess['quiz_questions'] = [QUESTIONS[i]['id'] for i in indices]
            sess['current_step']   = 0
            sess['user_answers']   = {}
            sess['user_comments']  = {}
            self.redirect('/quiz')

        elif path == '/submit_answer':
            q_id    = params.get('question_id', [None])[0]
            ans     = params.get('answer', [])
            comment = params.get('comment', [''])[0].strip()
            action  = params.get('action', ['next'])[0]

            if q_id:
                sess['user_answers'][q_id]  = ans
                sess['user_comments'][q_id] = comment

            if action == 'back':
                sess['current_step'] = max(0, sess['current_step'] - 1)
            else:
                sess['current_step'] += 1

            self.redirect('/quiz')

    # ── Helpers ───────────────────────────────────────────────────────────────
    def send_page(self, content, sid=None):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        if sid:
            self.send_header('Set-Cookie', f'session_id={sid}; Path=/')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def redirect(self, location):
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()

    def _generate_prompt(self, question):
        topic   = question.get('topic', 'Cloud Architecture')
        domain  = question.get('domain', '')
        text    = question.get('text', '')
        correct = [o['text'] for o in question['options'] if o['label'] in question['answers']]
        return (
            f"I'm studying for the Google Cloud Professional Cloud Architect exam.\n\n"
            f"Domain: {domain}\n"
            f"Topic: {topic}\n"
            f"Question: {text}\n\n"
            f"Correct answer: {', '.join(correct)}\n\n"
            f"Please explain the key architectural concepts behind this answer and why the "
            f"other options are less appropriate."
        )

    def log_message(self, fmt, *args):
        print(fmt % args)


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == '__main__':
    print(f"Starting server on http://localhost:{PORT}  (Ctrl+C to stop)")
    with ReusableTCPServer(('', PORT), QuizHandler) as httpd:
        httpd.serve_forever()
