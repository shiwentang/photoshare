######################################
# author ben lawson <balawson@bu.edu>
# Edited by: Craig Einstein <einstein@bu.edu>
# Edited by: Shiwen Tang <shiwent@bu.edu>
######################################
# Some code adapted from
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

from getpass import getuser
from unicodedata import name
import flask
from flask import Flask, Response, request, render_template, redirect, url_for, session
from flaskext.mysql import MySQL
import flask_login
from datetime import date

#for image uploading
import os, base64

from graphviz import render

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'mysql'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT user_id from Users")
users = cursor.fetchall()
firstLogin = True


def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT user_id from Users")
	return cursor.fetchall()

def getUserEmailFromId(id):
	cursor = conn.cursor()
	cursor.execute("SELECT email FROM Users WHERE user_id = '{0}'".format(id))
	return cursor.fetchone()[0]

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(user_id):
	users = getUserList()
	if not(user_id) or user_id not in str(users):
		return
	user = User()
	user.id = user_id
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or getUserIdFromEmail(email) or getUserIdFromEmail(email) not in str(users):
		return
	user = User()
	user_id = getUserIdFromEmail(email)
	user.id = user_id
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE user_id = '{0}'".format(user_id))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = (request.form['password'] == pwd)
	return user

'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = getUserIdFromEmail(email)
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"


@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out', logout='yes')

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html')

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
	return render_template('register.html', supress='True')

@app.route("/register", methods=['POST'])
def register_user():
	try:
		first_name = request.form.get('first_name')
		last_name = request.form.get('last_name')
		email = request.form.get('email')
		birth_date = request.form.get('birth_date')
		hometown = request.form.get('hometown')
		gender = request.form.get('gender')
		password = request.form.get('password')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print(cursor.execute("INSERT INTO Users (first_name, last_name, email, birth_date, hometown, gender, password) \
							VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format \
							(first_name, last_name, email, birth_date, hometown, gender, password)))
		conn.commit()
		#log user in
		user = User()
		user.id = getUserIdFromEmail(email)
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!')
	else:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('register'))

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT data, photo_id, caption, user_id FROM Photos WHERE user_id = '{0}'".format(uid))
	conn.commit()
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]


def getPhotos():
	cursor = conn.cursor()
	cursor.execute("SELECT data, photo_id, caption, user_id FROM Photos")
	conn.commit()
	return cursor.fetchall() 


def delete_photos(pid):
	cursor = conn.cursor()
	print(cursor.execute("DELETE FROM Photos WHERE photo_id = '{0}'".format(pid)))
	conn.commit()
	return cursor.fetchall()


# show photos with tags, comments, photo_id
def getInfoFromPhotos(uid=None):
	cursor = conn.cursor()
	if uid :
		cursor.execute("SELECT Photos.data, Photos.photo_id, Photos.caption, Users.email, \
						GROUP_CONCAT(DISTINCT Tags.name), GROUP_CONCAT(DISTINCT Tags.tag_id), \
						GROUP_CONCAT(DISTINCT Comments.text)  \
						FROM Users, Photos \
						LEFT JOIN Comments ON Comments.photo_id = Photos.photo_id \
						LEFT JOIN Tagged ON Photos.photo_id = Tagged.photo_id \
						LEFT JOIN Tags ON Tagged.tag_id = Tags.tag_id \
						WHERE Users.user_id = Photos.user_id AND Photos.user_id = '{0}'\
						GROUP BY Photos.photo_id".format(uid))
	else:
		cursor.execute("SELECT Photos.data, Photos.photo_id, Photos.caption, Users.email, \
						GROUP_CONCAT(DISTINCT Tags.name), GROUP_CONCAT(DISTINCT Tags.tag_id), \
						GROUP_CONCAT(DISTINCT Comments.text) \
						FROM Users, Photos \
						LEFT JOIN Comments ON Comments.photo_id = Photos.photo_id \
						LEFT JOIN Tagged ON Photos.photo_id = Tagged.photo_id \
						LEFT JOIN Tags ON Tagged.tag_id = Tags.tag_id \
						WHERE Users.user_id = Photos.user_id\
						GROUP BY Photos.photo_id")
		
	conn.commit()
	return cursor.fetchall()



def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return False
	else:
		return True
#end login code

@app.route('/profile', methods=['GET', 'POST'])
@flask_login.login_required
def protected():
	uid = flask_login.current_user.id
	photo = getUsersPhotos(uid)
	user_photos = getUsersPhotos(uid)
	session['like'] = getUserLikeFromPhoto()
	session['likenum'] = getLikeUsersNum()

	if request.method == 'POST':
		if 'viewmyp' in request.form:
			photo = getInfoFromPhotos(uid)
			return render_template('profile.html', name=getUserEmailFromId(uid), \
				message="Here's your profile", photos=photo, base64=base64\
				,userphotos=user_photos)
		if 'viewallp' in request.form:
			photo = getInfoFromPhotos()
			return render_template('profile.html', name=getUserEmailFromId(uid), \
				message="Here's your profile", photos=photo, base64=base64\
				,userphotos=user_photos)

	# add tag
		try:
			tag = request.form.get('tag')
			pid = request.form.get('photo_id')
		except:
			print("couldn't find all tokens")
			return redirect(url_for('protected'))

		cursor = conn.cursor()
		cursor.execute("INSERT INTO Tags (name) VALUES ('{0}')".format(tag))
		cursor.execute("INSERT INTO Tagged (photo_id, tag_id) VALUES('{0}', LAST_INSERT_ID())".format(pid))
		conn.commit()
	photo = getInfoFromPhotos()

	return render_template('profile.html', name=getUserEmailFromId(uid), \
				message="Here's your profile", photos=photo, base64=base64\
				,userphotos=user_photos)

def getTags():
	cursor = conn.cursor()
	cursor.execute("SELECT DISTINCT name FROM Tags")
	conn.commit()
	return cursor.fetchall() 


'''
list tags
'''
@app.route('/tag', methods=['GET', 'POST'])
def tag():
	tags = getTags()
	popTag = getPopTag()
	return render_template('tag.html', tags=tags, popTag=popTag)

# most popular tag
def getPopTag():
	cursor = conn.cursor()
	cursor.execute("SELECT Temp.name\
					FROM (SELECT Tags.name, COUNT(Photos.photo_id) AS numPhotos \
					FROM Photos, Tagged, Tags\
					WHERE Photos.photo_id = Tagged.photo_id AND Tagged.tag_id = Tags.tag_id\
					GROUP BY Tags.name) AS Temp\
					ORDER BY numPhotos DESC limit 1")
	conn.commit()
	return cursor.fetchall()

@app.route('/tagtemp')
def tagtemp():
	return render_template('tagtemp.html')

# route for each tag
@app.route('/tag/<tagname>')
def view_tag(tagname):
	photos = getPhotosFromTag(tagname)
	return render_template('tagtemp.html', photos=photos, base64=base64)
   
# show photos with tags
def getPhotosFromTag(tag):
	cursor = conn.cursor()
	cursor.execute("SELECT Photos.data, Photos.caption FROM Photos, Tagged, Tags\
					WHERE Photos.photo_id = Tagged.photo_id AND \
					Tags.tag_id = Tagged.tag_id AND Tags.name = '{0}'"\
					.format(tag))
	conn.commit()
	return cursor.fetchall()


#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid = flask_login.current_user.id
		caption = request.form.get('caption')
		aid = request.form.get('album_id')
		imgfile = request.files['photo']
		photo_data =imgfile.read()
		cursor = conn.cursor()
		cursor.execute('''INSERT INTO Photos (caption, data, user_id, albums_id) VALUES (%s, %s, %s, %s)''',\
											 (caption, photo_data, uid, aid))
		conn.commit()
		photo = getInfoFromPhotos()
		session['like'] = getUserLikeFromPhoto()
		session['likenum'] = getLikeUsersNum()
		return render_template('hello.html', name=getUserEmailFromId(flask_login.current_user.id),\
							message='Photo uploaded!', photos=photo, base64=base64)
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html', albumList=list_user_albums(flask_login.current_user.id),\
							name=getUserEmailFromId(flask_login.current_user.id))
#end photo uploading code

'''
serach photos based on tags
'''
@app.route('/photosearch', methods=['GET', 'POST'])
def photo_search():
	if request.method == 'POST':
		try: 
			tags = request.form.get('tags')
			tag_list = tags.split()
		except:
			print("couldn't find all tokens")
			return render_template('photosearch.html')
		photos = getPhotosFromTags(tag_list)
		return render_template('photosearch.html',
								base64=base64, photos=photos)
	return render_template('photosearch.html')

def getPhotosFromTags(tag_list):
	cursor = conn.cursor()
	sql0 = '''SELECT DISTINCT Photos.data FROM Photos, Tags, Tagged WHERE Photos.photo_id=Tagged.photo_id AND Tags.tag_id=Tagged.tag_id AND Tags.name = %s'''
	sql1 = ''' AND Photos.data IN (SELECT Photos.data FROM Photos, Tags, Tagged WHERE Photos.photo_id=Tagged.photo_id AND Tags.tag_id=Tagged.tag_id AND Tags.name = %s)'''
	sql =sql0  + ''.join([sql1]*(len(tag_list)-1))
	cursor.execute(sql, tuple(tag_list))			
	conn.commit()
	return cursor.fetchall()

'''
comments
'''
@app.route('/comment', methods=['GET', 'POST'])
def comment():
	if request.method == 'POST':
		try:
			comment = request.form.get('comment')
			pid = request.form.get('pid')
		except:
			print("could't find all tokens")
			return redirect(request.referrer)

		uid = -1 # visitor
		if flask_login.current_user.is_authenticated:
			uid = flask_login.current_user.id 
		# cannot leave comments on their photos
		uidPhoto = getUidFromPid(pid)
		if int(uid) == int(uidPhoto):
			print("Cannot leave comments on their own photos")
			return redirect(request.referrer)

		curr_date = date.today().strftime("%y-%m-%d")
		cursor = conn.cursor()
		cursor.execute('''INSERT INTO Comments (user_id, photo_id, text, date) VALUES (%s, %s, %s, %s)''',\
							(uid, pid, comment, curr_date))
		conn.commit()

	session["like"] = getUserLikeFromPhoto() 
	return redirect(request.referrer)

def getUidFromPid(pid):
	cursor = conn.cursor()
	cursor.execute("SELECT Photos.user_id FROM Photos WHERE Photos.photo_id = '{0}'".format(pid))
	conn.commit()
	return cursor.fetchone()[0]


'''
Likes
'''
@app.route('/like', methods=['GET', 'POST'])
@flask_login.login_required
def like():
	if request.method =='POST':
		if 'like' in request.form:
			try:
				pid = request.form.get('pid')
			except:
				print("couldn't find all tokens")
				return redirect(request.referrer)

			uid = flask_login.current_user.id
			
			if isLikeBefore(pid, uid) == 0:
				cursor = conn.cursor()
				cursor.execute('''INSERT INTO Likes (photo_id, user_id) VALUES (%s, %s)''', (pid, uid))
				conn.commit()

	session["like"] = getUserLikeFromPhoto() 
	session['likenum'] = getLikeUsersNum()

	return redirect(request.referrer)

# check click likes before
def isLikeBefore(pid, uid):
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(Likes.user_id) FROM Likes WHERE Likes.photo_id='{0}' AND Likes.user_id='{1}' ".format(pid, uid))
	conn.commit()
	return cursor.fetchone()[0]

def getLikeUsersNum():
	cursor = conn.cursor()
	cursor.execute("SELECT Likes.photo_id, COUNT(Likes.user_id) FROM Likes GROUP BY Likes.photo_id")
	conn.commit()
	return cursor.fetchall()

# show who likes the photo
def getUserLikeFromPhoto():
	cursor = conn.cursor()
	cursor.execute("SELECT Likes.user_id, Likes.photo_id, Users.email \
					FROM Users, Likes WHERE Likes.user_id = Users.user_id")
	conn.commit()
	return cursor.fetchall()



'''
comment
'''
@app.route('/commsearch', methods=['GET', 'POST'])
def commsearch():
	if request.method == 'POST':
		try:
			comment = request.form.get('comment')
		except:
			print("couldn't find all tokens")
			return redirect('commsearch.html')
		
		users = getUserFromComm(comment)
		return render_template('commsearch.html', users = users)

	return render_template('commsearch.html')


def getUserFromComm(text):
	cursor = conn.cursor()
	cursor.execute("SELECT Users.email, COUNT(Comments.comment_id) FROM Users, Comments \
					WHERE Users.user_id=Comments.user_id AND Comments.text = '{0}' AND Users.user_id<>'-1'\
					GROUP BY Users.email\
					ORDER BY COUNT(Comments.comment_id) DESC".format(text))
	conn.commit()
	return cursor.fetchall()


'''
contributors
'''
@app.route('/contribution', methods=['POST','GET'])
def contribution():
	users = top10contributors()
	return render_template('contribution.html', users = users)


def top10contributors():
	cursor = conn.cursor()
	cursor.execute("SELECT Temp.email, COUNT(DISTINCT Temp.cid)+COUNT(DISTINCT Temp.pid), COUNT(DISTINCT Temp.cid), COUNT(DISTINCT Temp.pid) \
					FROM (SELECT Users.email AS email, Comments.comment_id AS cid, Photos.photo_id AS pid\
					FROM Users, Comments, Photos \
					WHERE Users.user_id = Comments.user_id AND Photos.user_id = Users.user_id) AS Temp \
					GROUP BY Temp.email\
					ORDER BY COUNT(DISTINCT Temp.cid)+COUNT(DISTINCT Temp.pid) DESC LIMIT 10")
	conn.commit()
	return cursor.fetchall()


'''
friends
'''
@app.route('/friend', methods=['GET', 'POST'])
@flask_login.login_required
def friends():
	try:
		email = request.form.get('email')
	except:
		print("couldn't find all tokens") 
		return render_template('friend.html')

	is_self = check_friend(email)
	data = list_friends()
	# add_friend
	if is_self:
		cursor = conn.cursor()
		# user0 is the current user, user1 is the friend
		uid0 = flask_login.current_user.id
		# check if email is registered
		if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):

			uid1 = getUserIdFromEmail(email)
			print(cursor.execute('''INSERT INTO Friends(user_id1, user_id2) VALUES (%s, %s)''', (uid0, uid1)))
			conn.commit()
			data = list_friends()
			recomf = friendrecom()
			return render_template('friend.html', name=getUserEmailFromId(flask_login.current_user.id), \
								message='Friend added!', data=data, friends=recomf)
	recomf = friendrecom()
	return render_template('friend.html', name=getUserEmailFromId(flask_login.current_user.id), \
								message='You cannot make friends with yourself! Please try again.', data=data, friends=recomf)

def check_friend(email):
	user_email = getUserEmailFromId(flask_login.current_user.id)
	if user_email == email:
		return False
	else:
		return True

def list_friends():
	cursor = conn.cursor()
	uid = flask_login.current_user.id
	cursor.execute("SELECT Users.email FROM Friends, Users \
					WHERE Friends.user_id1='{0}' AND Friends.user_id2=Users.user_id ".format(uid))
	conn.commit()
	return cursor.fetchall()

# find the common friends of user1's friends 
# # of time appears in user1's friends is in descending order
def friendrecom():
	cursor = conn.cursor()
	uid = flask_login.current_user.id 
	cursor.execute("SELECT Users.email, COUNT(F2.user_id2) FROM Users, Friends AS F1 \
					LEFT JOIN Friends AS F2 ON F1.user_id2 = F2.user_id1 \
					WHERE F1.user_id1='{0}' AND Users.user_id = F2.user_id2 \
                    GROUP BY F2.user_id2 \
					ORDER BY COUNT(F2.user_id2) DESC".format(uid))
	conn.commit()
	return cursor.fetchall()

'''
you-may-also-like
'''
@app.route('/alsolike', methods=['GET', 'POST'])
@flask_login.login_required
def alsolike():
	uid = flask_login.current_user.id  
	photos = getPhotoFromTags(uid)
	return render_template('alsolike.html', photos=photos, base64=base64)

# table: tags in top 5 tag list, photo_id
# count tag number which is the recommendation index
def getPhotoFromTags(uid):
	tags = [i[0] for i in getTagsFromUser(uid)]
	cursor = conn.cursor()
	format = ','.join(['%s'] * len(tags))
	if tags!=[]:
		cursor.execute('''SELECT Photos.data, Tagged.photo_id, Photos.caption, COUNT(DISTINCT Tags.name) \
						FROM Tags, Tagged, Photos \
						WHERE Photos.photo_id = Tagged.photo_id AND Tags.tag_id = Tagged.tag_id AND Tags.name IN (%s) \
						GROUP BY Photos.photo_id \
						ORDER BY COUNT(Tags.name) DESC'''% format,tuple(tags))
		conn.commit()
		return cursor.fetchall()

# top 5 tags for user uid
def getTagsFromUser(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT DISTINCT Tags.name FROM Tags, Tagged, Photos \
					WHERE Tags.tag_id=Tagged.tag_id AND Tagged.photo_id=Photos.photo_id\
					AND Photos.user_id = '{0}' LIMIT 5".format(uid))
	conn.commit()
	return cursor.fetchall()

'''
begin albums code
''' 

# user albums
@app.route('/album', methods=['POST'])
@flask_login.login_required
def user_album():
	data = list_albums()
	uid = flask_login.current_user.id
	albumList = list_user_albums(uid)
	if request.method == 'POST':
		session['name'] = getUserEmailFromId(uid)

		if 'viewmy' in request.form:
			data = list_user_albums(uid)
			return render_template('album.html', data=data, list=albumList)

		if 'viewall' in request.form:
			session['data'] = list_albums()
			return render_template('album.html', data=data, list=albumList)

		if request.form.get('album_name') == None and request.form.get('album_id') == None:
			session['message'] = "Please enter the value!"
			return redirect(url_for('album'))

		if request.form['identifier'] == '0':
			album_name = request.form.get('album_name')
			if album_name == None:
				session['message'] = 'Please enter the album name!'
			else:
				data = create_album(album_name, data)
				session['data'] = list_albums()
				session['message'] ='Album created!'
			return redirect(url_for('album'))

		if request.form['identifier'] == '1':
			aid = request.form.get('album_id')
			if aid == None:
				session['message'] ='Please enter the album ID!'
			else:
				data = delete_album(aid, data)
				session['data'] = list_albums()
				session['message'] ='Album Delete!'
			return redirect(url_for('album'))
	return render_template('album.html', data=data, list=albumList)

def list_albums():
	cursor = conn.cursor()
	cursor.execute("SELECT Albums.name, Albums.date, Users.email, Albums.albums_id \
					FROM Albums, Users WHERE Albums.user_id = Users.user_id")
	return cursor.fetchall()

def list_user_albums(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT Albums.name, Albums.date, Users.email, Albums.albums_id \
					FROM Albums, Users WHERE Albums.user_id=Users.user_id AND Users.user_id='{0}'".format(uid))
	return cursor.fetchall()

# public albums
@app.route('/album', methods=['GET'])
def album():
	data = list_albums()
	# login
	if flask_login.current_user.is_authenticated:
		uid = flask_login.current_user.id
		albumList = list_user_albums(uid)
		if firstLogin:
			session['data'] = data
			session['name']=getUserEmailFromId(uid)
		return render_template('album.html', data=session['data'], \
							name=session['name'], list=albumList)
	# public
	return render_template('album.html', data=data)

def list_albums():
	cursor = conn.cursor()
	cursor.execute("SELECT Albums.name, Albums.date, Users.email, Albums.albums_id \
					FROM Albums, Users WHERE Albums.user_id = Users.user_id")
	conn.commit()
	return cursor.fetchall()

def list_user_albums(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT Albums.name, Albums.date, Users.email, Albums.albums_id \
					FROM Albums, Users WHERE Albums.user_id='{0}' AND Users.user_id='{0}'".format(uid))
	conn.commit()
	return cursor.fetchall()

def create_album(name, data): 
	cursor = conn.cursor()
	uid = flask_login.current_user.id
	curr_date = date.today().strftime("%y-%m-%d")
	print(cursor.execute('''INSERT INTO Albums(name, date, user_id) VALUES (%s, %s, %s)''', (name, curr_date, uid)))
	conn.commit()
	data = list_albums()
	return data

def delete_album(aid, data):
	aid = request.form.get('album_id')
	cursor = conn.cursor()
	print(cursor.execute("DELETE FROM Albums WHERE albums_id = '{0}'".format(aid)))
	conn.commit()
	data = list_albums()
	return data





#default page
@app.route("/", methods=['GET'])
def hello():
	session['like'] = getUserLikeFromPhoto()
	session['likenum'] = getLikeUsersNum()
	return render_template('hello.html', message='Welecome to Photoshare!', \
		photos=getInfoFromPhotos(), base64=base64)


			



if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)
