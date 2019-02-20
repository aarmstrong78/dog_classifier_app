import sys, os
import requests

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
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath("../../Spotdog-8e7720673e09.json")
firebase_admin.initialize_app()
USERS = firestore.client().collection('users')
PICTURES = firestore.client().collection('pictures')

# Configure file upload
#app.config['UPLOAD_FOLDER'] = app_settings['IMAGE_FILES_LOCATION']
#ALLOWED_EXTENSIONS = set(['jpg', 'jpeg', 'gif'])
#app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16Mb maximum

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Configure the image uploading via Flask-Uploads
app.config['UPLOADS_DEFAULT_DEST'] = app_settings['IMAGE_FILES_LOCATION']
photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)



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
    # CREATE cursor
    cur = mysql.connection.cursor()

    # Get picture
    result = cur.execute("SELECT * FROM pictures WHERE id = %s", [id])

    picture = cur.fetchone()
    if picture is None:
        abort(404)

    url = photos.url(picture['filename'])
    cur.close()

    return render_template('picture.html', url=url, picture=picture)

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

        #create DictCursor
        cur = mysql.connection.cursor()

        #execute query
        cur.execute('INSERT INTO users(name, email, username, password) VALUES(%s,%s,%s,%s)',(name, email, username, password))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

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

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by Username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get first matched user record
            data = cur.fetchone()
            password = data['password']
            name = data['name']
            # Close connection now that we have user data
            cur.close
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
    # CREATE cursor
    #cur = mysql.connection.cursor()

    # Get pictures
    #result = cur.execute("SELECT * FROM pictures WHERE author = %s",[session['name']])

    #pictures = cur.fetchall()

    pictures = PICTURES.where(u'user', u'==', session['name'])

    if result > 0:
        return render_template('dashboard.html', pictures=pictures)
    else:
        msg = 'No articles found'
        return render_template('dashboard.html', msg=msg)
    # Close connection
    cur.close()


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
            name = hashlib.md5(('admin' + str(time.time())).encode('utf-8')).hexdigest()[:15]

            filename = photos.save(image, name=name + '.')
            title = form.title.data

            # Try to identify dog breed
            path = photos.path(filename)
#            data = open(path, 'rb').read()
            files = {'file' : open(path, 'rb')}
            url = 'http://api:8001/dog_classifier_api/predict'
#            res = requests.post(url='http://nginx/dog_classifier_api/predict',data=data,headers={'Content-Type': 'application/octet-stream'})
            response = requests.post(url=url, files=files).json()#,headers={'Content-Type': 'application/octet-stream'})
            breeds = 'This dog is either a {0}, {1}, or {2}.'.format(response['dog'][0],response['dog'][1],response['dog'][2])
            flash(breeds,'success') #flash the response text


            #create cursor
            #cur = mysql.connection.cursor()

            # Execute
            #cur.execute("INSERT INTO pictures(title, filename, author) VALUES(%s,%s,%s)",(title, filename, session['name']))
            #pictureid = cur.lastrowid
            record = {
                'title' : title;
                'filename' : filename;
                'user' : session['name'];
                'breed' : breeds
                    'id' ?????? Autogenerate??
            }
            PICTURES.set(record)
            #for rank, breed in enumerate(response['dog']):
            #    cur.execute("INSERT INTO predictions(author, pictureid, breed, rank) VALUES(%s,%s,%s,%s)",(session['name'], pictureid, breed, rank))
            #cur.execute("INSERT INTO pictures(filename, author) VALUES(%s,%s)",(filename, session['name']))

            #Commit to DB
            #mysql.connection.commit()

            #Close connection
            #cur.close()

        flash('Upload completed','success')

        return redirect(url_for('picture', id=pictureid))
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
