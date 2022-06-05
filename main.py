from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_gravatar import Gravatar
from functools import wraps
import yagmail
import os

from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm, MessageForm
from find_colors import FindColors


# variables for email
email_username = os.environ['EMAIL']
password = os.environ['PASSWORD']
form_receive_email = os.environ['RECEIVE_EMAIL']

# variables for color extractor page
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# initiating flask app
app = Flask(__name__)
Bootstrap(app)
app.config['SECRET_KEY'] = os.urandom(26)

# for blog
ckeditor = CKEditor(app)

# - for color extractor configuration -
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
# max file size
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


# verifies file for color extractor
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ,
# #CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES

# Blog Tables
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    posts = relationship("BlogPost", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="comment_author")

    # to_do = relationship("ToDo", back_populates="user")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    # author = db.Column(db.String(250), nullable=False)

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    comments = relationship("Comment", back_populates="parent_post")

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comment_author = relationship("User", back_populates="comments")

    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    text = db.Column(db.Text, nullable=False)


db.create_all()
login_manager = LoginManager()
login_manager.init_app(app)


gravatar = Gravatar(app, size=100, rating='r', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Allows current date to be injected into all pages
@app.context_processor
def inject_now():
    return {'now': datetime.now()}


# functions for main page
@app.route("/")
def home():
    return render_template("index.html")


# Functions for blog
@app.route('/blog')
def get_all_posts():
    posts = BlogPost.query.all()
    print(posts)
    return render_template("blog.html", all_posts=posts)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash("You've already signed up, log in instead.")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method="pbkdf2:sha256",
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=form)


@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        pword = form.password.data

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("That email does not exist in the database, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, pword):
            flash("Incorrect password")
            return redirect(url_for('login'))
        else:
            # if check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    comment_form = CommentForm()
    requested_post = BlogPost.query.get(post_id)

    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for('login'))

        new_comment = Comment(
            text=comment_form.comment_text.data,
            comment_author=current_user,
            parent_post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, form=comment_form, current_user=current_user)


@app.route("/about")
def about():
    return render_template("about.html")


# Function to allow email to be sent from contact form
def send_email(name, mail, message, phone=None):
    email = yagmail.SMTP(user=email_username, password=password)
    email.send(to=form_receive_email,
               subject=f"Contact Form Message From: {name}.",
               contents=f"{name}\n\n{mail}\n\n{phone}\n\n\n{message}")


@app.route("/contact", methods=["POST", "GET"])
def contact():
    form = MessageForm()
    if request.method == "POST":
        name = form.name.data
        email = form.email.data
        phone = form.phone.data
        message = form.message.data
        send_email(name, email, phone, message)
        return render_template("blog.html")
    return render_template("contact.html", form=form)


# Allows admin only functions
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            the_id = current_user.id
        except:
            print("no user")
            the_id = 0
        if the_id == 1:
            return f(*args, **kwargs)
        return abort(403)
    return decorated_function


# Admin only functions for blog
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    print(post)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>", methods=["Get", "POST"])
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))
# End blog functions


# Color Extractor functions
@app.route('/extract-colors', methods=["POST", "GET"])
def upload_form():
    return render_template('upload.html')


@app.route('/extracted-colors', methods=['POST', 'GET'])
def upload_image():
    if 'file' not in request.files:
        flash('No file')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No image selected for uploading')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        print('upload_image filename: ' + filename)

        color_list = []
        colors = FindColors(file).find_colors()
        for color in colors:
            color_list.append(color.split()[-1].lstrip('(').rstrip(')'))
        dominant = FindColors(file).find_dominant_color().split()[-1].lstrip('(').rstrip(')')
        num_colors = len(color_list)
        print(color_list)
        flash('Upload Successful')

        return render_template('upload.html',
                               filename=filename,
                               colors=color_list,
                               dominant=dominant,
                               num_colors=num_colors)
    else:
        flash('Allowed image types are -> png, jpg, jpeg')
        return redirect(request.url)


@app.route('/display/<filename>', methods=["POST", "GET"])
def display_image(filename):
    print('display_image filename: ' + filename)
    return redirect(url_for('static', filename='uploads/' + filename), code=301)
# End color extractor functions


@app.route('/dnd_main')
def game():
    return render_template('dnd-reference.html')


if __name__ == '__main__':
    app.run(debug=True)
