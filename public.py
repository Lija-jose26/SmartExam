from flask import *
from database import *

pub=Blueprint('pub',__name__)


@pub.route("/")
def home():
    return render_template("home.html")

from running import *


@pub.route("/login",methods=['post','get']) 


# The function handling the login process
def login():
    if "submit" in request.form:
        username = request.form["username"]
        password = request.form["password"]
        print(username, password)

        q = "select * from login where username='%s' and password='%s'" % (username, password)
        db = select(q)
        print(db)

        if db:
            session['log'] = db[0]['login_id']
            if db[0]["usertype"] == "admin":
                return redirect(url_for("adm.admin"))
            if db[0]["usertype"] == "HOD":
                qry1 = "select * from faculty where login_id='%s'" % (session['log'])
                res1 = select(qry1)
                if res1:
                    session['dept'] = res1[0]['department_id']
                    session['faculty'] = res1[0]['faculty_id']
                    return redirect(url_for("hod.hod_home"))
            if db[0]["usertype"] == "faculty":
                qry2 = "select * from faculty where login_id='%s'" % (session['log'])
                res2 = select(qry2)
                if res2:
                    session['faculty'] = res2[0]['faculty_id']
                    return redirect(url_for("teacher.teacher_home"))

            if db[0]["usertype"] == "student":
                qry = "select * from student where login_id='%s'" % (session['log'])
                res = select(qry)
                if res:
                    session['student'] = res[0]['student_id']
                    session['student_name'] = res[0]['first_name'] + " " + res[0]['last_name']  # Store full name
                    session['login_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    #print("Student Logged In - ID:", session['student'])
                    print("Student Logged In - ID:", session['student'], "Name:", session['student_name'])

                    # Check if student is logging in for the first time
                    if 'student_logged_in' not in session:
                        running()
                        session['student_logged_in'] = True

                return redirect(url_for("student.student_home"))
        else:
            return """<script>alert("Invalid user");window.location='/login'</script>"""

    return render_template("login.html")






@pub.route('/logout')
def logout():
    session.clear()
    return redirect('/')



@pub.route('/logo')
def logo():
    if 'student' in session:
        session['logout_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        running()

    session.clear()
    return redirect('/')


