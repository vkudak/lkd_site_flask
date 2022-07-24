from flask import Blueprint, render_template, redirect, url_for


home_bp = Blueprint('home', __name__)


@home_bp.route('/')
@home_bp.route('/index.html')
def index():
    # global eb_users
    # eb_users = []
    # with open("eb_users.lst") as f:
    #     for line in f:
    #         eb_users.append(line.strip())
    return render_template('index.html')


@home_bp.route('/about.html')
def about():
    return render_template('about.html')


@home_bp.route('/contact.html')
def contact():
    return render_template('contact.html')