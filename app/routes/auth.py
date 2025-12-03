from flask import Flask, request, redirect, url_for, session, render_template, flash, Blueprint
import os
auth_bp = Blueprint('auth', __name__)

user_credential = {
     'username' : os.environ.get("USERNAME"),
     'password' :os.environ.get("PASSWORD")
}


@auth_bp.route("/login", methods = ['GET', 'POST'])
def login() :
    if request.method == 'POST' :
        username = request.form.get('username')
        password = request.form.get('password')

        if username == user_credential['username'] and password == user_credential['password'] :
            session['user'] = username
            session['admin'] = True
            flash("Login Successful", "success")
            return redirect(url_for('tasks.dashboard'))
        else:
            flash("Invalid username or password", "error")
        
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('auth.login'))
    