from flask import Flask, render_template,flash, redirect, url_for, request, session, logging
#from data import Articles
from flaskext.mysql import MySQL
from pymysql.cursors import DictCursor
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

mysql = MySQL(cursorclass=DictCursor)
 
# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'root'
app.config['MYSQL_DATABASE_DB'] = 'flaskapp_db'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
#app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# init Mysql
mysql.init_app(app)

# Articles has a return value -> this is data from file not DB
# Articles = Articles()

@app.route('/')
def index():
	return render_template('home.html')

@app.route('/about')
def about():
	return render_template('about.html')

# list of articles
@app.route('/articles')
def articles():
	# create connection zo DB
	conn = mysql.connect()

	# create cursor
	cur = conn.cursor()

	# get articles
	result = cur.execute("SELECT * FROM articles")
	articles = cur.fetchall()
	if result > 0:
		return render_template('articles.html', articles=articles)
	else:
		msg = 'No Articles Found'
		return render_template('articles.html', msg=msg)

	# close connection
	cur.close()

# show single article
@app.route('/article/<string:id>/')
def article(id):
	# create connection zo DB
	conn = mysql.connect()

	# create cursor
	cur = conn.cursor()

	# get articles
	result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
	article = cur.fetchone()
	# all data about this article
	return render_template('article.html', article=article)

# register Form class
class RegisterForm(Form):
	name = StringField('Name', [validators.Length(min=1, max=50)])
	username = StringField('Username', [validators.Length(min=4, max=25)])
	email = StringField('Email', [validators.Length(min=6, max=50)])
	password = PasswordField('Password', [
		validators.DataRequired(),
		validators.EqualTo('confirm', message='Passwords do not match')
	])
	confirm = PasswordField('Confirm Password')

# register User
@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		name = form.name.data
		email = form.email.data
		username = form.username.data
		password = sha256_crypt.encrypt(str(form. password.data))

		# create connection zo DB
		conn = mysql.connect()

		#create cursor
		cursor = conn.cursor()

		# execute query
		cursor.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

		# commit to DB
		conn.commit()

		# close connection
		cursor.close()

		flash('You are now registered and can log in.', 'success')
		return redirect(url_for('login'))

	return render_template('register.html', form=form)

# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		#get form fields
		username = request.form['username']
		password_candidate = request.form['password']

		# create connection zo DB
		conn = mysql.connect()

		# create cursor
		cur = conn.cursor()

		# get user by username
		result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

		#if there exists that user
		if result > 0:
			# get stored hash -> gets the first row that matches
			data = cur.fetchone()

			app.logger.info(data)

			# this works because we defined MYSQL_DATABASE_CURSORCLASS
			password = data['password']

			# compare passwords
			if sha256_crypt.verify(password_candidate, password):
				# app.logger.info('PASSWORD MATCHED')
				session['logged_in'] = True
				session['username'] = username

				flash('You are logged in!', 'success')
				return redirect(url_for('dashboard'))
			else:
				error = 'Invalid password!'
				return render_template('login.html', error=error)

			# close connection
			cur.close()

		else:
			error = 'Username not found!'
			return render_template('login.html', error=error)

	return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized, Please log in', 'danger')
			return redirect(url_for('login'))
	return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You are now log out!', 'success')
	return redirect(url_for('index'))

# user's dashboard
@app.route('/dashboard')
@is_logged_in #you can go here only if you're logged in
def dashboard():
	# create connection zo DB
	conn = mysql.connect()

	# create cursor
	cur = conn.cursor()

	# get articles
	result = cur.execute("SELECT * FROM articles")
	articles = cur.fetchall()
	if result > 0:
		return render_template('dashboard.html', articles=articles)
	else:
		msg = 'No Articles Found'
		return render_template('dashboard.html', msg=msg)

	# close connection
	cur.close()

# Article Form class
class ArticleForm(Form):
	title = StringField('Title', [validators.Length(min=1, max=200)])
	body = TextAreaField('Body', [validators.Length(min=30)])
	
# Add Article
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
	form = ArticleForm(request.form)
	if request.method == 'POST' and form.validate():
		title = form.title.data
		body = form.body.data

		# create connection zo DB
		conn = mysql.connect()

		# create cursor
		cur = conn.cursor()

		# execute 
		cur.execute("INSERT INTO articles(title, body, author) VALUES (%s, %s, %s)", (title, body, session['username']))

		# commit to DB
		conn.commit()

		# close connection
		cur.close()

		flash('Article created', 'success')
		return redirect(url_for('dashboard'))
	return render_template('add_article.html', form=form)

# Edit Article
@app.route('/edit_article/<string:id>/', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
	# create connection zo DB
	conn = mysql.connect()
	# create cursor
	cur = conn.cursor()
	
	# get user by id
	result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
	article = cur.fetchone()

	# get form which you will fill with data
	form = ArticleForm(request.form)
	# populate article form fields
	form.title.data = article['title']
	form.body.data = article['body']

	if request.method == 'POST' and form.validate():
		title = request.form['title']
		body = request.form['body']

		# create connection zo DB
		conn = mysql.connect()

		# create cursor
		cur = conn.cursor()

		# execute 
		cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s", (title, body, id))

		# commit to DB
		conn.commit()

		# close connection
		cur.close()

		flash('Article edited', 'success')
		return redirect(url_for('dashboard'))
	return render_template('edit_article.html', form=form)

# Delete article
@app.route('/delete_article/<string:id>/', methods=['POST'])
@is_logged_in
def delete_article(id):
	# create connection zo DB
	conn = mysql.connect()
	# create cursor
	cur = conn.cursor()
	
	# execute
	cur.execute("DELETE FROM articles WHERE id = %s", [id])

	# commit to DB
	conn.commit()

	# close connection
	cur.close()

	flash('Article deleted', 'success')
	return redirect(url_for('dashboard'))

# if script is gonna be executed
if __name__=='__main__':
	app.secret_key = 'sdf6rht78ut'
	#when you save changes, the changes are seen in browser
	# if debug=True
	app.run(debug=True) 