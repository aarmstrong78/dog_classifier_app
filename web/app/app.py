import sys, os
import requests
import datetime

from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from flask_uploads import UploadSet, IMAGES, configure_uploads
#from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, FileField, MultipleFileField, validators
#from wtforms import StringField, TextAreaField, PasswordField, FileField, validators
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired
from werkzeug.utils import secure_filename

import firebase_admin
from firebase_admin import firestore

from passlib.hash import sha256_crypt
from functools import wraps

from app.settings import *  #loads in the config settings variable
import app.storage as storage

import cv2
import time
import hashlib

app = Flask( __name__ )
#sys.path.append('/usr/share/nginx/html')
app.secret_key = app_settings['secret_key']
#WTF_CSRF_SECRET_KEY = 'dfgdgdss54645445y6yh5ebns467'
# Config MySQL

app.config['MYSQL_HOST'] = app_settings['MYSQL_HOST']
app.config['MYSQL_PORT'] = app_settings['MYSQL_PORT']
app.config['MYSQL_USER'] = app_settings['MYSQL_USER']
app.config['MYSQL_PASSWORD'] = app_settings['MYSQL_PASSWORD']
app.config['MYSQL_DB'] = app_settings['MYSQL_DB']
app.config['MYSQL_CURSORCLASS'] = app_settings['MYSQL_CURSORCLASS']

# Init MYSQL
#mysql = MySQL(app)
print(os.path.abspath('spotdog-90809b2458ef.json'))
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath('app/spotdog-90809b2458ef.json')
firebase_admin.initialize_app()

db = firestore.client()
USERS = firestore.client().collection('users')
PICTURES = firestore.client().collection('pictures')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Configure the image uploading via Flask-Uploads
app.config['UPLOADS_DEFAULT_DEST'] = app_settings['IMAGE_FILES_LOCATION']
photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)

######

# Have imported google fnctions, now need to actuall call the upload function in the add_picture route and then get then pass the url to the prediction rest api

def upload_image_file(file):
    """
    Upload the user-uploaded file to Google Cloud Storage and retrieve its
    publicly-accessible URL.
    """
    if not file:
        return None

    public_url, safe_filename = storage.upload_file(
        file.read(),
        file.filename,
        file.content_type
    )

    return public_url, safe_filename


######

# Index
@app.route('/')
def index():
    return render_template('home.html')

# About
@app.route('/about')
def about():
    return render_template('about.html')

# Pictures
@app.route('/pictures')
def pictures():
    # CREATE cursor
    cur = mysql.connection.cursor()

    # Get pictures
    result = cur.execute("SELECT * FROM pictures")

    pictures = cur.fetchall()

    if result > 0:
        return render_template('pictures.html', pictures=pictures)
    else:
        msg = 'No pictures found'
        return render_template('pictures.html', msg=msg)
    # Close connection
    cur.close()

#Single Picture
@app.route('/picture/<string:id>')
def picture(id):
    # Get picture
    doc_ref = PICTURES.document(id)

    try:
        picture = doc_ref.get().to_dict()
    except google.cloud.exceptions.NotFound:
        app.logger.error(u'No such document!')

    return render_template('picture.html', url=picture['url'], picture=picture)

#Register form class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1,max=50)])
    username = StringField('Username', [validators.Length(min=4,max=25)])
    email = StringField('Email',[validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')

# Register
@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        #create record to store in Firebase
        record = {
            u'name' : name,
            u'email' : email,
            u'username' : username,
            u'password' : password,
            u'date' : datetime.datetime.now()
        }

        # Create new document in the Firebase collection
        user_ref = USERS.document()

        # Set document record
        user_ref.set(record)


        flash('You are now registered and can log in','success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)

#User login
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        # Get form fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Get user by Username
#        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])
        users = USERS.where(u'username', u'==', username).limit(1).get()
        # The above query returns a generator, so need to get first element
        user = list(users)[0]
        if user.exists:
            user = user.to_dict()
            password = user['password']
            name = user['name']
            # compare passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username
                session['name'] = name

                flash('You are now logged in','success')
                app.logger.info('Password matched')
                return redirect(url_for('dashboard'))
            else:
                app.logger.info('Password not matched')
                error = 'Invalid login'
                return render_template('login.html', error = error)

        else:
            app.logger.info('No user')
            error = 'Username not found'
            return render_template('login.html', error = error)

    return render_template('login.html')

# Check if user logged if

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorised. Please login', 'danger')
            return redirect(url_for('login'))

    return wrap


# User logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out','success')
    return redirect(url_for('login'))

# Dashboard
@app.route ('/dashboard')
@is_logged_in
def dashboard():
    # Get pictures
    pictures = PICTURES.where(u'user', u'==', session['name']).limit(50).get()
    # The above query returns a generator, so need to get first element
    pictures = list(pictures)
    if pictures[0].exists:
        ## Need to use to_dict() method to get the actual data
        #
        return render_template('dashboard.html', pictures=pictures)
    else:
        msg = 'No articles found'
        return render_template('dashboard.html', msg=msg)


#picture form class
class PictureForm(FlaskForm):
    photo = FileField('Photo', [FileAllowed(photos, u'Image Only!'), FileRequired()])
    title = StringField('Title', [validators.Length(min=1,max=200)])

# Add Photo
@app.route ('/add_picture', methods=['GET','POST'])
@is_logged_in
def add_picture():
    form = PictureForm()
    if request.method == 'POST' and 'photo' in request.files and form.validate():
        print(form.errors)
        for image in request.files.getlist('photo'):
            # Upload image and return url and filename
            image_url, filename = upload_image_file(image)

            title = form.title.data

            # Try to identify dog breed using api
#            api_url = 'http://api:8001/dog_classifier_api/predict'
            api_url = 'http://spotdog.appspot.com/predict'

            response = requests.post(url=api_url, json={'image_url':image_url}).json()#,headers={'Content-Type': 'application/octet-stream'})

            breeds = 'This dog is either a {0}, {1}, or {2}.'.format(response['dog'][0],response['dog'][1],response['dog'][2])
            flash(breeds,'success') #flash the response text


            #create record to store in Firebase
            record = {
                u'title' : title,
                u'url' : image_url,
                u'filename' : filename,
                u'user' : session['name'],
                u'breed' : breeds,
                u'date' : datetime.datetime.now()
            }

            # Create new document in the Firebase collection
            pictureref = db.collection(u'pictures').document()

            # Set document record
            pictureref.set(record)

        flash('Upload completed','success')

        return redirect(url_for('picture', id=pictureref.id))
    print(form.errors)
    return render_template('add_picture.html', form=form)

# Edit picture
@app.route ('/edit_picture/<string:id>', methods=['GET','POST'])
@is_logged_in
def edit_picture(id):
    #create cursor
    cur = mysql.connection.cursor()

    #Get article by id
    result = cur.execute("SELECT * FROM pictures WHERE id = %s",[id])

    picture = cur.fetchone()

    #Get form
    form = PictureForm(request.form)

    #Populate article form fields
    form.title.data = picture['title']
    form.body.data = picture['body']

    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        #create cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("UPDATE pictures SET title=%s, body=%s WHERE id = %s",(request.form['title'], request.form['body'], id))

        #Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Picture updated','success')

        return redirect(url_for('dashboard'))

    return render_template('edit_picture.html', form=form)

# Delete picture
@app.route('/delete_picture/<string:id>', methods=["POST"])
@is_logged_in
def delete_picture(id):
    #os.remove(os.path.join(app.config['UPLOAD_FOLDER'], img_name))

    # Create cursor
    cur = mysql.connection.cursor()

    # Need to get the filename to delete it off the server
    result = cur.execute("SELECT * FROM pictures WHERE id = %s",[id])
    picture = cur.fetchone()

    path = photos.path(picture['filename'])
    print(path)
    os.remove(path)
#os.path.join
    #Execute
    cur.execute("DELETE FROM pictures where id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    #close connection
    cur.close()

    flash('Picture deleted', 'success')

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.secret_key = '45gdh56562wgyy724654usfbgasdeg'  #os.environ.get("SECRET_KEY", default=None)
#    app.run(host="0.0.0.0", debug=True)
    app.run(debug=True)
