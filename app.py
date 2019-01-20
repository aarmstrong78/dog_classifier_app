from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
#from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from settings import *  #loads in the config settings variable

app = Flask( __name__ )

app_settings
# Config MySQL  #No longer required, loaded from settings.py
#app.config.from_envvar('FLASKWEBAPP_SETTINGS')
app.config['MYSQL_HOST'] = app_settings['MYSQL_HOST']
app.config['MYSQL_USER'] = app_settings['MYSQL_USER']
app.config['MYSQL_PASSWORD'] = app_settings['MYSQL_PASSWORD']
app.config['MYSQL_DB'] = app_settings['MYSQL_DB']
app.config['MYSQL_CURSORCLASS'] = app_settings['MYSQL_CURSORCLASS']

# Init MYSQL
mysql = MySQL(app)

#Articles = Articles()

# Index
@app.route('/')
def index():
    return render_template('home.html')

# About
@app.route('/about')
def about():
    return render_template('about.html')

# Articles
@app.route('/articles')
def articles():
    # CREATE cursor
    cur = mysql.connection.cursor()

    # Get articles
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No articles found'
        return render_template('articles.html', msg=msg)
    # Close connection
    cur.close()

#Single Article
@app.route('/article/<string:id>')
def article(id):
    # CREATE cursor
    cur = mysql.connection.cursor()

    # Get articles
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

    article = cur.fetchone()


    return render_template('article.html', article=article)

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
    cur = mysql.connection.cursor()

    # Get articles
    result = cur.execute("SELECT * FROM articles WHERE author = %s",[session['name']])

    articles = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No articles found'
        return render_template('dashboard.html', msg=msg)
    # Close connection
    cur.close()


#Article form class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1,max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])

# Add Article
@app.route ('/add_article', methods=['GET','POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        #create cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s,%s,%s)",(title, body, session['name']))

        #Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Article created','success')

        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)

# Edit Article
@app.route ('/edit_article/<string:id>', methods=['GET','POST'])
@is_logged_in
def edit_article(id):
    #create cursor
    cur = mysql.connection.cursor()

    #Get article by id
    result = cur.execute("SELECT * FROM articles WHERE id = %s",[id])

    article = cur.fetchone()

    #Get form
    form = ArticleForm(request.form)

    #Populate article form fields
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        #create cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("UPDATE articles SET title=%s, body=%s WHERE id = %s",(request.form['title'], request.form['body'], id))

        #Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Article updated','success')

        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)

# Delete article
@app.route('/delete_article/<string:id>', methods=["POST"])
@is_logged_in
def delete_article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    #Execute
    cur.execute("DELETE FROM articles where id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    #close connection
    cur.close()

    flash('Article deleted', 'success')

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    application.secret_key = os.environ.get("SECRET_KEY", default=None)
    app.run(debug=True)
