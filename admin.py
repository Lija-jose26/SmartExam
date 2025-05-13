from flask import *
from database import *
app = Flask(__name__)

adm=Blueprint('adm',__name__)


@adm.route("/admhome")
def admin():
    if 'log' in session:
        response = make_response(render_template("admhome.html"))
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
    
    # return render_template("admhome.html")
import uuid


import smtplib
from email.mime.text import MIMEText
from flask_mail import Mail, Message
from email.mime.multipart import MIMEMultipart

@adm.route("/faculty_register", methods=['POST', 'GET'])
def faculty_register():
    if 'log' in session:
        if request.method == 'POST' and 'submit' in request.form:
            firstname = request.form.get("fname")
            lastname = request.form.get("lname")
            phone = request.form.get("phone")
            email = request.form.get("email")
            date = request.form.get("dob")
            qualification = request.form.get("qualification")
            username = request.form.get("username")
            password = request.form.get("password")
            img = request.files['img']
            path = "static/faculty/" + str(uuid.uuid4()) + img.filename
            img.save(path)
            department_id = request.form.get("department_id")
            
            check_username_query = "SELECT * FROM login WHERE username = '%s'" % (username)
            existing_user = select(check_username_query)

            if existing_user:
                return """
                    <script>
                        alert('Username already exists! Please choose a different username.');
                        window.history.back();
                    </script>
                """

            # **2. Check if Faculty Member with Same Email or Phone Exists**
            check_faculty_query = "SELECT * FROM faculty WHERE email = '%s' OR phone = '%s'" % (email, phone)
            existing_faculty = select(check_faculty_query)

            if existing_faculty:
                return """
                    <script>
                        alert('A faculty member with the same email or phone number already exists.');
                        window.history.back();
                    </script>
                """


            login_query = "INSERT INTO login (username, password, usertype) VALUES ('%s', '%s', 'faculty')" % (username, password)
            login_id = insert(login_query)

            faculty_query = "INSERT INTO faculty (faculty_id, login_id, first_name, last_name, phone, email, dob, qualification, file_path, department_id) VALUES (null, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')" % (
                login_id, firstname, lastname, phone, email, date, qualification, path, department_id)
            insert(faculty_query)

            # Send email notification
            send_email_faculty_reg(email,username,password)
            return '''<script>alert("Faculty registered successfully"); window.location="/faculty_register";</script>'''
        

            # Retrieve data for departments
            data = {}
            a = "SELECT * FROM department"
            data['view'] = select(a)

            # Render the faculty registration page with department data
            return render_template("faculty_register.html", data=data)

        else:
            # GET request: Render the form to register the faculty
            data = {}
            a = "SELECT * FROM department"
            data['view'] = select(a)
            response = make_response(render_template("faculty_register.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)

    # Set headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response

def send_email_faculty_reg(to_email,u,p):
    try:
        gmail = smtplib.SMTP('smtp.gmail.com', 587)
        gmail.ehlo()
        gmail.starttls()
        gmail.login('hariharan0987pp@gmail.com', 'rjcbcumvkpqynpep')

        msg = MIMEMultipart()
        msg['From'] = 'hariharan0987pp@gmail.com'
        msg['To'] = to_email
        msg['Subject'] = 'Registered Successfully'
        body = 'REGISTRATION SUCCESSFULL!      Your account has been created successfully. Happy teaching!.Your username is '+u+" and password is "+p
        msg.attach(MIMEText(body, 'plain'))

        gmail.send_message(msg)
        gmail.quit()
        print("Email sent successfully")

    except smtplib.SMTPException as e:
        print(f"Failed to send email: {e}")
        raise



@adm.route("/manage_faculty", methods=['GET', 'POST'])
def mng():
    if 'log' in session:
        action = request.args.get("action")
        faculty_id = request.args.get("id")
        data = {}

    # Update faculty
        if action == "update" and faculty_id:
            if request.method == 'POST':
                firstname = request.form.get("fname")
                lastname = request.form.get("lname")
                phone = request.form.get("phone")
                email = request.form.get("email")
                dob = request.form.get("dob")
                qualification = request.form.get("qualification")
                img = request.files.get("img")

                if img:
                    path = "static/faculty/" + str(uuid.uuid4()) + img.filename
                    img.save(path)
                    update_query = """
                        UPDATE faculty SET first_name = '%s', last_name = '%s', phone = '%s', email = '%s', dob = '%s', 
                        qualification = '%s', file_path = '%s' WHERE faculty_id = '%s'
                    """ % (firstname, lastname, phone, email, dob, qualification, path, faculty_id)
                else:
                    update_query = """
                        UPDATE faculty SET first_name = '%s', last_name = '%s', phone = '%s', email = '%s', dob = '%s', 
                        qualification = '%s' WHERE faculty_id = '%s'
                    """ % (firstname, lastname, phone, email, dob, qualification, faculty_id)
                
                update(update_query)
                return '''<script>alert("Faculty updated successfully"); window.location="/manage_faculty";</script>'''

        # Fetch the details of the faculty to be updated
            data['up'] = select("SELECT * FROM faculty WHERE faculty_id = '%s'" % faculty_id)
            return render_template("manage_faculty.html", data=data)

        
        # Delete faculty
        elif action == "delete" and faculty_id:
            # First, delete from login where faculty is linked
            delete_query_login = """
                DELETE FROM login WHERE login_id = 
                (SELECT login_id FROM faculty WHERE faculty_id = '%s')
            """ % faculty_id
            delete(delete_query_login)  # Execute login delete first

            # Then, delete from faculty
            delete_query_faculty = "DELETE FROM faculty WHERE faculty_id = '%s'" % faculty_id
            delete(delete_query_faculty)

            return '''<script>alert("Faculty deleted successfully"); window.location="/manage_faculty";</script>'''


    # View all faculty
        else:
            # Fetch all faculty details
            data['view'] = select("SELECT * FROM faculty")
           

        response = make_response(render_template("manage_faculty.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    # Set headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@adm.route("/view_faculty", methods=["GET", "POST"]) 
def view_faculty():
    data = {}
    if 'log' in session:

        a = "SELECT * FROM `faculty` INNER JOIN `department` USING(department_id)"
        res = select(a)
        
        if res:
            # Create a dictionary to store faculties grouped by department
            faculty_by_department = {}
            for faculty in res:
                department_name = faculty['department_name']  
                if department_name not in faculty_by_department:
                    faculty_by_department[department_name] = []
                faculty_by_department[department_name].append(faculty)
            
            # Add the grouped data to the existing dictionary
            data['faculty_by_department'] = faculty_by_department
        response = make_response(render_template("view_faculty.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    # Set headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
        
    return render_template("view_faculty.html", data=data)


@adm.route("/view_student", methods=["GET", "POST"])
def view_student():
    if 'log' in session:

        data = {}
        
        # Query to fetch students with their department details
        query = "SELECT student.*, department.department_name FROM `student` INNER JOIN `department` USING(department_id) order by first_name asc"
        
        # Fetch the data
        students = select(query)
        
        # Group students by department
        students_by_department = {}
        for student in students:
            department_name = student['department_name']
            if department_name not in students_by_department:
                students_by_department[department_name] = []
            students_by_department[department_name].append(student)

        data['students_by_department'] = students_by_department
        response = make_response(render_template("view_student.html", data=data))
    else:
        response = make_response("""
                <script>
                    alert('Session Expired');
                    window.location.href = '/';
                </script>
            """)
    # Set headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
    

    return render_template("view_student.html", data=data)


@adm.route("/managedepartment", methods=["GET", "POST"])
def managedepartment():
    if 'log' in session:
        data = {}
        # Fetch all departments
        a = "SELECT * FROM department"
        data['view'] = select(a)
        
        # Check for GET actions
        if 'action' in request.args:
            action = request.args['action']
            department_id = request.args.get('id')

            if action == 'delete':  # Delete Department
                qry1 = "DELETE FROM department WHERE department_id = '%s'" % department_id
                delete(qry1)
                return '''<script>alert("Department deleted successfully."); 
                        window.location="/managedepartment";</script>'''

            elif action == 'view_faculties':  # View Faculties
                faculty_query = f"""
                    SELECT 
                        faculty_id, 
                        CONCAT(first_name, ' ', last_name) AS faculty_name, 
                        phone, 
                        email, 
                        dob, 
                        qualification 
                    FROM faculty 
                    WHERE department_id = '{department_id}'
                """
                faculties = select(faculty_query)
                data['faculties'] = faculties
                data['department_id'] = department_id

            elif action == 'edit':  # Edit Department
                if department_id:
                    # Fetch department details for editing
                 query = "SELECT * FROM department WHERE department_id = '%s'" % department_id
                department = select(query)

                if department:
                        data['department'] = department[0]
                        # Render the edit department page with the department data
                        return render_template("editdept.html", data=data)
                else:
                        data['error'] = "Department not found."
        
        # Handle POST actions (for adding or updating departments)
        if request.method == "POST":
            department_name = request.form.get("department_name")
            department_id = request.form.get("department_id")
            
            if department_name:
                if department_id:
                    # Update the department
                    query = "UPDATE department SET department_name = %s WHERE department_id = %s"
                    update(query, (department_name, department_id))
                else:
                    # Add a new department
                 query = "INSERT INTO department (department_name) VALUES ('%s')" % department_name
                insert(query)

                
                return '''<script>alert("Department added/updated successfully."); 
                        window.location="/managedepartment";</script>'''
            else:
                return '''<script>alert("Please provide a department name."); 
                        window.location="/managedepartment";</script>'''
        response = make_response(render_template("managedepartment.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    # Set headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response       

    return render_template("managedepartment.html", data=data)

@adm.route("/editdept/<int:department_id>", methods=["GET", "POST"])
def editdept(department_id):
    if 'log' in session:

        data = {}

        if request.method == "GET":
            if department_id:
                # Fetch the department details to display in the form
                query = f"SELECT * FROM department WHERE department_id = {department_id}"
                department = select(query) 
                if department:
                    data['department'] = department[0]
                else:
                    data['error'] = "Department not found."
            else:
                data['error'] = "Invalid department ID."

        elif request.method == "POST":
            department_name = request.form.get("department_name")
            if department_name and department_id:
                # Update the department
                update_query = f"UPDATE department SET department_name = '{department_name}' WHERE department_id = {department_id}"
                update(update_query)
                return '''<script>alert("Department updated successfully."); 
                        window.location="/managedepartment";</script>'''
            else:
                data['error'] = "Please provide a department name."  
        return render_template("editdept.html", data=data)
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
    
    # Set headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response       


    return render_template("editdept.html", data=data)

@adm.route("/managecourse", methods=["GET", "POST"])
def managecourse():
    if 'log' in session:
        data = {}

        # Fetch departments for the dropdown to associate with courses
        departments_query = "SELECT * FROM department"
        data['view'] = select(departments_query)

        if request.method == "POST":
            course_name = request.form['course_name']
            department_id = request.form['department_id']
            course_id = request.form.get('course_id')  # Get course_id for update, if available
            
            if course_id:  # If course_id is present, update the course
                update_query = f"UPDATE course SET course_name='{course_name}', department_id='{department_id}' WHERE course_id='{course_id}'"
                update(update_query)
                return '''<script>alert("Course updated successfully."); window.location="/managecourse";</script>'''
            else:  # Otherwise, insert a new course
                insert_query = f"INSERT INTO course (course_name, department_id) VALUES ('{course_name}', '{department_id}')"
                insert(insert_query)
                return '''<script>alert("Course added successfully."); window.location="/managecourse";</script>'''

        # Fetch all courses for the table
        courses_query = "SELECT c.course_id, c.course_name, d.department_name FROM course c JOIN department d ON c.department_id = d.department_id"
        data['courses'] = select(courses_query)
        
        # Handle actions like delete and edit
        if 'action' in request.args:
            action = request.args['action']
            course_id = request.args['id']
            
            if action == 'delete':  # Delete course
                delete_query = f"DELETE FROM course WHERE course_id='{course_id}'"
                delete(delete_query)
                return '''<script>alert("Course deleted successfully."); window.location="/managecourse";</script>'''
        response = make_response(render_template("managecourse.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
        
    # Set headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

            
            
        # return render_template("managecourse.html", data=data)

# Route for managing semesters
@adm.route("/Manage_semester", methods=["GET", "POST"])
def Manage_semester():
    if 'log' in session:
        data = {}

        # Retrieve 'course_id' from the URL parameters
        course_id = request.args.get('id')
        
        if not course_id:
            flash("Course ID is missing.", "danger")
            return redirect("/managecourse")  # Redirect to course management page

        # Fetch available semesters for the selected course
        query_semesters = """
        SELECT s.semester_id, s.semester_name, c.course_name
        FROM Semester s
        JOIN Course c ON s.course_id = c.course_id
        WHERE s.course_id = %s
    """ % (course_id,)  # Directly format the string with the course_id
        data['semesters'] = select(query_semesters)  # Pass the formatted query


        # Fetch available course data for course details in the form
        query_courses = "SELECT * FROM Course WHERE course_id = %s"%(course_id,)
        data['course'] = select(query_courses)

        # Handle form submission for adding a semester
        if request.method == "POST" and "submit_semester" in request.form:
            semester_name = request.form['semester_name']
            query_insert="insert into  semester values(null,'%s','%s')" %(semester_name,course_id)
            res=insert(query_insert)
            print(res)

            flash("Semester added successfully!", "success")
            return redirect(f"/Manage_semester?id={course_id}")  

        if 'action' in request.args and request.args['action'] == 'delete_semester':
            semester_id = request.args.get('id')

            if semester_id:
                query_delete = "DELETE FROM semester WHERE semester_id = '%s'" %semester_id
                delete(query_delete)
                flash("Semester deleted successfully!", "success")
                return redirect(f"/Manage_semester?id={course_id}")  # Refresh the page to remove the deleted semester
            else:
                flash("Semester ID is missing.", "danger")
                return redirect(f"/Manage_semester?id={course_id}")
        response = make_response(render_template("manage_semester.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
        
    # Set headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
    

    return render_template("manage_semester.html", data=data)

if __name__ == "__main__":
    app.run(debug=True)



@adm.route("/add_subject", methods=["GET", "POST"])
def add_subject():
    if 'log' in session:

        data = {}
        semester_id = request.args.get("id")
        if semester_id:
            # Fetch all subjects related to the selected semester
            subjects_query = """
            SELECT s.subject_id, s.subject_name
            FROM subject s
            WHERE s.semester_id = %s
            """ % (semester_id,)
            data['subjects'] = select(subjects_query)
        else:
            data['subjects'] = []

        # Handle the form submission to add a new subject
        if "submit" in request.form:
            subject_name = request.form['subject_name']
            
            if subject_name:
                # Insert the new subject into the database (no teacher assignment)
                insert_query = """
                INSERT INTO subject (subject_name, semester_id)
                VALUES ('%s', '%s')
                """ % (subject_name, semester_id)  # String interpolation for inserting the values
                
                # Call the insert function (passing only the query as a single argument)
                insert(insert_query)
                return '''<script>alert("Subject Added successfully."); window.location="/add_subject?id={semester_id}";</script>'''.format(semester_id=semester_id)
            else:
                flash("Please fill in all fields", "error")
        
        # Handle delete subject action
        if 'action' in request.args:
            action = request.args['action']
            subject_id = request.args['id']
            
            if action == 'delete_subject':  # Delete subject by ID
                delete_query = "DELETE FROM subject WHERE subject_id='%s'" % subject_id
                delete(delete_query)
                return '''<script>alert("Subject deleted successfully."); window.location="/add_subject?id={semester_id}";</script>'''.format(semester_id=semester_id)
        response = make_response(render_template("add_subject.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
        
    # Set headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
    return render_template("add_subject.html", data=data)

@adm.route("/view_subjects", methods=["GET"])
def view_subjects():
    if 'log' in session:

        course_id = request.args.get("id")  # Get the course_id from the URL parameter
        data = {}
        
        if course_id:
            
            # Fetch all semesters related to this course
            semesters_query = """
            SELECT semester_id, semester_name
            FROM semester
            WHERE course_id = %s
            """ % (course_id,)
            data['semesters'] = select(semesters_query)  # Assuming you have a select function to fetch data
            
            # Fetch all subjects for each semester
            for semester in data['semesters']:
                semester['subjects'] = []
                subjects_query = """
                SELECT subject_id, subject_name
                FROM subject
                WHERE semester_id = %s
                """ % (semester['semester_id'])
                semester['subjects'] = select(subjects_query)
        response = make_response(render_template("view_subjects.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
        
    # Set headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
    return render_template("view_subjects.html", data=data)

@adm.route("/assign_subject", methods=["GET", "POST"])
def assign_subject():
    if 'log' in session:

        data = {}

        # Fetch all teachers
        query_teachers = "SELECT faculty_id, first_name, last_name FROM faculty"
        data['teachers'] = select(query_teachers)
         # Fetch subjects for dropdown (Fixing the issue)
        query_subject_dropdown = "SELECT subject_id, subject_name FROM subject"
        data['subjects'] = select(query_subject_dropdown)

        # Fetch subjects grouped by department
        query_subjects = """
        SELECT 
            d.department_name,
            s.subject_id, 
            s.subject_name, 
            sem.semester_name, 
            c.course_name, 
            IFNULL(CONCAT(f.first_name, ' ', f.last_name), 'Not Assigned') AS teacher_name
        FROM 
            subject s
        JOIN 
            semester sem ON s.semester_id = sem.semester_id
        JOIN 
            course c ON sem.course_id = c.course_id
        JOIN 
            department d ON c.department_id = d.department_id
        LEFT JOIN 
            faculty f ON s.teacher_id = f.faculty_id
        ORDER BY 
            d.department_name, s.subject_name;
        """
        subjects = select(query_subjects)

        # Group subjects by department
        department_wise_data = {}
        for subject in subjects:
            department = subject['department_name']
            if department not in department_wise_data:
                department_wise_data[department] = []
            department_wise_data[department].append(subject)

        data['department_wise_data'] = department_wise_data

        return render_template("assign_subject.html", data=data)

    else:
        return make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
     # Set headers to prevent caching
    
 
    return render_template("assign_subject.html", data=data)  # Ensure data includes both teachers and subjects

@adm.route("/manage_exam", methods=['POST', 'GET'])
def manage_exam():
    if 'log' in session:

        data = {}
        # Fetch all subjects to populate the dropdown
        qry = "SELECT subject_id, subject_name FROM subject"
        res = select(qry)
        if res:
            data['view'] = res

        data1 = {}
        # Fetch all exams with corresponding subject names
        qry2 = """
            SELECT e.exam_id,e.exam_date, e.notification_date, e.title,e.time, s.subject_name 
            FROM exam e
            INNER JOIN subject s USING(subject_id)
        """
        res2 = select(qry2)
        if res2:
            data1['viewd'] = res2

        # Handle form submission
        if "submit" in request.form:
            exam_date = request.form["exam_date"]
            subject_id = request.form["subject_id"]
            title = request.form["title"]
            time = request.form["time"]
        # notification_date = request.form["notification_date"]
            
            # Insert exam details into the exam table
            query_insert="insert into  exam values(null,'%s', '%s', '%s', curdate(),'%s')" %(exam_date,subject_id, title,time) 
            res=insert(query_insert)
            print(res)
            return '''<script>alert("Exam added successfully."); window.location="/manage_exam";</script>'''
        response = make_response(render_template("manage_exam.html", data=data, data1=data1))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
        
    # Set headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
       
    return render_template("manage_exam.html", data=data, data1=data1)

@adm.route("/delete_exam/<int:exam_id>")
def delete_exam(exam_id):
    print(session) 
    if 'log' in session:
        qry = "DELETE FROM exam WHERE exam_id = %s" % (exam_id)
        delete(qry)
        return '''<script>alert("Exam deleted successfully."); window.location="/manage_exam";</script>'''
    else:
        return '''<script>alert("Session Expired"); window.location="/";</script>'''



@adm.route("/view_all_examreports", methods=['GET'])
def view_all_examreports():
    if 'log' in session:

        data = {}

        query = """
        SELECT 
        e.title AS exam_title, 
        er.mark, 
        er.report,
        s.subject_name,
        st.student_id,
        CONCAT(st.first_name, ' ', st.last_name) AS student_name,  -- Concatenate first_name and last_name
        d.department_name AS department
    FROM exam_report er
    INNER JOIN exam e ON er.exam_id = e.exam_id
    INNER JOIN subject s ON e.subject_id = s.subject_id
    INNER JOIN student st ON er.student_id = st.student_id
    INNER JOIN department d ON st.department_id = d.department_id
    ORDER BY d.department_name, er.mark DESC
    """
        reports = select(query)

        # Group the reports by department
        grouped_reports = {}
        for report in reports:
            department = report['department']
            if department not in grouped_reports:
                grouped_reports[department] = []
            grouped_reports[department].append(report)

        data['grouped_reports'] = grouped_reports
        response = make_response(render_template("view_all_examreports.html", data=data))
    else:
        response = make_response("""
            <script>
                alert('Session Expired');
                window.location.href = '/';
            </script>
        """)
        
    # Set headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
       
        
    return render_template("view_all_examreports.html", data=data)

