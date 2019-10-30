import os
from lumirandom import app, db, bcrypt
from lumirandom.forms import RegistrationForm, LoginForm, UpdateAccountForm
from lumirandom.models import User, Students, Courses, TakenCourses, Professors, TeachingAssistants, Groups, GroupInfo, Forums, ForumInfo, Threads, Posts, Ratings, role_required
from flask import render_template, url_for, flash, redirect, request, abort, g
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import func
import secrets
from PIL import Image
from random import randint
from datetime import datetime
import sys
import psycopg2

cur_year = '2019/2020'
cur_sem = 1


# Convert time to time ago from current time
def time_ago(time=False):
    from datetime import datetime
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time,datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff // 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff // 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 14:
        return "a week ago"
    if day_diff < 31:
        return str(day_diff // 7) + " weeks ago"
    if day_diff < 61:
        return "a month ago"
    if day_diff < 365:
        return str(day_diff // 30) + " months ago"
    if day_diff < 730:
        return "a year ago"
    return str(day_diff // 365) + " years ago"

def forums_sort_cid(X):
    result = {}
    for x in X:
        if x.info.prof.cid not in result:
            result[x.info.prof.cid] = []
        result[x.info.prof.cid].append(x)
    return result

def groups_sort_cid(X):
    result = {}
    for x in X:
        if x.groupinfo.prof.cid not in result:
            result[x.groupinfo.prof.cid] = []
        result[x.groupinfo.prof.cid].append(x)
    return result

def sort_posts(posts):
    child_parent_list = []
    for post in posts:
        if post.ppost_num:
            child_parent_list.append((post.post_num, post.ppost_num))
    
    has_parent = set()
    all_items = {}
    for child, parent in child_parent_list:
        if parent not in all_items:
            all_items[parent] = {}
        if child not in all_items:
            all_items[child] = {}
        all_items[parent][child] = all_items[child]
        has_parent.add(child)

    result = {}
    for key, value in all_items.items():
        if key not in has_parent:
            result[key] = value
    return result

def find_rating(ratings):
    if not ratings:
        return 0
    count = 0
    sum = 0
    for rating in ratings:
        sum += rating.rating
        count += 1
    return format(sum/count, '.2f')

@app.context_processor
def inject_info():
    if current_user.is_authenticated:
        return dict(scourses=TakenCourses.query.filter(TakenCourses.sid==current_user.id, TakenCourses.year==cur_year, TakenCourses.sem==cur_sem).order_by(TakenCourses.cid.asc()).all(), \
            sgroups=groups_sort_cid(GroupInfo.query.filter_by(sid=current_user.id).all()), \
                sforums=forums_sort_cid(ForumInfo.query.join(GroupInfo, GroupInfo.gid==ForumInfo.gid).filter(GroupInfo.sid==current_user.id).all()), \
                    pgroups=Groups.query.filter_by(pid=current_user.id).all(), pforums=Forums.query.filter_by(pid=current_user.id).all(), \
                        tagroups=Groups.query.filter_by(sid=current_user.id).all(), taforums=ForumInfo.query.join(Groups, ForumInfo.gid==Groups.gid).filter(Groups.sid==current_user.id).all(), \
                            tacid=TeachingAssistants.query.filter_by(sid=current_user.id).first())
    else:
         return dict()


@app.route("/temp")
def temp():
    return render_template('layout2.html')


@app.route("/", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        accountid = request.form['accountid']
        password = request.form['password']
        user = User.query.filter_by(id=accountid).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Welcome {user.name}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Invalid ID or Password. Please try again.', 'error')       
    return render_template('login.html')


@app.route("/home")
@login_required
def home():
    return render_template('home.html')


@app.route("/about")
@login_required
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(name=form.f_name.data + ' ' + form.l_name.data, id=form.account_id.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.f_name.data} {form.l_name.data}!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def signin():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(id=form.account_id.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash(f'Welcome {user.name}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('login'))
        else:
            flash('Invalid ID or Password. Please try again.', 'error')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
    flash(f'Logout Successful! Please Visit Again!', 'success')
    return redirect(url_for('login'))
    


@app.route("/profile/<string:id>")
@login_required
def profile(id):
    User.query.get_or_404(id)
    user = User.query.get(id)
    roles = user.roles()
    student = Students()
    prof = Professors()
    return render_template('profile.html', title='Profile ' + id, user=user, roles=roles, student=student, prof=prof)


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pictures', picture_fn)

    old_picture = current_user.image_file
    if old_picture != 'default.jpg':
        delete_picture_path = os.path.join(app.root_path, 'static/profile_pictures', old_picture)
        os.remove(delete_picture_path)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/update-profile", methods=['GET', 'POST'])
@login_required
def update_profile():
    form = UpdateAccountForm()
    student = Students()
    prof = Professors()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        if form.confirm_password.data:
            hashed_password = bcrypt.generate_password_hash(form.confirm_password.data).decode('utf-8')
            current_user.password = hashed_password
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('profile', id=current_user.id))
    return render_template('update_profile.html', title='Update Profile', student=student, prof=prof, form=form)


@app.route("/mymodules")
@login_required
@role_required(role='Student')
def modules():
    takingmods = TakenCourses.query.filter(TakenCourses.sid==current_user.id, TakenCourses.year==cur_year, TakenCourses.sem==cur_sem).all()
    takenmods = TakenCourses.query.filter(TakenCourses.sid==current_user.id, TakenCourses.year!=cur_year or (TakenCourses.year==cur_year and TakenCourses.sem<cur_sem)).order_by(TakenCourses.year.desc(), TakenCourses.sem.desc()).all()
    mods = Courses()
    profs = Professors()
    return render_template('mymodules.html', title='My Modules', takingmods=takingmods, takenmods=takenmods, mods=mods, profs=profs, cur_year=cur_year, cur_sem=cur_sem)


@app.route("/module-search")
@login_required
@role_required(role='Student')
def module_search():
    courses = Courses.query.order_by(Courses.cid.asc()).all()
    return render_template('module_search.html', title='Module Search', courses=courses, taken=TakenCourses, prof=Professors, cur_year=cur_year, cur_sem=cur_sem)


@app.route("/prof/module-search")
@login_required
@role_required(role='Professor')
def prof_module_search():
    courses = Courses.query.order_by(Courses.cid.asc()).all()
    return render_template('prof_module_search.html', title='Module Search', courses=courses, prof=Professors)


@app.route("/module-info/<string:cid>", methods=['GET', 'POST'])
@login_required
def module(cid):
    Courses.query.get_or_404(cid)
    module = Courses.query.filter_by(cid=cid).first()
    connection = psycopg2.connect(user="postgres", password="Jczk1241", host="localhost", port="5432", database="postgre")
    # print('psql connected')
    cursor = connection.cursor()
    query = ("With studentGrades(sid, cid, year,sem, grade) AS\
                (SELECT sid, cid, year, sem, CASE\
	                WHEN grade = 'A+' then 5.0\
                	WHEN grade = 'A'  then 5.0\
                	WHEN grade = 'A-' then 4.5\
	                WHEN grade = 'B+' then 4.0\
	                WHEN grade = 'B'  then 3.5\
	                WHEN grade = 'B-' then 3.0\
	                WHEN grade = 'C+' then 2.5\
	                WHEN grade = 'D+' then 1.5\
	                WHEN grade = 'D'  then 1.0\
	                WHEN grade = 'F'  then 0\
                END AS numGrade\
                FROM takencourses\
                WHERE grade IS NOT NULL\
                GROUP BY sid ,cid, year, sem),\
                AverageGPA as (\
                    SELECT cid,year,sem,ROUND(AVG(grade),2) AS GPA\
                        FROM studentGrades\
                        WHERE cid = '" + str(cid) + "'\
                        GROUP BY cid, year,sem)\
                SELECT year,sem,coalesce(GPA,0.00) as GPA from AverageGPA;")
    cursor.execute(query)
    results = cursor.fetchall()
    print(results)
    if TakenCourses.query.filter_by(sid=current_user.id, cid=cid).filter(TakenCourses.year!=cur_year or (TakenCourses.year==cur_year and TakenCourses.sem<cur_sem)).first():
        status = "taken"
    elif TakenCourses.query.filter_by(sid=current_user.id, year=cur_year, sem=cur_sem, cid=cid).first():
        status = "taking"
    elif Professors.query.filter_by(cid=cid).first() == None:
        status = "unavailable"
    else:
        status = "nil"
    prof = Professors.query.filter_by(cid=cid).first()
    # return render_template('module.html', title=cid, module=module, status=status, cur_year=cur_year, cur_sem=cur_sem, prof=prof)
    return render_template('module.html', title=cid, module=module, status=status, cur_year=cur_year, cur_sem=cur_sem, prof=prof, results=results)


@app.route("/module/<string:cid>/enrol", methods=['GET', 'POST'])
@login_required
@role_required(role='Student')
def module_enrol(cid):
    Courses.query.get_or_404(cid)
    if TakenCourses.query.filter_by(sid=current_user.id, cid=cid).filter(TakenCourses.year!=cur_year or (TakenCourses.year==cur_year and TakenCourses.sem<cur_sem)).first():
        flash(f'You have already taken {cid} {Courses.query.get(cid).cname} before.', 'warning')
    elif Professors.query.filter_by(cid=cid).first() == None:
        flash(f'Sorry! {cid} {Courses.query.get(cid).cname} is not available this semester!', 'warning')
    elif TakenCourses.query.filter_by(sid=current_user.id, year=cur_year, sem=cur_sem, cid=cid).first():
        flash(f'You are already enrolled to {cid} {Courses.query.get(cid).cname}!', 'warning')
    else:
        if TakenCourses.query.filter_by(sid=current_user.id, year=cur_year, sem=cur_sem).count() >= 6:
            flash(f'Sorry! You have already enrolled to the maximum number of modules for this semester!', 'warning')
        else:
            course = TakenCourses(sid=current_user.id, cid=cid, year=cur_year, sem=cur_sem)
            db.session.add(course)
            db.session.commit()
            flash(f'You have enrolled to {cid} {Courses.query.get(cid).cname}!', 'success')  
    return redirect(url_for('module', cid=cid))


@app.route("/module/<string:cid>/withdraw", methods=['GET', 'POST'])
@login_required
@role_required(role='Student')
def module_withdraw(cid):
    Courses.query.get_or_404(cid)
    course = TakenCourses.query.filter_by(sid=current_user.id, year=cur_year, sem=cur_sem, cid=cid).first()
    if course:
        db.session.delete(course)
        db.session.commit()
        flash(f'You have withdrawn from {cid}!', 'warning')
    else:
        flash(f'You are not enrolled to {cid}!', 'error')
    return redirect(url_for('module', cid=cid))


@app.route("/module")
@app.route("/module/<string:cid>")
@login_required
def module_take(cid=None):
    if cid == None:
        if Professors.query.get(current_user.id):
            cid = Professors.query.get(current_user.id).cid
        else:
            abort(404)
    mod = Courses.query.get_or_404(cid)
    if not Professors.query.filter_by(cid=cid).first():
        abort(404)
    is_student, is_ta, is_prof = (False for i in range(3))
    if (TakenCourses.query.filter_by(sid=current_user.id, cid=cid, year=cur_year, sem=cur_sem).first()):
        is_student = True
    if 'Professor' in current_user.roles() and Professors.query.get(current_user.id).cid==cid:
        is_prof = True
    if 'TA' in current_user.roles() and TeachingAssistants.query.filter_by(sid=current_user.id, is_ta=True).first().cid==cid:
        is_ta = True
    if is_student or is_prof or is_ta:
        prof = Professors.query.filter_by(cid=cid).first()
        groups = Groups.query.filter_by(pid=prof.pid).all()
        students = TakenCourses.query.filter_by(cid=cid, year=cur_year, sem=cur_sem).all()
        return render_template('module_take.html', title=cid + ' ' +  mod.cname, mod=mod, students=students, groups=groups, Groups=Groups, groupinfo=GroupInfo, prof=prof, is_student=is_student, is_ta=is_ta, is_prof=is_prof, year=cur_year, sem=cur_sem)
    else:
        abort(403)


@app.route("/student_list/", methods=['GET', 'POST'])
@app.route("/student_list/search/<string:query>", methods=['GET', 'POST'])
@login_required
def student_list(query=None):
    if request.method == "POST":
        s_name = request.form['search']
        if len(s_name) <= 1:
            flash(f'Please enter more than 1 character!','warning')
        else:
            return redirect(url_for('student_list', query=s_name))
    if query:
        querystr = '%' + query + '%'
        page = request.args.get('page', 1, type=int)
        students = Students.query.join(User, Students.sid==User.id).filter(User.name.like(querystr)).order_by(Students.year.asc(), User.name.asc()).paginate(page=page, per_page=15)
        return render_template('student_list.html', title='Student List', students=students, query=query)
    page = request.args.get('page', 1, type=int)
    students = Students.query.join(User, Students.sid==User.id).order_by(Students.year.asc(), User.name.asc()).paginate(page=page, per_page=15)
    return render_template('student_list.html', title='Student List', students=students, query=query)


@app.route("/ta/signup", methods=['GET', 'POST'])
@login_required
@role_required(role='Student')
def ta_signup():
    requested = TeachingAssistants.query.filter_by(sid=current_user.id, is_ta=False).all()
    if Students.query.filter(Students.sid==current_user.id, Students.year>1).first():
        takenmods = TakenCourses.query.join(Professors, TakenCourses.cid==Professors.cid).filter(TakenCourses.sid==current_user.id, TakenCourses.year!=cur_year, TakenCourses.grade.like("A%"))
        available = []
        for takenmod in takenmods:
            found = False
            for request in requested:
                if takenmod.cid == request.cid:
                    found = True
                    break
            if not found:
                available.append(takenmod)
    else:
        available = None
    profs = Professors()
    ta = TeachingAssistants.query.filter_by(sid=current_user.id, is_ta=True).first()
    return render_template('ta_signup.html', title='TA Sign Up', available=available, profs=profs, requested=requested, ta=ta)


@app.route("/ta/join/<string:cid>", methods=['GET', 'POST'])
@login_required
@role_required(role='Student')
def ta_join(cid):
    Courses.query.get_or_404(cid)
    if Professors.query.filter_by(cid=cid).first() == None:
        flash(f'Sorry! {cid} {Courses.query.get(cid).cname} is not available this semester!', 'warning')
    elif TeachingAssistants.query.filter_by(sid=current_user.id, is_ta=True).first():
        ta = TeachingAssistants.query.filter_by(sid=current_user.id, is_ta=True).first()
        if ta.cid == cid:
            flash(f'You are already a Teaching Assistant for {ta.cid} {Courses.query.get(ta.cid).cname}!', 'warning')
        else:
            flash(f'You are already a Teaching Assistant for {ta.cid} {Courses.query.get(ta.cid).cname}! You are not allowed to apply to be a Teaching Assistant for any other modules.', 'warning')
    elif TeachingAssistants.query.filter_by(sid=current_user.id, cid=cid).first():
        flash(f'You have already requested to be a Teaching Assistant for {cid} {Courses.query.get(cid).cname}.', 'warning')
    elif TakenCourses.query.get([current_user.id, cid]).grade[0] != 'A' or Students.query.get(current_user.id).year == 1:
        flash(f'Sorry! You are not eligible to be a Teaching Assistant for {cid} {Courses.query.get(cid).cname}!', 'warning')
    else:
        ta = TeachingAssistants(sid=current_user.id, cid=cid, is_ta=False)
        db.session.add(ta)
        db.session.commit()
        flash(f'Thank you for requesting to be a Teaching Assistant for {cid} {Courses.query.get(cid).cname}! Awaiting confirmation from Professor.', 'success')  
    return redirect(url_for('ta_signup'))


@app.route("/ta/withdraw/<string:cid>", methods=['GET', 'POST'])
@login_required
@role_required(role='Student')
def ta_withdraw(cid):
    Courses.query.get_or_404(cid)
    if TeachingAssistants.query.filter_by(sid=current_user.id, cid=cid, is_ta=True).first():
        flash(f'You are already a Teaching Assistant for {cid} {Courses.query.get(cid).cname} and are not allowed to withdraw anymore.', 'error')
        return redirect(url_for('ta_signup'))
    mod = TeachingAssistants.query.filter_by(sid=current_user.id, cid=cid).first()
    if mod:
        db.session.delete(mod)
        db.session.commit()
        flash(f'You have withdrawn your application as a Teaching Assistant for {cid} {Courses.query.get(cid).cname}.', 'warning')
    else:
        flash(f'You have not signed up to be a Teaching Assistant for {mod} {Courses.query.get(cid).cname}.', 'info')
    return redirect(url_for('ta_signup'))
  


@app.route("/prof_list")
@login_required
def prof_list():
    profs = Professors.query.join(User, Professors.pid==User.id).order_by(User.name.asc()).all()
    return render_template('prof_list.html', title='Professor List', profs=profs)


@app.route("/prof/mytas")
@login_required
@role_required(role='Professor')
def my_tas():
    cid = Professors.query.get(current_user.id).cid
    tas = TeachingAssistants.query.filter_by(cid=cid, is_ta=True).all()
    requests = TeachingAssistants.query.filter_by(cid=cid, is_ta=False).all()
    students = Students()
    user = User()
    return render_template('my_tas.html', title='My TAs', cid=cid, tas=tas, requests=requests, students=students, user=user, cur_year=cur_year, cur_sem=cur_sem)


@app.route("/prof/accept/<string:sid>", methods=['GET', 'POST'])
@login_required
@role_required(role='Professor')
def ta_accept(sid):
    Students.query.get_or_404(sid)
    if TeachingAssistants.query.filter_by(sid=sid, cid=Professors.query.get(current_user.id).cid).first() == None:
        flash(f'Invalid Request!', 'error')
    else:
        othersignups = TeachingAssistants.query.filter_by(sid=sid).all()
        for othersignup in othersignups:
            db.session.delete(othersignup)
        ta = TeachingAssistants(sid=sid, cid=Professors.query.get(current_user.id).cid, is_ta=True)
        db.session.add(ta)
        db.session.commit()
        flash(f'Success! {Students.query.get(sid).info.name} is now your slave!', 'success')  
    return redirect(url_for('my_tas'))


@app.route("/prof/reject/<string:sid>", methods=['GET', 'POST'])
@login_required
@role_required(role='Professor')
def ta_reject(sid):
    Students.query.get_or_404(sid)
    if TeachingAssistants.query.filter_by(sid=sid, cid=Professors.query.get(current_user.id).cid).first() == None:
        flash(f'Invalid Request!', 'error')
    elif TeachingAssistants.query.filter_by(sid=sid, cid=Professors.query.get(current_user.id).cid, is_ta=True).first():
        student = TeachingAssistants.query.filter_by(sid=sid, cid=Professors.query.get(current_user.id).cid, is_ta=True).first()
        db.session.delete(student)
        db.session.commit()
        flash(f'{Students.query.get(sid).info.name} is no longer your slave!', 'warning')  
    else:
        student = TeachingAssistants.query.filter_by(sid=sid, cid=Professors.query.get(current_user.id).cid).first()
        db.session.delete(student)
        db.session.commit()
        flash(f'{Students.query.get(sid).info.name} is rejected from being your slave!', 'warning')  
    return redirect(url_for('my_tas'))


@app.route("/mygroups")
@login_required
@role_required(role='Student')
def my_groups():
    groups = groups_sort_cid(GroupInfo.query.filter_by(sid=current_user.id).all())
    user = User()
    return render_template('my_groups.html', title='Groups', groups=groups, groupinfo=GroupInfo, user=user)


@app.route("/module/<string:cid>/groups")
@login_required
@role_required(role='Student')
def mod_groups(cid):
    mod = Courses.query.get_or_404(cid)
    if not TakenCourses.query.filter_by(sid=current_user.id, cid=cid, year=cur_year, sem=cur_sem).first():
        abort(403)
    groups = Groups.query.join(GroupInfo, GroupInfo.gid==Groups.gid).join(Professors, Professors.pid==Groups.pid).filter(GroupInfo.sid==current_user.id, Professors.cid==cid).all()
    return render_template('mod_groups.html', title=cid + ' Groups', groups=groups, groupinfo=GroupInfo, mod=mod)


@app.route("/module/<string:cid>/group/<int:gid>")
@login_required
def group(cid, gid):
    Groups.query.get_or_404(gid)
    is_student, is_ta, is_prof = (False for i in range(3))
    if Students.query.get(current_user.id) and GroupInfo.query.filter(GroupInfo.gid==gid, GroupInfo.sid==current_user.id).first():
        is_student = True
    if current_user.id==Groups.query.get(gid).sid:
        is_ta = True
    if current_user.id==Groups.query.get(gid).pid:
        is_prof = True
    if is_student or is_ta or is_prof:
        group = Groups.query.get(gid)
        students = GroupInfo.query.join(User, GroupInfo.sid==User.id).filter(GroupInfo.gid==gid).order_by(User.name.asc()).all()
        size = GroupInfo.query.filter_by(gid=group.gid).count()
        return render_template('group.html', title='Group', group=group, students=students, size=size, user=User, is_student=is_student, is_ta=is_ta, is_prof=is_prof)
    else:
        abort(403)


@app.route("/ta/groups")
@login_required
@role_required(role='TA')
def ta_groups():
    groups = Groups.query.filter_by(sid=current_user.id).all()
    groupinfo = GroupInfo()
    cid = TeachingAssistants.query.filter_by(sid=current_user.id).first().cid
    return render_template('ta_groups.html', title='TA Groups', groups=groups, groupinfo=groupinfo, cid=cid)


@app.route("/prof/groups")
@login_required
@role_required(role='Professor')
def prof_groups():
    groups = Groups.query.filter_by(pid=current_user.id).all()
    groupinfo = GroupInfo()
    cid = Professors.query.get(current_user.id).cid
    user = User()
    return render_template('prof_groups.html', title='Groups', groups=groups, groupinfo=groupinfo, user=user, cid=cid)


@app.route("/prof/create-group", methods=['GET', 'POST'])
@login_required
@role_required(role='Professor')
def create_group():
    if request.method == 'POST':
        gname = request.form['gname']
        students = request.form['students'].split(',')
        ta = request.form['ta']
        if ta == "none":
            ta = ''
        if Groups.query.first() == None:
            gid = 1
        else:
            gid = db.session.query(func.max(Groups.gid)).scalar()+1
        g = Groups(gid=gid, gname=gname, pid=current_user.id, sid=ta)
        db.session.add(g)
        for student in students:
            s = GroupInfo(gid=gid, sid=student)
            db.session.add(s)
        db.session.commit()
        flash(f'New group {gname} successfully created!', 'success')
        return redirect(url_for('prof_groups'))
    cid = Professors.query.get(current_user.id).cid
    students = TakenCourses.query.join(User, TakenCourses.sid==User.id).filter(TakenCourses.cid==cid, TakenCourses.year==cur_year, TakenCourses.sem==cur_sem).order_by(User.name.asc()).all()
    s1, s2, s3, s4, s5 = ([] for i in range(5))
    for student in students:
        if student.student.year == 1:
            s1.append(student)
        elif student.student.year == 2:
            s2.append(student)
        elif student.student.year == 3:
            s3.append(student)
        elif student.student.year == 4:
            s4.append(student)
        elif student.student.year == 5:
            s5.append(student)
    tas = TeachingAssistants.query.join(User, TeachingAssistants.sid==User.id).filter(TeachingAssistants.cid==cid).order_by(User.name.asc()).all()   
    return render_template('create_group.html', title='Create Group', students=students, s1=s1, s2=s2, s3=s3, s4=s4, s5=s5, tas=tas, cid=cid)


@app.route("/module/<string:cid>/forum/<int:fid>", methods=['GET', 'POST'])
@login_required
def forum(cid, fid):
    if request.method == 'POST':
        if request.form['btn'] == 'Create':
            title = request.form['title']
            content = request.form['content']
            if Threads.query.filter_by(fid=fid).first() == None:
                tid = 1
            else:
                tid = db.session.query(func.max(Threads.tid)).filter(Threads.fid==fid).scalar()+1
            t = Threads(fid=fid, tid=tid, id=current_user.id, title=title, content=content)
            p = Posts(fid=fid, tid=tid, post_num=1, id=current_user.id, title=title, content=content, pfid=fid, ptid=tid, ppost_num=None)
            db.session.add(t)
            db.session.add(p)
            db.session.commit()
            flash(f'Thread created successfully.', 'success')
            return redirect(url_for('threads', cid=cid, fid=fid, tid=tid))
        elif request.form['btn'] == 'Delete':
            tid = request.form['tid']
            t = Threads.query.get([fid, tid])
            db.session.delete(t)
            db.session.commit()
            flash(f'Thread has been deleted.', 'info')
            return redirect(url_for('forum', cid=cid, fid=fid))
    if not Professors.query.filter_by(cid=cid).first() or not Forums.query.get(fid) or Forums.query.get(fid).pid != Professors.query.filter_by(cid=cid).first().pid:
        abort(404)
    is_student, is_ta, is_prof = (False for i in range(3))
    if ForumInfo.query.join(GroupInfo, ForumInfo.gid==GroupInfo.gid).filter(GroupInfo.sid==current_user.id).all():
        is_student = True
    if ForumInfo.query.join(Groups, ForumInfo.gid==Groups.gid).filter(Groups.sid==current_user.id).first():
        is_ta = True
    if Forums.query.get(fid).pid == current_user.id:
        is_prof = True
    if is_student or is_ta or is_prof:
        forum = Forums.query.get(fid)
        groups = Groups.query.join(ForumInfo, ForumInfo.gid==Groups.gid).filter(ForumInfo.fid==fid).order_by(Groups.gname.asc()).all()
        size = ForumInfo.query.filter_by(fid=fid).count()
        threads = Threads.query.filter_by(fid=fid).order_by(Threads.date_created.asc()).all()
        totalthreads = Threads.query.filter_by(fid=fid).count()
        return render_template('forums.html', title='Forum - ' + forum.title, forum=forum, groups=groups, size=size, threads=threads, totalthreads=totalthreads, \
            posts=Posts, cid=cid, fid=fid, time_ago=time_ago, is_student=is_student, is_ta=is_ta, is_prof=is_prof)
    else:
        abort(403)


@app.route("/forums")
@login_required
@role_required(role='Student')
def student_forums():
    forums = forums_sort_cid(ForumInfo.query.join(GroupInfo, GroupInfo.gid==ForumInfo.gid).filter(GroupInfo.sid==current_user.id).all())
    return render_template('student_forums.html', title='Forums', forums=forums, foruminfo=ForumInfo, time_ago=time_ago)


@app.route("/<string:cid>/forums")
@login_required
@role_required(role='Student')
def mod_forums(cid):
    mod = Courses.query.get_or_404(cid)
    if not TakenCourses.query.filter_by(sid=current_user.id, cid=cid, year=cur_year, sem=cur_sem).first():
        abort(403)
    forums = ForumInfo.query.join(GroupInfo, GroupInfo.gid==ForumInfo.gid).join(Forums, Forums.fid==ForumInfo.fid).join(Professors, Professors.pid==Forums.pid)\
        .filter(GroupInfo.sid==current_user.id, Professors.cid==cid).all()
    return render_template('mod_forums.html', title=cid + ' Forums', forums=forums, foruminfo=ForumInfo, mod=mod, time_ago=time_ago)


@app.route("/prof/forum")
@login_required
@role_required(role='Professor')
def prof_forums():
    forums = Forums.query.filter_by(pid=current_user.id).all()
    foruminfo = ForumInfo()
    cid = Professors.query.get(current_user.id).cid
    user = User()
    return render_template('prof_forums.html', title='Forums', forums=forums, foruminfo=foruminfo, user=user, cid=cid, time_ago=time_ago)


@app.route("/ta/forum")
@login_required
@role_required(role='TA')
def ta_forums():
    forums = ForumInfo.query.join(Groups, Groups.gid==ForumInfo.gid).filter(Groups.sid==current_user.id).all()
    cid = TeachingAssistants.query.filter_by(sid=current_user.id).first().cid
    return render_template('ta_forums.html', title='Forums', forums=forums, foruminfo=ForumInfo, cid=cid, time_ago=time_ago)


@app.route("/prof/create-forum", methods=['GET', 'POST'])
@login_required
@role_required(role='Professor')
def create_forum():
    if request.method == 'POST':
        title = request.form['title']
        groups = request.form['groups'].split(',')
        if Forums.query.first() == None:
            fid = 1
        else:
            fid = db.session.query(func.max(Forums.fid)).scalar()+1
        f = Forums(fid=fid, title=title, pid=current_user.id)
        db.session.add(f)
        for group in groups:
            g = ForumInfo(fid=fid, gid=group)
            db.session.add(g)
        db.session.commit()
        flash(f'New forum {title} has been successfully created!', 'success')
        return redirect(url_for('prof_forums'))
    cid = Professors.query.get(current_user.id).cid
    groups = Groups.query.filter_by(pid=current_user.id).order_by(Groups.gname).all()  
    return render_template('create_forum.html', title='Create Forum', groups=groups, cid=cid)


@app.route("/module/<string:cid>/forum/<int:fid>/create_post", methods=['GET', 'POST'])
@login_required
def create_post(cid, fid):
    if not Professors.query.filter_by(cid=cid).first() or not Forums.query.get(fid) or Forums.query.get(fid).pid != Professors.query.filter_by(cid=cid).first().pid:
        abort(404)
    module = Courses.query.get(cid)
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        if Posts.query.filter_by(fid=fid).first() == None:
            postnum = 1
        else:
            postnum = db.session.query(func.max(Posts.post_num)).filter(Posts.fid==fid).scalar()+1
        p = Posts(fid=fid, post_num=postnum, title=title, id=current_user.id, content=content, p_fid=fid, p_post_num=None)
        db.session.add(p)
        db.session.commit()
        flash(f'Post created successfully.', 'success')
        return redirect(url_for('forum', cid=cid, fid=fid))
    forum = Forums.query.get(fid)
    return render_template('create_post.html',title="Create Post", module=module, forum=forum, cid=cid)


@app.route("/module/<string:cid>/forum/<int:fid>/thread/<int:tid>", methods=['GET', 'POST'])
@login_required
def threads(cid, fid, tid):
    if request.method == 'POST':
        if request.form['btn'] == 'Submit':
            title = request.form['title']
            content = request.form['content']
            pfid = fid
            ptid = tid
            ppostnum = request.form['post_num']
            postnum = db.session.query(func.max(Posts.post_num)).filter(Posts.fid==fid, Posts.tid==tid).scalar()+1
            p = Posts(fid=fid, tid=tid, post_num=postnum, id=current_user.id, title=title, content=content, pfid=pfid, ptid=ptid, ppost_num=ppostnum)
            db.session.add(p)
            db.session.commit()
            flash(f'Post created successfully.', 'success')
            return redirect(url_for('threads', cid=cid, fid=fid, tid=tid))
        elif request.form['btn'] == 'Delete':
            postnum = request.form['post_num']
            p = Posts.query.get([fid, tid, postnum])
            db.session.delete(p)
            db.session.commit()
            flash(f'Post has been deleted.', 'info')
            return redirect(url_for('threads', cid=cid, fid=fid, tid=tid))
        elif request.form['btn'] == 'Save':
            postnum = request.form['post_num']
            title = request.form['title']
            content = request.form['content']
            dateedited = datetime.now()
            Posts.query.get([fid, tid, postnum]).title = title
            Posts.query.get([fid, tid, postnum]).content = content
            Posts.query.get([fid, tid, postnum]).date_edited = dateedited
            if postnum == '1':
                Threads.query.get([fid, tid]).title = title
                Threads.query.get([fid, tid]).content = content
            db.session.commit()
            flash(f'Post edited successfully.', 'success')
            return redirect(url_for('threads', cid=cid, fid=fid, tid=tid))
        elif request.form['btn'] == 'Rate':
            postnum = request.form['post_num']
            rating = request.form['rating']
            Posts.query.get([fid, tid, postnum]).rating = rating
            if Ratings.query.get([fid, tid, postnum, current_user.id]):
                Ratings.query.get([fid, tid, postnum, current_user.id]).rating = rating
            else:
                r = Ratings(fid=fid, tid=tid, post_num=postnum, id=current_user.id, rating=rating)
                db.session.add(r)
            db.session.commit()
            return redirect(url_for('threads', cid=cid, fid=fid, tid=tid))
    if not Professors.query.filter_by(cid=cid).first() or not Forums.query.get(fid) or Forums.query.get(fid).pid != Professors.query.filter_by(cid=cid).first().pid or not Threads.query.get([fid, tid]):
        abort(404)
    is_student, is_ta, is_prof = (False for i in range(3))
    if ForumInfo.query.join(GroupInfo, ForumInfo.gid==GroupInfo.gid).filter(GroupInfo.sid==current_user.id).all():
        is_student = True
    if ForumInfo.query.join(Groups, ForumInfo.gid==Groups.gid).filter(Groups.sid==current_user.id).first():
        is_ta = True
    if Forums.query.get(fid).pid == current_user.id:
        is_prof = True
    if is_student or is_ta or is_prof:
        forum = Forums.query.get(fid)
        thread = Posts.query.get([fid, tid, 1])
        posts = Posts.query.filter_by(fid=fid, tid=tid).all()
        posts = sort_posts(posts)
        return render_template('threads.html', title='Forum Thread - ' + thread.title, forum=forum, thread=thread, p=Posts, finfo=ForumInfo, ginfo=GroupInfo, \
            posts=posts, cid=cid, fid=fid, tid=tid, time_ago=time_ago, is_student=is_student, is_ta=is_ta, is_prof=is_prof, ratings=Ratings, find_rating=find_rating)
    else:
        abort(403)


# @app.route("/test", methods = ['GET', 'POST'])
# @login_required
# def test():
#     connection = psycopg2.connect(user = "postgres", password = "Jczk1241", host = "localhost", port = "5432", database = "postgres")
#     print('psql connected')
#     cursor = connection.cursor()
#     user = current_user.id
#     query = "SELECT * from forums"
#     cursor.execute(query)
#     # cursor.execute("SELECT * from forums;")
#     results = cursor.fetchall()
#     for i in results:
#         print(i[0])
#     return render_template("test.html", title = "test")



@app.errorhandler(404)
def Error404(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def Error403(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(500)
def Error500(error):
    return render_template('errors/500.html'), 500
