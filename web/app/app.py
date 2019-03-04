import sys, os, io
import requests
import datetime

from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from flask_uploads import UploadSet, IMAGES, configure_uploads
#from data import Articles
#from flask_mysqldb import MySQL
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

from PIL import Image
import time
import hashlib

app = Flask( __name__ )
#sys.path.append('/usr/share/nginx/html')
app.secret_key = app_settings['secret_key']
#os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.abspath('app/spotdog-90809b2458ef.json')
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

def fix_orientation(file_like_object):
    img = Image.open(file_like_object)

    if hasattr(img, '_getexif'):
        exifdata = img._getexif()
    try:
        orientation = exifdata.get(274)
    except:
        # There was no EXIF Orientation Data
        orientation = 1
    else:
        orientation = 1

    if orientation is 1:    # Horizontal (normal)
        pass
    elif orientation is 2:  # Mirrored horizontal
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    elif orientation is 3:  # Rotated 180
        img = img.rotate(180)
    elif orientation is 4:  # Mirrored vertical
        img = img.rotate(180).transpose(Image.FLIP_LEFT_RIGHT)
    elif orientation is 5:  # Mirrored horizontal then rotated 90 CCW
        img = img.rotate(-90).transpose(Image.FLIP_LEFT_RIGHT)
    elif orientation is 6:  # Rotated 90 CCW
        img = img.rotate(-90)
    elif orientation is 7:  # Mirrored horizontal then rotated 90 CW
        img = img.rotate(90).transpose(Image.FLIP_LEFT_RIGHT)
    elif orientation is 8:  # Rotated 90 CW
        img = img.rotate(90)


    data = BytesIO()
    img.save(data)
    return data

# Have imported google fnctions, now need to actuall call the upload function in the add_picture route and then get then pass the url to the prediction rest api

def upload_image_file(file):
    """
    Upload the user-uploaded file to Google Cloud Storage and retrieve its
    publicly-accessible URL.
    """
    if not file:
        return None



    public_url, safe_filename = storage.upload_file(
#        file.read(),
        fix_orientation(file),
        file.filename,
        file.content_type
    )

    return public_url, safe_filename

# Index
@app.route('/')
def index():
    if 'logged_in' in session:
        # Get list of pictures from cloud storage for this user, to display on carousel
        pictures = PICTURES.where(u'user', u'==', session['name']).limit(50).get()
        # Pictures comes back as a generator of 'documents'. List turns generator into list, to_dict method on documents gets the values out
        pictures = [pic.to_dict() for pic in list(pictures)]
    else:
        pictures = []
    return render_template('home.html', pictures=pictures)

# About
@app.route('/about')
def about():
    return render_template('about.html')

# Pictures
@app.route('/pictures')
def pictures():
    # Get pictures
    pictures = PICTURES.where(u'user', u'==', session['name']).limit(50).get()
    # The above query returns a generator, so need to get first element
    pictures = list(pictures)
    if pictures[0].exists:
        pictures = [pic.to_dict() for pic in pictures]
        #
        return render_template('pictures.html', pictures=pictures)
    else:
        msg = 'No pictures found'
        return render_template('pictures.html', msg=msg)

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
    if pictures:
        pictures = [pic.to_dict() for pic in pictures]
        #
        return render_template('dashboard.html', pictures=pictures)
    else:
        msg = 'No pictures found'
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


            # Create new document in the Firebase collection
            pictureref = db.collection(u'pictures').document()
            pic_id = pictureref.id
            #create record to store in Firebase
            record = {
                u'id' : pic_id,
                u'title' : title,
                u'url' : image_url,
                u'filename' : filename,
                u'user' : session['name'],
                u'breed' : breeds,
                u'date' : datetime.datetime.now()
            }


            # Set document record
            pictureref.set(record)

        flash('Upload completed','success')

        return redirect(url_for('picture', id=pic_id))
    print(form.errors)
    return render_template('add_picture.html', form=form)

# Edit picture
@app.route ('/edit_picture/<string:id>', methods=['GET','POST'])
@is_logged_in
def edit_picture(id):
    # Get pictures
    picture = PICTURES.where(u'id', u'==', id).get().to_dict()
    #Get form
    form = PictureForm(request.form)

    #Populate article form fields
    form.title.data = picture['title']

    if request.method == 'POST' and form.validate():
        title = form.title.data

        ## Need code here to update google cloud data!!!

        flash('Picture updated','success')

        return redirect(url_for('dashboard'))

    return render_template('edit_picture.html', form=form)

# Delete picture
@app.route('/delete_picture/<string:id>', methods=["POST"])
@is_logged_in
def delete_picture(id):

    #Get the filename from filestore
    picture = PICTURES.document(id).get().to_dict()

    # Delete the picture itself from Cloud Storage
    storage.delete_file(picture['filename'])

    # Delete the record from firestore
    PICTURES.document(id).delete()


    flash('Picture deleted', 'success')

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.secret_key = '45gdh56562wgyy724654usfbgasdeg'  #os.environ.get("SECRET_KEY", default=None)
#    app.run(host="0.0.0.0", debug=True)
    app.run(debug=True)
