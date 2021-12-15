import json
import os
import random
from datetime import timedelta

from flask import Flask, render_template, redirect, request, Response
import flask_login
from flask_login import LoginManager, login_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'adfu8y@guioau&*jjidfu1@'

login_manager = LoginManager()
login_manager.init_app(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user.db'
db = SQLAlchemy(app)

REQUIRED_RECORD = 50

class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    progress = db.Column(db.Integer)
    section = db.Column(db.Integer)
    aval_record_q = db.Column(db.Integer)
    aval_record_c = db.Column(db.Integer)
    aval_record_r = db.Column(db.Integer)

    def __repr__(self):
        return f'{self.username}'

class Comment(db.Model):
    __tablename__ = 'comment'

    cid = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.Integer, unique=True)
    question_id = db.Column(db.Integer)
    sentence_order = db.Column(db.Integer)
    type = db.Column(db.Integer)
    result = db.Column(db.Integer)

    def __repr__(self):
        return f'{self.username}'

class UserLog(flask_login.UserMixin):
    def __init__(self, uid):
        self.id = uid

@login_manager.user_loader
def user_loader(uid):
    return UserLog(uid)

@app.route("/", methods=['GET', 'POST'])
@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/home')
    if request.method == 'POST':
        username = request.form['un']
        user = User.query.filter_by(username=username).first()
        if user.password == request.form['pw']:
            userlog = user_loader(user.id)
            login_user(userlog, remember=True, duration=timedelta(days=14))
            return redirect('/home')
    return render_template('login.html')

@app.route('/logout', methods=['GET'])
def logout():
    flask_login.logout_user()
    return redirect('/login')

@app.route('/home')
@login_required
def home():
    user = User.query.filter_by(id=current_user.id).first()
    progress = min(user.aval_record_q, user.aval_record_r, user.aval_record_c)
    return render_template('home.html', user=user, progress=progress, required=REQUIRED_RECORD)

def load_images(p):
    gt = [f'/static/data/image/origin/{p}/{i}.png'.format(i) for i in range(5)]
    cps = [f'/static/data/image/cpcsv/{p}/{i}.png'.format(i) for i in range(5)]
    mgs = [f'/static/data/image/mygan/{p}/{i}.png'.format(i) for i in range(5)]
    return gt, cps, mgs

@app.route('/relevance')
@login_required
def relevance():
    user = User.query.filter_by(id=current_user.id).first()
    p = user.progress
    gt, cps, mgs = load_images(p)
    with open(f'static/data/text/{p}.txt') as f:
         txts = f.readlines()
    d = {0: 'cpcsv', 1: 'mine', 2: 'unknown'}

    return render_template('relevance.html', cps=cps, mgs=mgs, gt=gt, txts=txts, d=d)

@app.route('/consistency')
@login_required
def consistency():
    user = User.query.filter_by(id=current_user.id).first()
    p = user.progress
    gt, cps, mgs = load_images(p)

    d = {0: 'cpcsv', 1: 'mine', 2: 'unknown'}
    return render_template('consistency.html', cps=cps, mgs=mgs, gt=gt, d=d)

@app.route('/quality')
@login_required
def quality():
    user = User.query.filter_by(id=current_user.id).first()
    p = user.progress
    gt, cps, mgs = load_images(p)

    d = {0: 'cpcsv', 1: 'mine', 2: 'unknown'}

    return render_template('quality.html', cps=cps, mgs=mgs, gt=gt, d=d)

@app.route('/result', methods=['POST'])
def result():
    data = json.loads(request.data.decode('utf-8'))
    section = data['section']
    results = data['results']
    save_result(current_user.id, section, results)
    return Response(status=200)

def save_result(uid, section, results):
    d = {
        0: 'aval_record_q',
        1: 'aval_record_r',
        2: 'aval_record_c'
    }
    user = User.query.filter_by(id=uid).first()
    progress = user.progress

    # add record
    if section == 1:
        for i in range(len(results)):
            record = Comment(uid=user.id, question_id=progress, 
                            sentence_order=i, type=section, result=results[i])
            if results[i] != 'unknown':
                user.aval_record_r += 1
            db.session.add(record)
    else:
        record = Comment(uid=user.id, question_id=progress, 
                            type=section, result=results, )
        if results != 'unknown':
            if section == 0:
                user.aval_record_q += 1
            elif section == 2:
                user.aval_record_c += 1
            
        db.session.add(record)
   
    # update user progres
    if section == 2:
        user.section = 0
        user.progress += 1
    else:
        user.section = section + 1
   
    db.session.commit()

@app.route('/skip')
def skip():
    user = User.query.filter_by(id=current_user.id).first()

    #TODO: save to db

    user.progress += 1
    db.session.commit()
    return Response(status=200)

@app.route('/tutorial')
def tutorial():
    p = random.randint(2000, 2200)
    return redirect('/tuto_quality/'+str(p))

@app.route('/tuto_quality/<p>')
def tuto_quality(p):
    print(p)
    if p == None:
        p = random.randint(2000, 2321)
    gt, cps, mgs = load_images(p)
    return render_template('tuto_quality.html', cps=cps, mgs=mgs, gt=gt)

@app.route('/tuto_relevance/<p>')
def tuto_relevance(p):
    if p == None:
        p = random.randint(2000, 2200)
    gt, cps, mgs = load_images(p)
    with open(f'static/data/text/{p}.txt') as f:
        txts = f.readlines()
    return render_template('tuto_relevance.html', cps=cps, mgs=mgs, gt=gt, txts=txts)

@app.route('/tuto_consistency/<p>')
def tuto_consistency(p):
    if p == None:
        p = random.randint(2000, 2200)
    gt, cps, mgs = load_images(p)
    return render_template('tuto_consistency.html', cps=cps, mgs=mgs, gt=gt)
