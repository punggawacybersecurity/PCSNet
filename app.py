# Name:    PCSNet Web Tools App
# Author:  Kang Ali
# Version: v1.0  
# Date:    2025-05-23

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
import markdown
import datetime
import subprocess
import sys 

app = Flask(__name__)

# --- Konfigurasi Aplikasi ---
# SECRET_KEY HARUS diambil dari environment variable untuk keamanan.
# Jika tidak ditemukan, aplikasi akan keluar dengan error.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    sys.exit("Error: SECRET_KEY environment variable not set. Please set it for security.")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# --- Konfigurasi Gemini API (API Key) ---
API_KEY = "GOOGLE_API_KEY" # <--- GANTI DENGAN API KEY ASLI ANDA DI SINI!
genai.configure(api_key=API_KEY)

# --- Konfigurasi Tools Scanning ---
SUBLIST3R_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "Sublist3r", "sublist3r.py") 

# --- Model Database ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    chats = db.relationship('ChatSession', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}')"

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False, default="New Chat")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now(datetime.timezone.utc))
    messages = db.relationship('ChatMessage', backref='session', lazy=True, order_by='ChatMessage.timestamp', cascade="all, delete-orphan")

    def __repr__(self):
        return f"ChatSession('{self.title}', '{self.user.username}')"

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False) # 'user' or 'bot'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now(datetime.timezone.utc))

    def __repr__(self):
        return f"ChatMessage('{self.role}', '{self.session.title}')"

# --- Flask-Login User Loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Fungsi Utility ---
def clean_and_convert_markdown(text):
    if not text:
        return ""
    
    cleaned_text = text.strip()
    cleaned_text = cleaned_text.replace('\\n', '\n')
    cleaned_text = cleaned_text.replace('\\"', '"')

    html_content = markdown.markdown(
        cleaned_text, 
        extensions=['fenced_code', 'tables', 'nl2br', 'sane_lists'] 
    )
    return html_content

# --- Routes Aplikasi ---

@app.route("/", methods=['GET', 'POST'])
@login_required 
def index():
    if request.method == 'POST':
        tool = request.form.get('tool')
        target = request.form.get('target')
        result = ""
        command = []

        if not target:
            return jsonify({'result': 'Error: Target tidak boleh kosong.'}), 400

        try:
            if tool == 'whois':
                command = ['whois', target]
            elif tool == 'dnslookup':
                command = ['dig', target]
            elif tool == 'whatweb':
                command = ['whatweb', target]
            elif tool == 'ip_locator':
                command = ['curl', f'ipinfo.io/{target}']
            elif tool == 'nmap_basic':
                command = ['nmap', target]
            elif tool == 'nmap_extensive':
                command = ['sudo', 'nmap', '-sS', '-sV', '--top-ports', '1000', '-T4', '-O', target]
            elif tool == 'subdomain':
                command = ['python3', SUBLIST3R_PATH, '-d', target]
            elif tool == 'waf_check':
                command = ['wafw00f', target]
            elif tool == 'sqlmap':
                command = ['sqlmap', '-u', target, '--dbs']
            elif tool == 'xss':
                command = ['XSpear', '-u', target, '-v', '1']
            elif tool == 'http_header':
                command = ['curl', '-I', target]
            elif tool == 'traceroute':
                command = ['traceroute', target]
            elif tool == 'ddos_test':
                command = ['slowhttptest', '-c', '10000', '-H', '-g', '-o', 'apache_no_mitigation', '-i', '10', '-r', '200', '-t', 'GET', '-u', target]
            elif tool == 'ddos_vuln_check':
                command = ['nmap', '--script', 'http-slowloris-check', target]
            else:
                return jsonify({'result': 'Invalid tool selected.'}), 400

            process = subprocess.run(command, capture_output=True, text=True, check=True, env=os.environ)
            result = process.stdout
            if process.stderr:
                result += f"\n[stderr]\n{process.stderr}"

        except subprocess.CalledProcessError as e:
            result = f"Error executing {tool}: {e.stderr if e.stderr else e.output}. Exit Code: {e.returncode}"
            app.logger.error(f"Error running command: {' '.join(command)} - {e.stderr}")
        except FileNotFoundError:
            result = f"Error: Command '{command[0]}' not found. Pastikan tool terinstal dan bisa diakses di PATH."
            app.logger.error(f"Tool not found: {command[0]}")
        except Exception as e:
            result = f"Terjadi kesalahan tak terduga: {str(e)}"
            app.logger.error(f"Unexpected error: {str(e)}")

        return jsonify({'result': result})
    
    return render_template("index.html")

# Rute Chat AI
@app.route("/chat_ai", methods=["GET", "POST"])
@login_required
def chat_ai():
    llm_response_html = ""
    user_query_display = ""
    current_chat_id = request.args.get('chat_id', type=int)
    current_chat_session = None
    chat_messages_history = []
    
    if current_chat_id:
        current_chat_session = ChatSession.query.filter_by(id=current_chat_id, user_id=current_user.id).first()
    
    if not current_chat_session:
        current_chat_session = ChatSession(user_id=current_user.id, title="Chat PCSNet")
        db.session.add(current_chat_session)
        db.session.commit()
        current_chat_id = current_chat_session.id
        flash(f"Memulai sesi chat baru.", 'success')
        return redirect(url_for('chat_ai', chat_id=current_chat_id)) 

    chat_messages_history = ChatMessage.query.filter_by(session_id=current_chat_session.id).order_by(ChatMessage.timestamp.asc()).all()

    if request.method == "POST":
        user_query = request.form.get("query")
        user_query_display = user_query 

        if user_query:
            try:
                user_msg = ChatMessage(session_id=current_chat_session.id, role='user', content=user_query)
                db.session.add(user_msg)
                db.session.commit() 
                
                chat_messages_history = ChatMessage.query.filter_by(session_id=current_chat_session.id).order_by(ChatMessage.timestamp.asc()).all()

                messages_for_gemini = []
                for msg in chat_messages_history:
                    messages_for_gemini.append({'role': 'user' if msg.role == 'user' else 'model', 'parts': [{'text': msg.content}]})
                
                model = genai.GenerativeModel("gemini-2.0-flash") 
                response = model.generate_content(messages_for_gemini)
                raw_llm_response = response.text 
                
                bot_msg = ChatMessage(session_id=current_chat_session.id, role='bot', content=raw_llm_response)
                db.session.add(bot_msg)
                db.session.commit()

                return redirect(url_for('chat_ai', chat_id=current_chat_id))

            except Exception as e:
                flash(f"Terjadi kesalahan saat menghubungi Gemini API: {e}. Pastikan API Key benar dan kuota tersedia.", 'danger')
    
    rendered_messages = []
    for msg in chat_messages_history:
        rendered_messages.append({
            'role': msg.role,
            'content_html': clean_and_convert_markdown(msg.content)
        })

    header_chat_title = "Chat PCSNet" 

    return render_template("chat_ai.html", 
                           user_query=user_query_display, 
                           llm_response_html=llm_response_html, 
                           current_chat_id=current_chat_id,
                           current_chat_title=header_chat_title,
                           rendered_messages=rendered_messages)

# --- Routes Autentikasi ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username sudah ada. Pilih nama lain.', 'danger')
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Akun berhasil dibuat! Silakan login.', 'success')
            return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        remember = True if request.form.get("remember") else False
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash('Login berhasil!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Login gagal. Periksa username dan password.', 'danger')
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('login'))

# --- Routes Halaman Statis ---
@app.route("/tentang")
def tentang():
    return render_template("tentang.html")

@app.route("/kontak")
def kontak():
    return render_template("kontak.html")

@app.route("/website")
def website():
    return render_template("website_link.html")

# --- Routes Riwayat Chat ---
@app.route("/chat_history")
@login_required
def chat_history():
    user_chat_sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.created_at.desc()).all()
    return render_template("chat_history.html", sessions=user_chat_sessions)

# --- Edit Chat Title Route ---
@app.route("/edit_chat_title/<int:chat_id>", methods=["POST"])
@login_required
def edit_chat_title(chat_id):
    chat_session = ChatSession.query.filter_by(id=chat_id, user_id=current_user.id).first()
    if chat_session:
        new_title = request.form.get("new_title")
        if new_title and new_title.strip():
            chat_session.title = new_title.strip()
            db.session.commit()
            flash(f"Judul chat berhasil diubah menjadi '{chat_session.title}'", 'success')
        else:
            flash("Judul chat tidak boleh kosong.", 'danger')
    else:
        flash("Sesi chat tidak ditemukan atau bukan milik Anda.", 'danger')
    return redirect(url_for('chat_history'))

# --- Delete Chat Route ---
@app.route("/delete_chat/<int:chat_id>", methods=["POST"])
@login_required
def delete_chat(chat_id):
    chat_session = ChatSession.query.filter_by(id=chat_id, user_id=current_user.id).first()
    if chat_session:
        db.session.delete(chat_session)
        db.session.commit()
        flash(f"Sesi chat '{chat_session.title}' berhasil dihapus.", 'success')
    else:
        flash("Sesi chat tidak ditemukan atau bukan milik Anda.", 'danger')
    return redirect(url_for('chat_history'))

# --- Delete All Chats Route ---
@app.route("/delete_all_chats", methods=["POST"])
@login_required
def delete_all_chats():
    try:
        user_chat_sessions = ChatSession.query.filter_by(user_id=current_user.id).all()
        for session in user_chat_sessions:
            db.session.delete(session)
        db.session.commit()
        flash('Semua riwayat chat Anda berhasil dihapus.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan saat menghapus riwayat chat: {e}', 'danger')
    
    return redirect(url_for('chat_history'))

# --- Endpoint API (tidak berubah) ---
@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    data = request.json
    user_query = data.get("query")
    current_chat_id = data.get("chat_id")

    if not user_query or not current_chat_id:
        return jsonify({"error": "Query dan chat_id tidak boleh kosong"}), 400

    current_chat_session = ChatSession.query.filter_by(id=current_chat_id, user_id=current_user.id).first()
    if not current_chat_session:
        return jsonify({"error": "Sesi chat tidak ditemukan atau bukan milik Anda"}), 404

    try:
        user_msg = ChatMessage(session_id=current_chat_session.id, role='user', content=user_query)
        db.session.add(user_msg)
        db.session.commit()

        messages_for_gemini = []
        for msg in ChatMessage.query.filter_by(session_id=current_chat_session.id).order_by(ChatMessage.timestamp.asc()).all():
            messages_for_gemini.append({'role': 'user' if msg.role == 'user' else 'model', 'parts': [{'text': msg.content}]})

        model = genai.GenerativeModel("gemini-2.0-flash") 
        response = model.generate_content(messages_for_gemini)
        raw_llm_response = response.text 
        
        bot_msg = ChatMessage(session_id=current_chat_session.id, role='bot', content=raw_llm_response)
        db.session.add(bot_msg)
        db.session.commit()

        return jsonify({
            "user_query_html": clean_and_convert_markdown(user_query),
            "response_html": clean_and_convert_markdown(raw_llm_response),
            "user_timestamp": user_msg.timestamp.strftime('%H:%M'),
            "bot_timestamp": bot_msg.timestamp.strftime('%H:%M')
        })
    except Exception as e:
        return jsonify({"error": f"Terjadi kesalahan saat menghubungi Gemini API: {e}"}), 500
    return jsonify({"error": "Query tidak boleh kosong"}), 400


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Database 'site.db' created or already exists.")
    app.run(host='0.0.0.0', port=1337, debug=True)