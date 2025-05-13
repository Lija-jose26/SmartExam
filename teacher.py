from flask import *
from database import *

teacher=Blueprint('teacher',__name__)


@teacher.route("/conduct_exam",methods=['post','get'])
def conduct_exam():
    if 'log' in session:
        
        id=request.args['id']
        data={}
        z="select * from exam_question where exam_id='%s'"%(id)
        data['view']=select(z)
        if request.method == 'POST' and "submit" in request.form:
            
            
            qu = request.form["qu"]
            oa = request.form["oa"]
            ob = request.form["ob"]
            oc = request.form["oc"]
            od = request.form["od"]
            co = request.form["co"]
            
            z="insert into exam_question values(null,'%s','%s','%s','%s','%s','%s','%s')"%(id,qu,co,oa,ob,oc,od)
            xx=insert(z)
            return redirect(url_for('teacher.conduct_exam',id=id))
      
        
        response = make_response(render_template("conduct_exam.html",data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response
    # return render_template("conduct_exam.html")


@teacher.route("/teacher_home")
def teacher_home():
    if 'log' in session:
        response = make_response(render_template("teacher.html"))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response
    return render_template("teacher.html")


import uuid

import smtplib
from email.mime.text import MIMEText
from flask_mail import Mail, Message
from email.mime.multipart import MIMEMultipart


@teacher.route("/student_register", methods=['POST', 'GET']) 
def student_register():
    if 'log' in session:
        data = {}
        
        qrt = "select * from faculty where faculty_id='%s'" % (session['faculty'])
        ress = select(qrt)
        
        depid = ress[0]['department_id']
        
        print(depid, "///////////////")
        
        if request.method == 'POST' and "submit" in request.form:
            img = request.files["img"]
            path = "static/student/" + str(uuid.uuid4()) + img.filename
            img.save(path)
            
            firstname = request.form["fname"]
            lastname = request.form["lname"]
            phone = request.form["phone"]
            email = request.form["email"]
            date = request.form["dob"]
            place = request.form["place"]
            username = request.form["username"]
            password = request.form["password"]
        
            print(firstname, lastname, phone, email, date, place, username, password)
            
             # Check if Username Already Exists
            check_username_query = "SELECT * FROM login WHERE username = '%s'" % (username)
            existing_user = select(check_username_query)

            if existing_user:
                return """
                    <script>
                        alert('Username already exists! Please choose a different username.');
                        window.history.back();
                    </script>
                """

            # Check if Student with Same Email or Phone Exists
            check_student_query = "SELECT * FROM student WHERE email = '%s' OR phone = '%s'" % (email, phone)
            existing_student = select(check_student_query)

            if existing_student:
                return """
                    <script>
                        alert('A student with the same email or phone number already exists.');
                        window.history.back();
                    </script>
                """

            
            # Insert into the login table
            login_query = "INSERT INTO login VALUES (NULL, '%s', '%s', 'student')" % (username, password)
            login_id = insert(login_query)  # Assuming `insert` returns the inserted ID
            
            student_query = """
                INSERT INTO student 
                (login_id, teacher_id, department_id, first_name, last_name, phone, email, dob, place, file_path)
                VALUES 
                ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')
            """ % (login_id, session['faculty'], depid, firstname, lastname, phone, email, date, place, path)
            insert(student_query)
            
            # Send email notification
            send_email_student_reg(email,username,password)
            
            return '''<script>alert("Student registered successfully"); window.location="/student_register";</script>'''
        
        response = make_response(render_template("student_register.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response
    return render_template("student_register.html", data=data)

def send_email_student_reg(to_email,u,p):
    try:
        gmail = smtplib.SMTP('smtp.gmail.com', 587)
        gmail.ehlo()
        gmail.starttls()
        gmail.login('hariharan0987pp@gmail.com', 'rjcbcumvkpqynpep')

        msg = MIMEMultipart()
        msg['From'] = 'hariharan0987pp@gmail.com'
        msg['To'] = to_email
        msg['Subject'] = 'Registered Successfully'
        
        body = 'You have been registered successfully as a student.Your Username is '+u+" and password is "+p
        msg.attach(MIMEText(body, 'plain'))

        gmail.send_message(msg)
        gmail.quit()
        print("Email sent successfully")

    except smtplib.SMTPException as e:
        print(f"Failed to send email: {e}")
        raise



# Manage Students

@teacher.route("/manage_student", methods=['GET', 'POST'])
def manage_student():
    if 'log' in session:

        data = {}

        qrt = "SELECT * FROM faculty WHERE faculty_id='%s'" % (session['faculty'])
        ress = select(qrt)

        depid = ress[0]['department_id']

        print(depid, "///////////////")

        # Fetch all students
        a = "SELECT * FROM student WHERE department_id='%s'" % (depid)
        data['view'] = select(a)

        if 'action' in request.args:
            action = request.args['action']
            student_id = request.args['id']

            if action == 'delete':
                qry1 = "DELETE FROM student WHERE student_id='%s'" % (student_id)
                delete(qry1)
                return '''<script>alert("Student deleted successfully"); window.location="/manage_student";</script>'''

            if action == 'update':
                qry = "SELECT * FROM student WHERE student_id = '%s'" % (student_id)
                res = select(qry)
                data['up'] = res

        # Handle the form submission for updating student
        if 'submit' in request.form:
            # Get updated values from form
            firstname = request.form.get("fname")  # Use request.form.get()
            lastname = request.form.get("lname")
            phone = request.form.get("phone")
            email = request.form.get("email")
            date = request.form.get("dob")
            place = request.form.get("place")

            # Ensure that all required fields are filled
        

            # Check if a new image is uploaded
            if 'img' in request.files and request.files['img'].filename != '':
                img = request.files["img"]
                path = "static/student/" + str(uuid.uuid4()) + img.filename
                img.save(path)

                # Update query with image path
                up_qry = """
                UPDATE student 
                SET 
                    first_name = '%s', 
                    last_name = '%s', 
                    phone = '%s', 
                    email = '%s', 
                    dob = '%s', 
                    place = '%s', 
                    file_path = '%s' 
                WHERE 
                    student_id = '%s'
                """ % (firstname, lastname, phone, email, date, place, path, student_id)
            else:
                # Update query without image path
                up_qry = """
                UPDATE student 
                SET 
                    first_name = '%s', 
                    last_name = '%s', 
                    phone = '%s', 
                    email = '%s', 
                    dob = '%s', 
                    place = '%s' 
                WHERE 
                    student_id = '%s'
                """ % (firstname, lastname, phone, email, date, place, student_id)

            # Execute the update query
            update(up_qry)
            return '''<script>alert("Student updated successfully"); window.location="/manage_student";</script>'''
        response = make_response(render_template("manage_student.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

    return render_template("manage_student.html", data=data)

@teacher.route("/student_details/<int:student_id>", methods=['GET'])
def view_student_details(student_id):
    if 'log' in session:

        qry = f"SELECT * FROM student WHERE student_id = {student_id}"
        student = select(qry)

        if not student:
            return "Student not found", 404

        data = {'student': student[0]}
        response = make_response(render_template("student_details.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

    return render_template("student_details.html", data=data)


@teacher.route("/viewstudentt", methods=["GET", "POST"])
def viewstudentt():
    if 'log' in session:

        data={}
        a="SELECT * FROM `student` INNER JOIN `department` USING(department_id) WHERE teacher_id='%s'"%(session['faculty'])
        data['view']=select(a)
        response = make_response(render_template("viewstudentt.html",data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response
    return render_template("viewstudentt.html",data=data)


@teacher.route("/view_course")
def view_course():
    if 'log' in session:

        data={}
        query = "select * from course"
        data['view']=select(query)
        response = make_response(render_template("view_course.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response
        
    return render_template("view_course.html", data=data)


@teacher.route("/view_semester")
def view_semester():
    if 'log' in session:

        data = {}
        faculty_id = session.get("faculty")

        query = f"""
            SELECT c.course_name, COUNT(s.semester_id) AS semester_count
            FROM course c
            INNER JOIN semester s ON c.course_id = s.course_id
            INNER JOIN department d ON c.department_id = d.department_id
            INNER JOIN faculty t ON d.department_id = t.department_id
            WHERE t.faculty_id = {faculty_id}
            GROUP BY c.course_id, c.course_name
        """

        try:
            data['view'] = select(query)
        except Exception as e:
            data['error'] = str(e)
        response = make_response(render_template("view_semester.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response
            

    return render_template("view_semester.html", data=data)




@teacher.route("/assigned_subject")
def assigned_subject():
    if 'log' in session:

        faculty_id = session['faculty']  
        data = {}
        dept_query = f"SELECT department_id FROM faculty WHERE faculty_id = '{faculty_id}'"
        dept_result = select(dept_query) 

        if dept_result:
            department_id = dept_result[0]['department_id'] 
            query = f"""
                SELECT f.first_name, f.last_name,
                    s.subject_name, sem.semester_name, c.course_name, d.department_name
                FROM faculty f
                INNER JOIN subject s ON f.faculty_id = s.teacher_id
                INNER JOIN semester sem ON s.semester_id = sem.semester_id
                INNER JOIN course c ON sem.course_id = c.course_id
                INNER JOIN department d ON c.department_id = d.department_id
                WHERE d.department_id = '{department_id}'
            """ 

            data['view'] = select(query) 
        response = make_response(render_template("assigned_subject.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response
    return render_template("assigned_subject.html", data=data)



@teacher.route("/examnotifications")
def examnotifications():
    if 'log' in session:

        if 'faculty' not in session:
            return redirect(url_for('pub.login'))  

        faculty_id = session['faculty']  
        print(f"Logged-in Faculty ID: {faculty_id}")  # Debugging step

        # Fetch the department_id of the logged-in faculty member
        dept_query = f"""
            SELECT department_id 
            FROM faculty 
            WHERE faculty_id = '{faculty_id}'
        """
        teacher_department = select(dept_query)[0]['department_id']
        print(f"Faculty Department ID: {teacher_department}")  # Debugging step

        # Fetch exam notifications only for the teacher's department
        query = f"""
        SELECT 
            exam.exam_id, 
            exam.exam_date, 
            subject.subject_name, 
            exam.title, 
            exam.notification_date 
        FROM exam 
        JOIN subject ON exam.subject_id = subject.subject_id
        JOIN faculty ON subject.teacher_id = faculty.faculty_id
        WHERE faculty.department_id = '{teacher_department}'
        ORDER BY exam.exam_date ASC
        """

        # Get the exam notifications for the teacher's department
        data = {'view': select(query)}
        print(f"Exam Notifications Data: {data['view']}")  # Debugging step
        
        # Handle case where no exam notifications are found
        if not data['view']:
            data['view'] = []
        response = make_response(render_template("examnotifications.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response
            

    return render_template("examnotifications.html", data=data)


# @teacher.route("/conductexam", methods=['POST', 'GET'])
# def conduct_exam():
#     if 'log' in session:

#         if "submit" in request.form:
#             exam_name = request.form["exam_name"]
#             course_id = request.form["course_id"]
#             semester_id = request.form["semester_id"]
#             subject_id = request.form["subject_id"]
#             date = request.form["date"]
#             time = request.form["time"]
            
#             query = "insert into exams values(null, '%s', '%s', '%s', '%s', '%s', '%s')" % (exam_name, course_id, semester_id, subject_id, date, time)
#             insert(query)
#             flash("Exam scheduled successfully.", "success")
            
#         courses = select("select * from courses")
#         semesters = select("select * from semester")
#         subjects = select("select * from subjects")
#         response = make_response(render_template("conductexam.html", courses=courses, semesters=semesters, subjects=subjects))
#     else:
#         response = make_response("""
#             <script>
#                 alert('Session Expired');
#                 window.location.href = '/';
#             </script>
#         """)
    
#     response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
#     response.headers['Pragma'] = 'no-cache'
#     response.headers['Expires'] = '0'
    
#     return response
            

        
#     return render_template("conductexam.html", courses=courses, semesters=semesters, subjects=subjects)


@teacher.route("/examonitoring")
def exam_monitoring():
    query = "select * from exams"
    exams = select(query)
    return render_template("examonitoring.html", data=exams)



@teacher.route("/send_examreport", methods=['GET', 'POST'])
def send_examreport():
    if 'log' in session:

        data = {}

        faculty_id = session.get('faculty')  # Fetch logged-in faculty's ID
        
        # Fetch faculty's department
        department_query = f"SELECT department_id FROM faculty WHERE faculty_id = '{faculty_id}'"
        department_data = select(department_query)

        if not department_data:
            flash("Department not found for faculty!", "danger")
            return redirect(url_for('teacher.dashboard'))  # Redirect if no department found

        department_id = department_data[0]['department_id']

        # Fetch exams using subject and faculty tables
        data['exams'] = select(f"""
            SELECT e.exam_id, e.title 
            FROM exam e
            JOIN subject s ON e.subject_id = s.subject_id
            JOIN faculty f ON s.teacher_id = f.faculty_id  -- Linking subject to faculty
            WHERE f.department_id = '{department_id}'
        """)

        # Fetch students only from the faculty's department
        data['students'] = select(f"""
            SELECT student_id, CONCAT(first_name, ' ', last_name) AS student_name 
            FROM student 
            WHERE department_id = '{department_id}'
        """)

        if 'submit' in request.form:
            # Extracting form data
            exam_id = request.form['exam_id']
            student_id = request.form['student_id']
            marks = request.form['mark']
            report = request.form['report']
            
            query = "INSERT INTO exam_report VALUES(null, '%s', '%s', '%s', '%s')" % (exam_id, student_id, marks, report)
            insert(query)
            
            flash("Exam report submitted successfully!", "success")
            return redirect(url_for('teacher.send_examreport'))
        
        # Fetch reports related to this faculty's department
        data['reports'] = select(f"""
            SELECT 
                er.report_id, 
                e.title AS exam_title, 
                CONCAT(s.first_name, ' ', s.last_name) AS student_name, 
                er.mark, 
                er.report,er.malpractice_description,er.browser_report_path
            FROM exam_report er
            INNER JOIN exam e ON er.exam_id = e.exam_id
            INNER JOIN student s ON er.student_id = s.student_id
            INNER JOIN subject sub ON e.subject_id = sub.subject_id
            INNER JOIN faculty f ON sub.teacher_id = f.faculty_id  -- Linking subject to faculty
            WHERE f.department_id = '{department_id}'
            ORDER BY er.report_id DESC
        """)
        response = make_response(render_template("send_examreport.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response
 
    return render_template("send_examreport.html", data=data)
