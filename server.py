from flask import Flask, render_template, redirect, request, flash, session
from mysqlconnection import connectToMySQL
import re
from flask_bcrypt import Bcrypt
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret"
schema = "my_db"
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$') 
bcrypt = Bcrypt(app)

@app.route('/')
def index():
    return render_template("index.html")

@app.route("/registration", methods=['POST'])
def registration():
    is_valid = True
    if len(request.form['first_name']) < 2:
        is_valid = False
        flash("First name is a required field")
    if len(request.form['last_name']) < 2:
        is_valid = False
        flash("Last name is a required field")
    
    if len(request.form['email']) < 1:
        is_valid = False
        flash("Email is a required field")
    elif not EMAIL_REGEX.match(request.form['email']):
        is_valid = False
        flash("Please enter a valid email address")    
    else:
        mysql = connectToMySQL(schema)
        query = 'SELECT * FROM users WHERE email = %(email)s;'
        data = {
            'email': request.form['email']
        }
        user = mysql.query_db(query,data)
        if user:
            is_valid = False
            flash("Email address is already registered")
    

    if len(request.form['password']) <= 5:
        is_valid = False
        flash("Password must be at least 5 characters long")
    if request.form['cpassword'] != request.form['password']:
        is_valid = False
        flash("Passwords must match")

    if is_valid:
        pw_hash = bcrypt.generate_password_hash(request.form['password'])
        mysql = connectToMySQL(schema)
        query = "INSERT INTO users (first_name, last_name, email, password, created_at, updated_at) VALUES (%(fn)s, %(ln)s, %(email)s, %(pass)s, NOW(), NOW());"
        data = {
            "fn": request.form["first_name"],
            "ln": request.form["last_name"],
            "email": request.form["email"],
            "pass": pw_hash
        }
        user_id = mysql.query_db(query, data)
        flash("Registration complete")
    return redirect("/")

@app.route("/login", methods=['POST'])
def login():
    is_valid = True

    if len(request.form['email']) < 1:
        is_valid = False
        flash("Email is required")
    if len(request.form['password']) < 1:
        is_valid = False
        flash("Password is required")
    if is_valid:
        mysql = connectToMySQL(schema)
        query = "SELECT * FROM users WHERE email = %(email)s;"
        data = {
            "email": request.form['email']
        }
        user = mysql.query_db(query, data)
        if user:
            if bcrypt.check_password_hash(user[0]['password'], request.form['password']):
                session['user_id'] = user[0]['id']
                return redirect("/dashboard")
            else:
                flash("Email or password incorrect")
        else:
            flash("Email or password incorrect")
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect('/')

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    
    mysql = connectToMySQL(schema)
    query = "SELECT * FROM users WHERE id = %(id)s;"
    data = {
        "id": session['user_id']
    }
    user = mysql.query_db(query, data)

    mysql = connectToMySQL(schema)
    query = "SELECT users.first_name, users.last_name, messages.content, messages.created_at, messages.id, messages.user_id FROM users JOIN messages ON messages.user_id = users.id ORDER BY messages.created_at DESC;"
    messages = mysql.query_db(query)

    for message in messages:
        message['created_at'] = message['created_at'].strftime("%b %d %Y %H:%M:%S")

    mysql = connectToMySQL(schema)
    query = "SELECT users.first_name, users.last_name, comments.content, comments.created_at, comments.id, comments.message_id, comments.user_id FROM users JOIN comments ON comments.user_id = users.id ORDER BY comments.created_at;"
    comments = mysql.query_db(query)

    return render_template('dashboard.html', this_user=user[0], all_messages=messages, all_comments=comments)

@app.route("/message/create", methods=["POST"])
def message():
    mysql = connectToMySQL(schema)
    query = "INSERT INTO messages (content, user_id, created_at, updated_at) VALUES (%(content)s, %(user_id)s, NOW(), NOW());"
    data = {
        "content": request.form["message"],
        "user_id": session['user_id']
        }
    message = mysql.query_db(query, data)
    return redirect("/dashboard")

@app.route("/message/<message_id>/comment", methods=["POST"])
def comment(message_id):
    message_id = int(message_id)

    mysql = connectToMySQL(schema)
    query = 'SELECT * FROM messages WHERE id = %(id)s;'
    data = {
        'id': message_id
    }
    validate_message = mysql.query_db(query,data)
    
    if validate_message:

        mysql = connectToMySQL(schema)
        query = "INSERT INTO comments (content, user_id, message_id, created_at, updated_at) VALUES (%(content)s, %(user_id)s, %(message_id)s, NOW(), NOW());"
        data = {
            "content": request.form["comment"],
            "user_id": session['user_id'],
            "message_id": message_id
        }
        comment = mysql.query_db(query, data)
        return redirect("/dashboard")

@app.route("/message/<message_id>/delete")
def delete_message(message_id):
    query = "DELETE FROM comments WHERE message_id = %(message_id)s AND user_id = %(id)s;"
    data = {
        'message_id': message_id,
        'id': session['user_id']
    }
    mysql = connectToMySQL(schema)
    mysql.query_db(query, data)

    query = "DELETE FROM messages WHERE id = %(message_id)s AND user_id = %(id)s;"
    data = {
        'message_id': message_id,
        'id': session['user_id']
    }
    mysql = connectToMySQL(schema)
    mysql.query_db(query, data)
    return redirect("/dashboard")

@app.route("/comment/<comment_id>/delete")
def delete_comment(comment_id):
    query = "DELETE FROM comments WHERE id = %(comment_id)s AND user_id = %(id)s;"
    data = {
        'comment_id': comment_id,
        'id': session['user_id']
    }
    mysql = connectToMySQL(schema)
    mysql.query_db(query, data)
    return redirect("/dashboard")


if __name__ == "__main__":
    app.run(debug=True)