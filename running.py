# import psutil
# from datetime import datetime

# # Get a list of all processes currently running
# for proc in psutil.process_iter(['pid', 'name', 'status', 'create_time']):
#     try:
#         # Fetch process details
#         pid = proc.info['pid']
#         name = proc.info['name']
#         status = proc.info['status']
#         start_time = proc.info['create_time']

#         # Convert start time from timestamp to human-readable format
#         start_time = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")

#         print(f"PID: {pid}, Name: {name}, Status: {status}, Start Time: {start_time}")
#     except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
#         pass



import psutil
from datetime import datetime
from fpdf import FPDF
from flask import session

def running():
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pdf_filename = f"running_applications_{current_time}.pdf"

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Set title
    pdf.set_font("Arial", size=16, style='B')
    pdf.cell(200, 10, txt="Running Applications - PID, Name, Status, and Start Time", ln=True, align='C')

    pdf.ln(10)

    # If student data exists, display student information
    if 'student' in session:
        student_info = f"Student ID: {session['student']}\n"
        student_info += f"Student Name: {session.get('student_name', 'N/A')}\n"  # Get student name
        student_info += f"Login Time: {session['login_time']}\n"
        if 'logout_time' in session:
            student_info += f"Logout Time: {session['logout_time']}\n"
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, student_info)
        pdf.ln(10)  # Add some space after student info

    # Set header for the table
    pdf.set_font("Arial", size=12, style='B')
    pdf.cell(40, 10, "PID", border=1, align='C')
    pdf.cell(60, 10, "Name", border=1, align='C')
    pdf.cell(40, 10, "Status", border=1, align='C')
    pdf.cell(50, 10, "Start Time", border=1, align='C')
    pdf.ln()

    # Set regular font for data rows
    pdf.set_font("Arial", size=12)

    # Iterate over processes and add rows to the table
    for proc in psutil.process_iter(['pid', 'name', 'status', 'create_time']):
        try:
            pid = proc.info['pid']
            name = proc.info['name']
            status = proc.info['status']
            start_time = proc.info['create_time']

            # Convert start time to human-readable format
            start_time = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")

            # Add data to PDF
            pdf.cell(40, 10, str(pid), border=1, align='C')
            pdf.cell(60, 10, name, border=1, align='C')
            pdf.cell(40, 10, status, border=1, align='C')
            pdf.cell(50, 10, start_time, border=1, align='C')
            pdf.ln()

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Save the PDF to a file with the current date and time in the filename
    pdf.output(pdf_filename)

    print(f"PDF saved as '{pdf_filename}'")
