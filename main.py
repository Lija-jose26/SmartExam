from flask import *
from public import *
from admin import *
from hod import *
from teacher import *
from student import *
app=Flask(__name__)

app.secret_key='12355'

app.register_blueprint(pub)
app.register_blueprint(adm)
app.register_blueprint(hod)
app.register_blueprint(teacher)
app.register_blueprint(student)

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'hariharan0987pp@gmail.com'
app.config['MAIL_PASSWORD'] = 'rjcbcumvkpqynpep'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

app.run(debug=True,port=5003)