from flask import *
from database import *

hod=Blueprint('hod',__name__)


@hod.route("/hod_home")
def hod_home():
    return render_template("hod.html")

# @hod.route("/viewteacher", methods=["GET", "POST"])
# def viewteacher():
#     data={}
#     a="select * from faculty where faculty_type='teacher'"
#     res=select(a)
#     if res:
#         data['view']=res
#     return render_template("viewteacher.html",data=data)

@hod.route("/manage_teacher",methods=['post','get'])
def manage_teacher():
    data={}
    a="select * from faculty where faculty_type='teacher'"
    data['view']=select(a)
    
    if 'action' in request.args:
        act=request.args['action']
        fid=request.args['id']
        
        if act == 'delete':
            qry1 = "delete FROM faculty WHERE faculty_id='%s'" % (fid)
            delete(qry1)
            return '''<script>alert("Teacher deleted successfully"); window.location="/manage_teacher";</script>'''
        
        if act == 'update':
            qry="select * from faculty where faculty_id='%s'"%(fid)
            res=select(qry)
            data['up']=res
            
            if 'submit' in request.form:
                firstname=request.form["fname"]
                lastname=request.form["lname"]
                phone=request.form["phone"]
                email=request.form["email"]
                age=request.form["age"]
                qualification=request.form["qualification"]
                place=request.form["place"]
                
                up_qry="update faculty set first_name='%s',last_name='%s',phone='%s',email='%s',age='%s',qualification='%s',place='%s' where faculty_id='%s'"%(firstname,lastname,phone,email,age,qualification,place,fid)
                update(up_qry)
                return '''<script>alert("values updated");window.location="/manage_teacher"</script>'''
    return render_template("viewteacher.html",data=data)


@hod.route("/assign_subject", methods=["GET", "POST"])
def assign_subject():
    data = {}

    # Get logged-in HoD's department ID from session
    hod_department_id = session.get('dept')

    if not hod_department_id:
        return "Unauthorized Access", 403

    # Fetch teachers for the logged-in HoD's department
    query_teachers = """
    SELECT faculty_id, first_name, last_name
    FROM faculty
    WHERE department_id = %s AND faculty_type = 'Teacher'
    """ % (hod_department_id)
    data['teachers'] = select(query_teachers)  # No need for the second argument

    # Fetch subjects for the logged-in HoD's department
    query_subjects = """
    SELECT 
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
    LEFT JOIN 
        faculty f ON s.teacher_id = f.faculty_id
    WHERE 
        c.department_id = %s
    """ % (hod_department_id)
    data['subjects'] = select(query_subjects) #Store subjects in the data dictionary

    # Handle form submission (assign subject to a  teacher)
    if "submit" in request.form:
        subject_id = request.form['subject']
        teacher_id = request.form['teacher']

        # Update the subject with the assigned teacher
        update_query = """
        UPDATE subject
        SET teacher_id = %s
        WHERE subject_id = %s
        """ % (teacher_id, subject_id)  # String formatting (no parametrization)
        
        # Execute the query with string formatting
        insert(update_query)
        return redirect("/assign_subject")

    return render_template("assign_subject.html", data=data)  # Ensure data includes both teachers and subjects

if __name__ == "__main__":
    app.run(debug=True)



#View Students
# @hod.route("/viewstudent", methods=["GET", "POST"])
# def viewstudent():
#     data={}
#     a="SELECT * FROM `student` INNER JOIN `department` USING(department_id) WHERE teacher_id='%s'"%(session['faculty'])
#     data['view']=select(a)
#     return render_template("viewstudent.html",data=data)




# @hod.route("/manage_exam", methods=['POST', 'GET'])
# def manage_exam():
#     data = {}
#     # Fetch all subjects to populate the dropdown
#     qry = "SELECT subject_id, subject_name FROM subject"
#     res = select(qry)
#     if res:
#         data['view'] = res

#     data1 = {}
#     # Fetch all exams with corresponding subject names
#     qry2 = """
#         SELECT e.exam_date, e.notification_date, e.title, s.subject_name 
#         FROM exam e
#         INNER JOIN subject s USING(subject_id)
#     """
#     res2 = select(qry2)
#     if res2:
#         data1['viewd'] = res2

#     # Handle form submission
#     if "submit" in request.form:
#         exam_date = request.form["exam_date"]
#         subject_id = request.form["subject_id"]
#         title = request.form["title"]
#        # notification_date = request.form["notification_date"]
        
        
        
       

#         # Insert exam details into the exam table
#         query_insert="insert into  exam values(null,'%s', '%s', '%s', curdate())" %(exam_date,subject_id, title) 
#         res=insert(query_insert)
#         print(res)
        
        

#         return '''<script>alert("Exam added successfully."); window.location="/manage_exam";</script>'''

#     return render_template("manage_exam.html", data=data, data1=data1)



# @hod.route("/examnotification",methods=['post','get'])
# def examnotification():
#     if "submit" in request.form:
#         hod=request.form["hod"]
#         print(hod)
#         a="insert into exam_notification values(null,'%s','%s',)"% ()
