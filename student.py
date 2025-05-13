from flask import *
from database import *

student=Blueprint('student',__name__)



@student.route("/exam_res")
def exam_res():
    if 'log' in session:
        data={}
        id=request.args['id'] 
        z="select * from exam_report where exam_id='%s' and student_id='%s'"%(id,session['student'])
        data['view']=select(z)
        print(data,"////////////")
        return render_template("exam_res.html", data=data)
    else:
        return redirect(url_for('student.student_home'))

@student.route("/exam_result/<exam_id>")
def exam_result(exam_id):
    if 'log' in session:
        score = session.get('exam_score', 0)  # Get stored score
        return render_template("exam_result.html", score=score)
    else:
        return redirect(url_for('student.student_home'))
 
    
from final import *
from queue import Queue
import threading
from datetime import datetime
import time
import cv2
import winsound
from flask import session
import os
import hashlib
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Import the BrowserActivityTracker from brw.py
from brow import BrowserActivityTracker

# Global variables
monitor_thread = None
monitor = None
malpractice_queue = Queue()
browser_tracker = BrowserActivityTracker()  # Initialize the browser tracker

class EnhancedAttentionMonitor(AttentionMonitor):
    def __init__(self):
        super().__init__()
        self.malpractice_detected = False
        self.malpractice_type = None
        
    def process_frame(self, frame):
        frame = cv2.resize(frame, (640, 480))
        self.frame_counter += 1
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector(gray)
        
        # Check head pose
        for face in faces:
            shape = self.predictor(gray, face)
            pitch, yaw = self.head_pose_estimation(shape, frame)
            
            if pitch is not None and yaw is not None:
                if yaw < -20:
                    self.pose_counts['Looking Left'] += 1
                elif yaw > 20:
                    self.pose_counts['Looking Right'] += 1
                elif pitch < -20:
                    self.pose_counts['Looking Down'] += 1
                else:
                    self.pose_counts = {k: max(0, v - 1) for k, v in self.pose_counts.items()}
                
                # Immediately check if pose threshold is crossed
                for pose, count in self.pose_counts.items():
                    if count >= self.pose_threshold:
                        self.trigger_malpractice('pose')
                        return frame
        
        # Check phone
        phone_detected = self.detect_phone(frame)
        self.phone_detections.append(1 if phone_detected else 0)
        if sum(self.phone_detections) >= self.phone_threshold:
            self.trigger_malpractice('phone')
            return frame
        
        # Check earbuds
        if self.frame_counter % 5 == 0:  # Check every 5th frame
            earbud_detected = self.detect_earbuds(frame)
            self.earbud_detections.append(1 if earbud_detected else 0)
            if sum(self.earbud_detections) >= self.earbud_threshold:
                self.trigger_malpractice('earbud')
                return frame
        
        # Update debug info on frame
        if self.debug:
            cv2.putText(frame, 
                        f"Head Pose - Left: {self.pose_counts['Looking Left']} Right: {self.pose_counts['Looking Right']} Down: {self.pose_counts['Looking Down']}", 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            cv2.putText(frame, 
                        f"Phone Detections: {sum(self.phone_detections)}/{self.phone_threshold}", 
                        (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(frame, 
                        f"Earbud Detections: {sum(self.earbud_detections)}/{self.earbud_threshold}", 
                        (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return frame

    def trigger_malpractice(self, alert_type):
        """Immediately trigger malpractice alert and stop monitoring"""
        description = self.get_malpractice_description(alert_type)
        
        # Debug log
        print(f"Malpractice detected: {description}")
        
        # Put malpractice info in queue
        malpractice_info = {
            'type': alert_type,
            'description': description,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        malpractice_queue.put(malpractice_info)
        
        print(f"Added to queue: {malpractice_info}")
        
        # Play alert sound
        winsound.Beep(1000, 500)
        
        # Stop monitoring
        self.stop()
    
    def get_malpractice_description(self, alert_type):
        if alert_type == 'pose':
            suspicious_poses = [pose for pose, count in self.pose_counts.items() if count >= self.pose_threshold]
            return f"Suspicious head movement detected: {', '.join(suspicious_poses)}"
        elif alert_type == 'phone':
            return "Mobile phone usage detected"
        elif alert_type == 'earbud':
            return "Earbuds/headphones detected"
        return "Unknown malpractice type"

def start_monitoring():
    global monitor
    monitor = EnhancedAttentionMonitor()
    monitor.run()
    


@student.route("/attend_exam")
def attend_exam():
    if 'log' in session:
        
        id = request.args.get('id')
        data = {}
        
        # Check if already attended
        bb = "select * from exam_report where student_id='%s' and exam_id='%s'" % (session['student'], id)
        ed = select(bb)
        
        if ed:
            return """<script>alert("You have already attended the exam");window.location='/view_examreport?id=%s'</script>""" % (id)
        
        # Get exam questions
        query = "SELECT * FROM exam_question WHERE exam_id='%s'" % (id)
        data['view'] = select(query)
        
        # Get exam details including time limit
        exam_query = "SELECT * FROM exam WHERE exam_id='%s'" % (id)
        exam_details = select(exam_query)
        
        if not exam_details:
            return """
                <script>
                    alert('Exam details not found.');
                    window.location= '/view_examnotification';
                </script>
            """
            
        data['exam_time'] = exam_details[0]['time'] if exam_details else 1  # Default to 1 minute if not specified
        
        if not data['view']:
            return """
                <script>
                    alert('No questions uploaded for this exam.');
                    window.location= '/view_examnotification';
                </script>
            """
        
        # Start browser activity tracking
        student_id = session['student']
        browser_tracker.start_tracking(student_id, id)
        
        # Clear any previous malpractice detections
        while not malpractice_queue.empty():
            malpractice_queue.get()
        
        # Start monitoring in new thread
        global monitor_thread
        if monitor_thread is None or not monitor_thread.is_alive():
            monitor_thread = threading.Thread(target=start_monitoring)
            monitor_thread.daemon = True
            monitor_thread.start()
        
        response = make_response(render_template("attend_exam.html", data=data, exam_id=id))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    return """<script>alert("Session Expired");window.location='/'</script>"""

@student.route("/record_browser_activity", methods=["POST"])
def record_browser_activity():
    """API endpoint to record browser activity"""
    if 'log' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})
    
    try:
        data = request.json
        student_id = session['student']
        exam_id = data.get('exam_id')
        url = data.get('url')
        title = data.get('title')
        
        browser_tracker.record_activity(student_id, exam_id, url, title)
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error recording browser activity: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@student.route("/check_malpractice")
def check_malpractice():
    """Endpoint for frontend to check if malpractice was detected"""
    if not malpractice_queue.empty():
        malpractice_info = malpractice_queue.get()
        print(f"Sending malpractice info to frontend: {malpractice_info}")
        return jsonify({
            'malpractice_detected': True,
            'details': malpractice_info
        })
    return jsonify({'malpractice_detected': False})

@student.route("/submit_exam/<exam_id>", methods=["POST"])
def submit_exam(exam_id):
    if 'log' not in session:
        return """<script>alert("Session Expired");window.location='/'</script>"""
    
    print("Starting exam submission process...")
    student_id = session['student']
    
    # Generate browser activity report
    browser_report_path = None
    try:
        browser_report_path = browser_tracker.generate_pdf_report(student_id, exam_id)
        print(f"Generated browser activity report: {browser_report_path}")
    except Exception as e:
        print(f"Error generating browser report: {str(e)}")
    
    # Check if this is a timeout submission
    timeout_submission = request.form.get('timeout_submission') == 'true'
    if timeout_submission:
        print("Exam submitted due to timeout")
    
    # Check for malpractice from form data first
    malpractice_detected = request.form.get('malpractice_detected') == 'true'
    malpractice_description = request.form.get('malpractice_description')
    malpractice_timestamp = request.form.get('malpractice_timestamp')
    
    print(f"Form data - Malpractice detected: {malpractice_detected}")
    print(f"Form data - Description: {malpractice_description}")
    print(f"Form data - Timestamp: {malpractice_timestamp}")
    
    if malpractice_detected and malpractice_description:
        print(f"Processing malpractice from form data: {malpractice_description}")
        
        # Insert disqualification report
        disqualification_query = """
            INSERT INTO exam_report 
            (exam_id, student_id, mark, report, malpractice_description, browser_report_path)
            VALUES ('%s', '%s', '%s', '%s', '%s', '%s')
        """ % (
            exam_id,
            student_id,
            '0',  # Score
            'DISQUALIFIED',
            malpractice_description,
            browser_report_path or ''
        )
        insert(disqualification_query)
        print("Inserted malpractice report from form data")
        
        # Stop monitoring
        global monitor, monitor_thread
        if monitor:
            monitor.stop()
        if monitor_thread and monitor_thread.is_alive():
            monitor_thread.join()
        
        return """
            <script>
                alert("Exam terminated due to malpractice: %s");
                window.location='/student_home'
            </script>
        """ % malpractice_description
    
    # If no malpractice from form, check queue as backup
    if not malpractice_queue.empty():
        malpractice_info = malpractice_queue.get()
        print(f"Processing malpractice from queue: {malpractice_info}")
        
        # Handle malpractice from queue
        disqualification_query = """
            INSERT INTO exam_report 
            (exam_id, student_id, mark, report, malpractice_description, browser_report_path)
            VALUES ('%s', '%s', '%s', '%s', '%s', '%s')
        """ % (
            exam_id,
            student_id,
            '0',
            'DISQUALIFIED',
            malpractice_info['description'],
            browser_report_path or ''
        )
        insert(disqualification_query)
        print("Inserted malpractice report from queue")
        
        # Stop monitoring
        if monitor:
            monitor.stop()
        if monitor_thread and monitor_thread.is_alive():
            monitor_thread.join()
        
        return """
            <script>
                alert("Exam terminated due to malpractice: %s");
                window.location='/student_home'
            </script>
        """ % malpractice_info['description']
    
    print("No malpractice detected, processing normal submission")
    
    # Process normal exam submission
    query = "SELECT exam_question_id, correct_answer FROM exam_question WHERE exam_id='%s'" % (exam_id)
    questions = select(query)
    
    total_questions = len(questions)
    correct_count = 0
    answered_count = 0
    
    for q in questions:
        qid = str(q['exam_question_id'])
        correct_ans = q['correct_answer'].strip().upper()
        selected_ans = request.form.get(f'answer_{qid}', '').strip().upper()
        
        # Count both correct answers and total answered questions
        if selected_ans:
            answered_count += 1
            if selected_ans == correct_ans:
                correct_count += 1
    
    # Calculate percentage based on total questions
    percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0
    
    # Add note about timeout if applicable
    submission_note = ""
    if timeout_submission:
        answered_percentage = (answered_count / total_questions) * 100 if total_questions > 0 else 0
        submission_note = f" (Time expired - {answered_count}/{total_questions} questions answered)"
    
    # Determine grade
    if percentage < 45: grade = "F"
    elif percentage < 59: grade = "D"
    elif percentage < 69: grade = "C"
    elif percentage < 79: grade = "B"
    elif percentage < 90: grade = "A"
    else: grade = "A+"
    
    # Append note to grade if timeout occurred
    final_grade = grade + submission_note if submission_note else grade
    
    # Insert exam report with browser report path
    z = """
        INSERT INTO exam_report 
        (exam_id, student_id, mark, report, malpractice_description, browser_report_path)
        VALUES ('%s', '%s', '%s', '%s', NULL, '%s')
    """ % (exam_id, student_id, percentage, final_grade, browser_report_path or '')
    insert(z)
    print("Inserted normal exam report")
    
    # Stop monitoring
    if monitor:
        monitor.stop()
    if monitor_thread and monitor_thread.is_alive():
        monitor_thread.join()
    
    return """<script>alert("Exam submitted successfully!");window.location='/student_home'</script>"""

# @student.route("/attend_exam")
# def attend_exam():
#     if 'log' in session:
        
#         id = request.args.get('id')
#         data = {}
        
#         # Check if already attended
#         bb = "select * from exam_report where student_id='%s' and exam_id='%s'" % (session['student'], id)
#         ed = select(bb)
        
#         if ed:
#             return """<script>alert("You have already attended the exam");window.location='/exam_res?id=%s'</script>""" % (id)
        
#         # Get exam questions
#         query = "SELECT * FROM exam_question WHERE exam_id='%s'" % (id)
#         data['view'] = select(query)
        
#         # Get exam details including time limit
#         exam_query = "SELECT * FROM exam WHERE exam_id='%s'" % (id)
#         exam_details = select(exam_query)
        
#         if not exam_details:
#             return """
#                 <script>
#                     alert('Exam details not found.');
#                     window.location= '/view_examnotification';
#                 </script>
#             """
            
#         data['exam_time'] = exam_details[0]['time'] if exam_details else 1  # Default to 1 minute if not specified
        
#         if not data['view']:
#             return """
#                 <script>
#                     alert('No questions uploaded for this exam.');
#                     window.location= '/view_examnotification';
#                 </script>
#             """
        
#         # Start browser activity tracking
#         student_id = session['student']
#         browser_tracker.start_tracking(student_id, id)
        
#         # Clear any previous malpractice detections
#         while not malpractice_queue.empty():
#             malpractice_queue.get()
        
#         # Start monitoring in new thread
#         global monitor_thread
#         if monitor_thread is None or not monitor_thread.is_alive():
#             monitor_thread = threading.Thread(target=start_monitoring)
#             monitor_thread.daemon = True
#             monitor_thread.start()
        
#         response = make_response(render_template("attend_exam.html", data=data, exam_id=id))
#         response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
#         response.headers['Pragma'] = 'no-cache'
#         response.headers['Expires'] = '0'
#         return response
    
#     return """<script>alert("Session Expired");window.location='/'</script>"""

# @student.route("/record_browser_activity", methods=["POST"])
# def record_browser_activity():
#     """API endpoint to record browser activity"""
#     if 'log' not in session:
#         return jsonify({'status': 'error', 'message': 'Not logged in'})
    
#     try:
#         data = request.json
#         student_id = session['student']
#         exam_id = data.get('exam_id')
#         url = data.get('url')
#         title = data.get('title')
        
#         browser_tracker.record_activity(student_id, exam_id, url, title)
#         return jsonify({'status': 'success'})
#     except Exception as e:
#         print(f"Error recording browser activity: {str(e)}")
#         return jsonify({'status': 'error', 'message': str(e)})

# @student.route("/check_malpractice")
# def check_malpractice():
#     """Endpoint for frontend to check if malpractice was detected"""
#     if not malpractice_queue.empty():
#         malpractice_info = malpractice_queue.get()
#         print(f"Sending malpractice info to frontend: {malpractice_info}")
#         return jsonify({
#             'malpractice_detected': True,
#             'details': malpractice_info
#         })
#     return jsonify({'malpractice_detected': False})

# @student.route("/submit_exam/<exam_id>", methods=["POST"])
# def submit_exam(exam_id):
#     if 'log' not in session:
#         return """<script>alert("Session Expired");window.location='/'</script>"""
    
#     print("Starting exam submission process...")
#     student_id = session['student']
    
#     # Generate browser activity report
#     browser_report_path = None
#     try:
#         browser_report_path = browser_tracker.generate_pdf_report(student_id, exam_id)
#         print(f"Generated browser activity report: {browser_report_path}")
#     except Exception as e:
#         print(f"Error generating browser report: {str(e)}")
    
#     # Check if this is a timeout submission
#     timeout_submission = request.form.get('timeout_submission') == 'true'
#     if timeout_submission:
#         print("Exam submitted due to timeout")
    
#     # Check for malpractice from form data first
#     malpractice_detected = request.form.get('malpractice_detected') == 'true'
#     malpractice_description = request.form.get('malpractice_description')
#     malpractice_timestamp = request.form.get('malpractice_timestamp')
    
#     print(f"Form data - Malpractice detected: {malpractice_detected}")
#     print(f"Form data - Description: {malpractice_description}")
#     print(f"Form data - Timestamp: {malpractice_timestamp}")
    
#     if malpractice_detected and malpractice_description:
#         print(f"Processing malpractice from form data: {malpractice_description}")
        
#         # Insert disqualification report
#         disqualification_query = """
#             INSERT INTO exam_report 
#             (exam_id, student_id, mark, report, malpractice_description, browser_report_path)
#             VALUES ('%s', '%s', '%s', '%s', '%s', '%s')
#         """ % (
#             exam_id,
#             student_id,
#             '0',  # Score
#             'DISQUALIFIED',
#             malpractice_description,
#             browser_report_path or ''
#         )
#         insert(disqualification_query)
#         print("Inserted malpractice report from form data")
        
#         # Stop monitoring
#         global monitor, monitor_thread
#         if monitor:
#             monitor.stop()
#         if monitor_thread and monitor_thread.is_alive():
#             monitor_thread.join()
        
#         return """
#             <script>
#                 alert("Exam terminated due to malpractice: %s");
#                 window.location='/student_home'
#             </script>
#         """ % malpractice_description
    
#     # If no malpractice from form, check queue as backup
#     if not malpractice_queue.empty():
#         malpractice_info = malpractice_queue.get()
#         print(f"Processing malpractice from queue: {malpractice_info}")
        
#         # Handle malpractice from queue
#         disqualification_query = """
#             INSERT INTO exam_report 
#             (exam_id, student_id, mark, report, malpractice_description, browser_report_path)
#             VALUES ('%s', '%s', '%s', '%s', '%s', '%s')
#         """ % (
#             exam_id,
#             student_id,
#             '0',
#             'DISQUALIFIED',
#             malpractice_info['description'],
#             browser_report_path or ''
#         )
#         insert(disqualification_query)
#         print("Inserted malpractice report from queue")
        
#         # Stop monitoring
#         if monitor:
#             monitor.stop()
#         if monitor_thread and monitor_thread.is_alive():
#             monitor_thread.join()
        
#         return """
#             <script>
#                 alert("Exam terminated due to malpractice: %s");
#                 window.location='/student_home'
#             </script>
#         """ % malpractice_info['description']
    
#     print("No malpractice detected, processing normal submission")
    
#     # Process normal exam submission
#     query = "SELECT exam_question_id, correct_answer FROM exam_question WHERE exam_id='%s'" % (exam_id)
#     questions = select(query)
    
#     total_questions = len(questions)
#     correct_count = 0
#     answered_count = 0
    
#     for q in questions:
#         qid = str(q['exam_question_id'])
#         correct_ans = q['correct_answer'].strip().upper()
#         selected_ans = request.form.get(f'answer_{qid}', '').strip().upper()
        
#         # Count both correct answers and total answered questions
#         if selected_ans:
#             answered_count += 1
#             if selected_ans == correct_ans:
#                 correct_count += 1
    
#     # Calculate percentage based on total questions
#     percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0
    
#     # Add note about timeout if applicable
#     submission_note = ""
#     if timeout_submission:
#         answered_percentage = (answered_count / total_questions) * 100 if total_questions > 0 else 0
#         submission_note = f" (Time expired - {answered_count}/{total_questions} questions answered)"
    
#     # Determine grade
#     if percentage < 45: grade = "F"
#     elif percentage < 59: grade = "D"
#     elif percentage < 69: grade = "C"
#     elif percentage < 79: grade = "B"
#     elif percentage < 90: grade = "A"
#     else: grade = "A+"
    
#     # Append note to grade if timeout occurred
#     final_grade = grade + submission_note if submission_note else grade
    
#     # Insert exam report with browser report path
#     z = """
#         INSERT INTO exam_report 
#         (exam_id, student_id, mark, report, malpractice_description, browser_report_path)
#         VALUES ('%s', '%s', '%s', '%s', NULL, '%s')
#     """ % (exam_id, student_id, percentage, final_grade, browser_report_path or '')
#     insert(z)
#     print("Inserted normal exam report")
    
#     # Stop monitoring
#     if monitor:
#         monitor.stop()
#     if monitor_thread and monitor_thread.is_alive():
#         monitor_thread.join()
    
#     return """<script>alert("Exam submitted successfully!");window.location='/student_home'</script>"""



@student.route("/student_home")
def student_home():
    if 'log' in session:
        response = make_response(render_template("student.html"))
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
    return render_template("student.html")

# View Courses
@student.route("/viewcourses")
def viewcourses():
    if 'log' in session:
        data={}
        query = """
            SELECT c.course_name, d.department_id, d.department_name
            FROM Course c
            INNER JOIN Department d ON c.department_id = d.department_id
        """
        data['view']=select(query)
        print("Fetched Data:", data['view']) 
        response = make_response(render_template("viewcourses.html", data=data))
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
        
    return render_template("viewcourses.html", data=data)

@student.route("/view_substudent")
def view_substudent():
    if 'log' in session:
        student_id = session.get('student')  # Get student ID from session
        #faculty_id = session['faculty']  
        data = {}
        dept_query = f"SELECT department_id FROM student WHERE student_id = '{student_id}'"
        student_result = select(dept_query) 
        data = {}

        # Fetch course_id and semester_id of the logged-in student
        # student_query = "SELECT department_id, semester_id FROM student WHERE student_id = '{student_id}'"
        # student_result = select(student_query)  

        if student_result:
            department_id = student_result[0]['department_id']
           

            # Query to fetch assigned subjects along with teacher details for the student's course and semester
            query = f"""
                SELECT 
                    f.first_name, f.last_name,
                    s.subject_name, 
                    sem.semester_name, 
                    c.course_name, 
                    d.department_name
                FROM faculty f
                INNER JOIN subject s ON f.faculty_id = s.teacher_id
                INNER JOIN semester sem ON s.semester_id = sem.semester_id
                INNER JOIN course c ON sem.course_id = c.course_id
                INNER JOIN department d ON c.department_id = d.department_id
                WHERE d.department_id = '{department_id}' 
            """  
            data['view'] = select(query)  
        else:
            data['view'] = []  # Assign an empty list if no course or semester found
        
        response = make_response(render_template("view_substudent.html", data=data))
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

  
    return render_template("view_substudent.html", data=data)



@student.route("/view_department")
def view_department():
    if 'log' in session:
        data = {}

        query = """
            SELECT 
                department_id, 
                department_name 
            FROM department
            ORDER BY department_name
        """
        data['departments'] = select(query)  # Execute the query
        response = make_response(render_template("view_department.html", data=data))
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
  
    return render_template("view_department.html", data=data)

@student.route("/view_hod/<int:department_id>")
def view_hod(department_id):
    if 'log' in session:
        data = {}

        query = """
            SELECT 
                faculty.first_name, 
                faculty.last_name, 
                faculty.phone, 
                faculty.email 
            FROM faculty
            WHERE department_id = %s """ % department_id
        data['hod'] = select(query)  # Execute the query
        response = make_response(render_template("view_hod.html", data=data))
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
  
    return render_template("view_hod.html", data=data)



@student.route("/view_examnotification")
def view_examnotification():
    if 'log' in session:
        data = {}
        
        # Ensure student is logged in by checking if the session has the 'student' key
        if "student" not in session:
            return redirect(url_for('pub.login'))  # Redirect to login if not logged in

        # Get the logged-in student's ID
        student_id = session['student']
        print(f"Logged-in Student ID: {student_id}")  # Debugging step

        # Fetch the department_id of the logged-in student from the `student` table
        dept_query = f"""
            SELECT department_id 
            FROM student 
            WHERE student_id = '{student_id}'
        """
        student_department = select(dept_query)[0]['department_id']
        print(f"Student Department ID: {student_department}")  # Debugging step

        # Fetch exam notifications only for the student's department
        query = f"""
        SELECT 
            exam.exam_id, 
            exam.exam_date, 
            subject.subject_name, 
            exam.title, 
            exam.notification_date ,
            exam.time 
            
        FROM exam 
        JOIN subject ON exam.subject_id = subject.subject_id
        JOIN faculty ON subject.teacher_id = faculty.faculty_id
        WHERE faculty.department_id = '{student_department}'
        ORDER BY exam.exam_date ASC
    """

        
        # Get the exam notifications for the student's department
        data['view'] = select(query)
        print(f"Exam Notifications Data: {data['view']}")  # Debugging step
        
        # Check if data['view'] has results
        if not data['view']:
            data['view'] = []  # Handle case where no exam notifications are found
        response = make_response(render_template("view_examnotification.html", data=data))
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
  








@student.route("/showprofile", methods=["GET", "POST"])
def showprofile():
    if 'log' in session:
        data = {}

        # Ensure student is logged in by checking if session has the 'student' key
        if "student" in session:  # Check if the student is logged in
            student_id = session["student"]
            print(f"Student ID from session: {student_id}")  # Debugging step

            # Modify query to fetch the profile using student_id from session
            query = """
                SELECT * 
                FROM `student` 
                INNER JOIN `department` USING(department_id) 
                WHERE student_id = '%s'
            """ % student_id  
            
            # Fetch the profile details from the database
            data["view"] = select(query)
            print(f"Query result: {data['view']}")  
            
            if not data["view"]:
                data["view"] = []  
        else:
            print("No student logged in. Redirecting to login.")  # Debugging step
            return redirect(url_for("pub.login"))  # Redirect to login page if session is not set
        response = make_response(render_template("showprofile.html", data=data))
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
  
        
    return render_template("showprofile.html", data=data)

@student.route("/view_examreport", methods=['GET'])
def view_examreport():
    if 'log' in session:
        data = {}

        student_id = session.get('student')  
        print("Student ID:", student_id)  # Debugging step

        query = f"""
            SELECT 
                e.title AS exam_title, 
                s.subject_name,  -- Added subject name
                er.mark, 
                er.report ,
                er.malpractice_description
            FROM exam_report er
            INNER JOIN exam e ON er.exam_id = e.exam_id
            INNER JOIN subject s ON e.subject_id = s.subject_id  -- Join with subject table
            WHERE er.student_id = '{student_id}'
            ORDER BY er.report_id DESC
        """
        
        data['reports'] = select(query)  
        print("Session Data:", session)
        print("Logged-in Student ID:", student_id)
        print("Reports Data:", data['reports']) 
        response = make_response(render_template("view_examreport.html", data=data))
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
  
    return render_template("view_examreport.html", data=data)
