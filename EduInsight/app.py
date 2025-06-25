from flask import Flask, render_template, request, redirect, session, flash, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
import csv
import io
import firebase_admin
from firebase_admin import credentials, firestore
from flask import flash, redirect, url_for

#------------------------------------------FLASK-------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY') or 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///studentsys.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#================================================================================================

#------------------------------------------SQL ALCHEMY AND FIRE BASE INITIALIZATION-------------------------------------------------

db = SQLAlchemy(app)

cred = credentials.Certificate("Your Firebase key") # For Firebase API Key, visit official Firebase Website -> Go to Console -> Create API -> It will be in .json form
firebase_admin.initialize_app(cred)
firestore_db = firestore.client()

STUDENT_DB_FOLDER = 'student_dbs'

if not os.path.exists(STUDENT_DB_FOLDER):
    os.makedirs(STUDENT_DB_FOLDER)
#================================================================================================

#------------------------------------------DATABASE MODELS-------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  
    role = db.Column(db.String(20), nullable=False)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    questions = db.relationship('Question', back_populates='quiz', lazy=True, cascade='all, delete-orphan')

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    text = db.Column(db.String(200), nullable=False)
    choice_1 = db.Column(db.String(200), nullable=False)
    choice_2 = db.Column(db.String(200), nullable=False)
    choice_3 = db.Column(db.String(200), nullable=False)
    choice_4 = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(200), nullable=False)
    quiz = db.relationship('Quiz', back_populates='questions')

StudentBase = declarative_base()

class StudentQuizResult(StudentBase):
    __tablename__ = 'quiz_result'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, nullable=False)
    quiz_id = Column(Integer, nullable=False)
    quiz_name = Column(String(100), nullable=False)  
    score = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
#================================================================================================

#------------------------------------------INITIALIZING LOCATION FOR STORING DATA-------------------------------------------------

def get_student_db_path(username):
    safe_username = "".join(c for c in username if c.isalnum() or c in ('_', '-')).rstrip()
    return os.path.join(STUDENT_DB_FOLDER, f'student_{safe_username}.db')

def get_student_db_session(username):
    db_path = get_student_db_path(username)
    engine = create_engine(f'sqlite:///{db_path}', connect_args={'check_same_thread': False})
    StudentBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

with app.app_context():
    db.create_all()
#================================================================================================

#------------------------------------------MAPPING THE FLOW-------------------------------------------------
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'teacher':
            return redirect('/teacher')
        elif session.get('role') == 'student':
            return redirect('/student')
    return redirect('/login')
#================================================================================================

#------------------------------------------LOGIN-------------------------------------------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        user = User.query.filter_by(username=username, role=role).first()
        if user and user.password == password:  
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash("Logged in successfully.", "success")
            if role == 'teacher':
                return redirect("/teacher")
            else:
                return redirect("/student")
        else:
            flash("Invalid username, password, or role.", "danger")
    return render_template('login.html')
#================================================================================================

#------------------------------------------SIGNUP-------------------------------------------------
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect('/signup')

        new_user = User(username=username, role=role, password=password)  # Store password in plain text
        db.session.add(new_user)
        db.session.commit()
        
        # Sync to Firebase
        if firestore_db:
            firestore_db.collection('users').document(str(new_user.id)).set({
                'username': username,
                'password': password,
                'role': role
            })

        flash("Account created! Please log in.", "success")
        return redirect('/login')
    return render_template('signup.html')
#================================================================================================

#------------------------------------------LOGOUT-------------------------------------------------
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect('/login')
#================================================================================================

#------------------------------------------TEACHER DASHBOARD-------------------------------------------------
@app.route('/teacher')
def teacher_dashboard():
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Unauthorized access.", "warning")
        return redirect('/login')
    quizzes = Quiz.query.all()
    return render_template('teacher_dashboard.html', username=session.get('username'), quizzes=quizzes)
#================================================================================================

#------------------------------------------TEACHER - ADDING QUIZ-------------------------------------------------
@app.route('/teacher/quizzes/add', methods=['GET','POST'])
def add_quiz():
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Unauthorized access.", "warning")
        return redirect('/login')
    if request.method == 'POST':
        quiz_name = request.form.get('quiz_name')
        num_questions = int(request.form.get('num_questions',1))
        new_quiz = Quiz(name=quiz_name)
        db.session.add(new_quiz)
        db.session.commit()
        
        if firestore_db:
            questions_data = []
            for i in range(1, num_questions + 1):
                q_text = request.form.get(f'question_{i}')
                c1 = request.form.get(f'choice_{i}_1')
                c2 = request.form.get(f'choice_{i}_2')
                c3 = request.form.get(f'choice_{i}_3')
                c4 = request.form.get(f'choice_{i}_4')
                correct = request.form.get(f'correct_answer_{i}')
                question = Question(
                    quiz_id=new_quiz.id, text=q_text,
                    choice_1=c1, choice_2=c2, choice_3=c3, choice_4=c4,
                    correct_answer=correct)
                db.session.add(question)
                questions_data.append({
                    'text': q_text,
                    'choices': {
                        '1': c1,
                        '2': c2,
                        '3': c3,
                        '4': c4
                    },
                    'correct_answer': correct
                })
            db.session.commit()
            firestore_db.collection('quizzes').document(str(new_quiz.id)).set({
                'name': quiz_name,
                'questions': questions_data
            })

        flash("Quiz created successfully!", "success")
        return redirect('/teacher')
    return render_template('add_quiz.html')
#================================================================================================

#------------------------------------------TEACHER - EDITING QUIZ-------------------------------------------------
@app.route('/teacher/quizzes/edit/<int:quiz_id>', methods=['GET','POST'])
def edit_quiz(quiz_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Unauthorized access.", "warning")
        return redirect('/login')
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        quiz.name = request.form.get('quiz_name', quiz.name)
        Question.query.filter_by(quiz_id=quiz.id).delete()
        db.session.commit()
        num_questions = int(request.form.get('num_questions',1))
        for i in range(1, num_questions+1):
            q_text = request.form.get(f'question_{i}', '').strip()
            c1 = request.form.get(f'choice_{i}_1', '').strip()
            c2 = request.form.get(f'choice_{i}_2', '').strip()
            c3 = request.form.get(f'choice_{i}_3', '').strip()
            c4 = request.form.get(f'choice_{i}_4', '').strip()
            correct = request.form.get(f'correct_answer_{i}', '').strip()
            if q_text and c1 and c2 and correct:
                question = Question(
                    quiz_id=quiz.id, text=q_text,
                    choice_1=c1, choice_2=c2, choice_3=c3, choice_4=c4,
                    correct_answer=correct)
                db.session.add(question)
        db.session.commit()
        
        if firestore_db:
            questions_data = []
            for i in range(1, num_questions + 1):
                q_text = request.form.get(f'question_{i}')
                c1 = request.form.get(f'choice_{i}_1')
                c2 = request.form.get(f'choice_{i}_2')
                c3 = request.form.get(f'choice_{i}_3')
                c4 = request.form.get(f'choice_{i}_4')
                correct = request.form.get(f'correct_answer_{i}')
                questions_data.append({
                    'text': q_text,
                    'choices': {
                        '1': c1,
                        '2': c2,
                        '3': c3,
                        '4': c4
                    },
                    'correct_answer': correct
                })
            firestore_db.collection('quizzes').document(str(quiz_id)).set({
                'name': quiz.name,
                'questions': questions_data
            })

        flash("Quiz updated!", "success")
        return redirect('/teacher')
    questions = quiz.questions
    num_questions = len(questions)
    return render_template('edit_quiz.html', quiz=quiz, questions=questions, num_questions=num_questions)
#================================================================================================

#------------------------------------------TEACHER - DELETING QUIZ-------------------------------------------------
@app.route('/teacher/quizzes/delete/<int:quiz_id>', methods=['POST'])
def delete_quiz(quiz_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Unauthorized access.", "warning")
        return redirect('/login')
    quiz = Quiz.query.get_or_404(quiz_id)
   
    db.session.delete(quiz)
    db.session.commit()
    
    # Sync to Firebase
    if firestore_db:
        firestore_db.collection('quizzes').document(str(quiz_id)).delete()

    flash("Quiz deleted successfully!", "success")
    return redirect('/teacher')
#================================================================================================

#------------------------------------------ATTEMPTING QUIZ-------------------------------------------------
@app.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
def quiz_view(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if request.method == 'POST':
        score = 0
        total = len(quiz.questions)
        for question in quiz.questions:
            selected = request.form.get(f'q{question.id}')
            if selected and selected.lower() == question.correct_answer.lower():
                score += 1
        
        if 'user_id' in session and session.get('role') == 'student':
            username = session['username']
            session_db = get_student_db_session(username)
            new_result = StudentQuizResult(
                student_id=session['user_id'],
                quiz_id=quiz_id,
                quiz_name=quiz.name,
                score=score,
                total_questions=total,
                timestamp=datetime.utcnow()
            )
            session_db.add(new_result)
            session_db.commit()
            session_db.close()

            store_result_in_firebase(
                user_id=session['user_id'],
                quiz_id=quiz_id,
                quiz_name=quiz.name,
                score=score,
                total_questions=total
            )

        flash(f"QUIZ COMPLETED! Your score: {score}/{total}", 'success')
        
        return redirect(url_for('quiz_view', quiz_id=quiz_id))
    
    return render_template('quiz.html', quiz=quiz)
#================================================================================================

#------------------------------------------STORING RESULT TO FIREBASE-------------------------------------------------
def store_result_in_firebase(user_id, quiz_id, quiz_name, score, total_questions):
    """Stores quiz results in Firestore"""
    try:
        firestore_db.collection('results').add({
            'student_id': str(user_id),
            'quiz_id': str(quiz_id),
            'quiz_name': quiz_name,
            'score': score,
            'total_questions': total_questions,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        return True
    except Exception as e:
        print(f"Error storing in Firebase: {e}")
        return False
#================================================================================================

#------------------------------------------STUDENT - DASHBOARD-------------------------------------------------
@app.route('/student')
def student_dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        flash("Unauthorized access.", "warning")
        return redirect('/login')
    quizzes = Quiz.query.all()
    return render_template('student_dashboard.html', username=session.get('username'), quizzes=quizzes)
#================================================================================================

#------------------------------------------STUDENT - APPEARING FOR QUIZ-------------------------------------------------
@app.route('/student/quiz/<int:quiz_id>', methods=['GET', 'POST'])
def student_take_quiz(quiz_id):
    if 'user_id' not in session or session.get('role') != 'student':
        flash("Unauthorized access.", "warning")
        return redirect('/login')
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if request.method == 'POST':
        score = 0
        total = len(quiz.questions)
        for question in quiz.questions:
            selected = request.form.get(f'q{question.id}')
            if selected and selected.lower() == question.correct_answer.lower():
                score += 1
        
        username = session['username']
        session_db = get_student_db_session(username)
        new_result = StudentQuizResult(
            student_id=session['user_id'],
            quiz_id=quiz_id,
            quiz_name=quiz.name,
            score=score,
            total_questions=total,
            timestamp=datetime.utcnow()
        )
        session_db.add(new_result)
        session_db.commit()
        session_db.close()

        flash(f"Quiz completed! Your score: {score}/{total}", "success")
        
        return redirect('/student')  
    return render_template('student_quiz.html', quiz=quiz)
#================================================================================================

#------------------------------------------STUDENT - RESULT MANAGEMENT-------------------------------------------------
@app.route('/student/results')
def student_results():
    if 'user_id' not in session or session.get('role') != 'student':
        flash("Unauthorized access.", "warning")
        return redirect('/login')
    
    username = session['username']
    user_id = session['user_id']
    
    combined_results = []
    
    try:
        session_db = get_student_db_session(username)
        sql_results = session_db.query(StudentQuizResult).order_by(StudentQuizResult.timestamp.desc()).all()
        for result in sql_results:
            combined_results.append({
                'type': 'sql',
                'quiz_id': result.quiz_id,
                'quiz_name': result.quiz_name,
                'score': result.score,
                'total_questions': result.total_questions,
                'timestamp': result.timestamp
            })
        session_db.close()
    except Exception as e:
        flash(f"Error loading local results: {str(e)}", "danger")
    
    try:
        if firestore_db:  
            firestore_results = firestore_db.collection('results') \
                .where('student_id', '==', str(user_id)) \
                .order_by('timestamp', direction=firestore.Query.DESCENDING) \
                .stream()
            
            for result in firestore_results:
                result_data = result.to_dict()
                combined_results.append({
                    'type': 'firestore',
                    'quiz_id': result_data.get('quiz_id'),
                    'quiz_name': result_data.get('quiz_name', 'Unknown Quiz'),
                    'score': result_data.get('score', 0),
                    'total_questions': result_data.get('total_questions', 0),
                    'timestamp': result_data.get('timestamp')
                })
    except Exception as e:
        flash(f"Error loading cloud results: {str(e)}", "danger")
    
    combined_results.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template('student_results.html', results=combined_results)
#================================================================================================

#------------------------------------------TEACHER - RESULT MANAGEMENT-------------------------------------------------
@app.route('/teacher/results')
def teacher_results():
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Unauthorized access.", "warning")
        return redirect('/login')

    results = []
    for student in User.query.filter_by(role='student').all():
        student_results = get_student_db_session(student.username).query(StudentQuizResult).all()
        for result in student_results:
            result.student = student  
            results.append(result)

    return render_template('teacher_results.html', results=results)
#================================================================================================

#------------------------------------------TEACHER - DELETE STUDENT ------------------------------------------------
@app.route('/teacher/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Unauthorized access.", "warning")
        return redirect('/login')

    student = User.query.get_or_404(student_id)
    student_db_path = get_student_db_path(student.username)
    if os.path.exists(student_db_path):
        try:
            os.remove(student_db_path)
        except OSError:
            flash("Failed to delete student's database file.", "warning")

    db.session.delete(student)
    db.session.commit()
    flash(f"Student '{student.username}' and related results have been deleted.", 'success')
    return redirect('/teacher/results')
#================================================================================================

#------------------------------------------DOWNLOADING RESULT ------------------------------------------------
@app.route('/teacher/download_student_results/<int:student_id>')
def download_student_results(student_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Unauthorized access.", "warning")
        return redirect('/login')
    
    student = User.query.filter_by(id=student_id, role='student').first()
    if not student:
        flash("Student not found.", "danger")
        return redirect('/teacher/results')

    all_results = []

    try:
        session_db = get_student_db_session(student.username)
        sql_results = session_db.query(StudentQuizResult).order_by(StudentQuizResult.timestamp.desc()).all()
        for result in sql_results:
            all_results.append({
                'quiz_name': result.quiz_name,
                'score': result.score,
                'total_questions': result.total_questions,
                'timestamp': result.timestamp.strftime("%Y-%m-%d %H:%M"),
                'source': 'Local Database'
            })
        session_db.close()
    except Exception as e:
        flash(f"Error loading local results: {str(e)}", "danger")

    try:
        if firestore_db:
            firestore_results = firestore_db.collection('results') \
                .where('student_id', '==', str(student_id)) \
                .order_by('timestamp', direction=firestore.Query.DESCENDING) \
                .stream()
            for result in firestore_results:
                data = result.to_dict()
                all_results.append({
                    'quiz_name': data.get('quiz_name', 'Unknown Quiz'),
                    'score': data.get('score', 0),
                    'total_questions': data.get('total_questions', 0),
                    'timestamp': data.get('timestamp').strftime("%Y-%m-%d %H:%M") if data.get('timestamp') else 'N/A',
                    'source': 'Firebase'
                })
    except Exception as e:
        flash(f"Error loading cloud results: {str(e)}", "danger")

    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Quiz Name', 
        'Score', 
        'Total Questions', 
        'Date Taken', 
        'Data Source'
    ])
    
    for result in all_results:
        writer.writerow([
            result['quiz_name'],
            result['score'],
            result['total_questions'],
            result['timestamp'],
            result['source']
        ])

    csv_content = output.getvalue()
    output.close()

    filename = f"{student.username}_complete_results.csv"
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )




@app.route('/teacher/download_quiz_results/<int:quiz_id>')
def download_quiz_results(quiz_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Unauthorized access.", "warning")
        return redirect('/login')

    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        flash("Quiz not found.", "danger")
        return redirect('/teacher/results')

    results_data = []
    for student in User.query.filter_by(role='student').all():
        session_db = get_student_db_session(student.username)
        student_results = session_db.query(StudentQuizResult).filter_by(quiz_id=quiz_id).all()
        session_db.close()
        for res in student_results:
            results_data.append({
                'student_username': student.username,
                'score': res.score,
                'total_questions': res.total_questions,
                'timestamp': res.timestamp
            })

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student Username", "Score", "Total Questions", "Date Taken"])

    for row in results_data:
        writer.writerow([
            row['student_username'],
            row['score'],
            row['total_questions'],
            row['timestamp'].strftime("%Y-%m-%d %H:%M")
        ])

    csv_content = output.getvalue()
    output.close()

    filename = f"quiz_{quiz_id}_all_student_results.csv"
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

if __name__ == '__main__':
    app.run(debug=True, port=8080)