from flask import Flask, render_template, flash, redirect, url_for, session,  request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import requests, datetime
from flask_weasyprint import HTML, render_pdf


app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
app.config['MYSQL_DB'] = 'librarymanagement'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

response = requests.get("https://frappe.io/api/method/frappe-library")
raw_data = response.json()
keys = []
data = []
new_list = []
author_list = []
for value in raw_data.values():
    for x in value:
        data.append(x)
for title in data:
    new_list.append(title['title'])
    keys.append(title['title'])


for author in data:
    author_list.append(author['authors'])

    keys.append(author['authors'])
data_len = len(data)



@app.route('/')
def index():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM books")

    books = cur.fetchall()

    cur.close()
    return render_template('home.html', books=books, data=data)





class RegisterForm(Form):
    username = StringField('Username', [validators.Length(min=3, max=30)])
    email = StringField('Email', [validators.Length(min=8, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match!')
    ])
    confirm = PasswordField('Confirm Password')



@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO users(username, email, password) VALUES(%s, %s, %s)", (username, email, password))

        mysql.connection.commit()

        cur.close()

        flash('You Have Registered Successfully :-)', 'success')

        return redirect(url_for('index'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_user = request.form['password']


        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM users WHERE username= %s", [username])

        if result > 0:
            data = cur.fetchone()
            password = data['password']

            if sha256_crypt.verify(password_user, password):
                session['logged_in'] = True
                session['username'] = username

                return redirect(url_for('home'))
            else:
                error = 'Invalid Password'
                return render_template('login.html', error=error)
            cur.close()
        else:
            error = 'Invalid Username'
            return render_template('login.html', error=error)

    return render_template('login.html')


def check_login(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Please login to continue!!', 'danger')
            return redirect(url_for('login'))

    return wrap


@app.route('/search', methods=['GET', 'POST'])
@check_login
def search(data=data):
    cur = mysql.connection.cursor()

    result_key = cur.execute("SELECT * FROM books")

    books_key = cur.fetchall()
    for key in books_key:
        keys.append(key['title'])
        keys.append(key['author'])

    cur.close()
    if request.method == 'POST':
        search_key = request.form['search']

        if (search_key in author_list) or (search_key in new_list):
            if search_key in author_list:
                data_index = author_list.index(search_key)
                data_new = data[data_index]
            else:
                data_index = new_list.index(search_key)
                data_new = data[data_index]
            title = data_new['title']
            author = data_new['authors']
            return render_template('result.html', title=title, author=author)

        else:
            cur = mysql.connection.cursor()
            result = cur.execute("SELECT * FROM books WHERE title = %s OR author =%s", [search_key,search_key])

            if result > 0:
                data = cur.fetchone()
                title = data['title']
                author = data['author']


                return render_template('result.html', title=title, author=author)
                cur.close()
            else:
                flash('No books found', 'danger')
                return redirect(url_for('search'))

    return render_template('search.html', keys=keys)





@app.route('/home')
@check_login
def home():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM books")

    books = cur.fetchall()


    return render_template('home.html', books=books, data=data)


    cur.close()


class BookForm(Form):
    bookid = StringField('BookId', [validators.Length(min=1,max=100)])
    title = StringField('Title', [validators.Length(min=1, max=200)])
    author = StringField('Author', [validators.Length(min=1, max=200)])
    isbn = StringField('ISBN', [validators.Length(min=1, max=200)])
    isbn13 = StringField('ISBN13', [validators.Length(min=1, max=200)])
    language_code = StringField('LanguageCode', [validators.Length(min=1, max=200)])
    availability = StringField('Availability', [validators.Length(min=1, max=200)])


@app.route('/books')
@check_login
def books():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM books")

    books = cur.fetchall()

    if result > 0:
        return render_template('books.html', books=books, data=data)
    else:
        msg = 'No Books Found'
        return render_template('books.html', msg=msg)

    cur.close()

@app.route('/book/<string:title>/')
@check_login
def book(title):

    if title in new_list:
        data_index = new_list.index(title)
        data_new = data[data_index]
        return render_template('book.html', data=data_new, index=data_index, list=new_list, check=title)
    else:
        cur = mysql.connection.cursor()

        result = cur.execute("SELECT * FROM books WHERE title LIKE %s", [title])

        book = cur.fetchone()

        cur.close()
        return render_template('book.html', book=book)



@app.route('/add_book', methods=['GET', 'POST'])
@check_login
def add_book():
    form = BookForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        bookid = form.bookid.data
        author = form.author.data
        isbn = form.isbn.data
        isbn13 = form.isbn13.data
        language_code = form.language_code.data
        availability = form.availability.data

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO books(bookid, title, author, isbn, isbn13, language_code, availability) VALUES(%s, %s, %s, %s, %s, %s, %s)", (bookid, title, author, isbn, isbn13, language_code, availability))

        mysql.connection.commit()

        cur.close()

        flash('Hurrah!! Book is added!', 'success')

        return redirect(url_for('books'))

    return render_template('add_book.html', form=form)

@app.route('/edit_book/<string:id>', methods=['GET', 'POST'])
@check_login
def edit_book(id):

    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM books WHERE id = %s", [id])

    book = cur.fetchone()
    cur.close()

    form = BookForm(request.form)

    form.bookid.data = book['bookid']
    form.title.data = book['title']
    form.author.data = book['author']
    form.isbn.data = book['isbn']
    form.isbn13.data = book['isbn13']
    form.language_code.data = book['language_code']
    form.availability.data = book['availability']

    if request.method == 'POST' and form.validate():
        bookid = request.form['bookid']
        title = request.form['title']
        author = request.form['author']
        isbn = request.form['isbn']
        isbn13 = request.form['isbn13']
        language_code = request.form['language_code']
        availability = request.form['availability']


        cur = mysql.connection.cursor()
        app.logger.info(title)

        cur.execute ("UPDATE books SET bookid=%s, title=%s, author=%s, isbn=%s, isbn13=%s, language_code=%s, availability=%s WHERE id=%s",(bookid, title, author, isbn, isbn13, language_code, availability, id))

        mysql.connection.commit()

        cur.close()

        flash('Book is Updated Succesfully!', 'success')

        return redirect(url_for('books'))

    return render_template('edit_book.html', form=form)

class BookEditForm(Form):
    bookid = StringField('BookId', [validators.Length(min=1,max=100)])
    title = StringField('Title', [validators.Length(min=1, max=200)])
    authors = StringField('Author', [validators.Length(min=1, max=200)])
    average_rating = StringField('Average Rating', [validators.Length(min=1, max=200)])
    isbn = StringField('ISBN', [validators.Length(min=1, max=200)])
    isbn13 = StringField('ISBN13', [validators.Length(min=1, max=200)])
    language_code = StringField('LanguageCode', [validators.Length(min=1, max=200)])
    ratings_count = StringField('Ratings Count', [validators.Length(min=1, max=200)])
    text_reviews_count = StringField('Text Reviews Count', [validators.Length(min=1, max=200)])
    publication_date = StringField('Publication Date', [validators.Length(min=1, max=200)])
    publisher = StringField('Publisher', [validators.Length(min=1, max=200)])
    availability = StringField('Availability', [validators.Length(min=1, max=200)])

@app.route('/edit_books/<string:title>', methods=['GET', 'POST'])
@check_login
def edit_books(title):

    data_index = new_list.index(title)
    book = data[data_index]

    form = BookEditForm(request.form)

    form.bookid.data = book['bookID']
    form.title.data = book['title']
    form.authors.data = book['authors']
    form.average_rating.data = book['average_rating']
    form.isbn.data = book['isbn']
    form.isbn13.data = book['isbn13']
    form.language_code.data = book['language_code']
    form.ratings_count.data = book['ratings_count']
    form.text_reviews_count.data = book['text_reviews_count']
    form.publication_date.data = book['publication_date']
    form.publisher.data = book['publisher']

    if request.method == 'POST' and form.validate():
        bookid = request.form['bookid']
        title = request.form['title']
        authors = request.form['authors']
        average_rating = request.form['average_rating']
        isbn = request.form['isbn']
        isbn13 = request.form['isbn13']
        language_code = request.form['language_code']
        ratings_count = request.form['ratings_count']
        text_reviews_count = request.form['text_reviews_count']
        publication_date = request.form['publication_date']
        publisher = request.form['publisher']
        availability = request.form['availability']

        book['bookID'] = bookid
        book['title'] = title
        book['authors'] = authors
        book['average_rating'] = average_rating
        book['isbn'] = isbn
        book['isbn13'] = isbn13
        book['language_code'] = language_code
        book['ratings_count'] = ratings_count
        book['text_reviews_count'] = text_reviews_count
        book['publication_date'] = publication_date
        book['publisher'] = publisher
        book['availability'] = availability


        flash('Book is Updated Succesfully!', 'success')

        return redirect(url_for('books'))

    return render_template('edit_books.html', form=form)

@app.route('/delete_book/<string:title>', methods=['POST'])
@check_login
def delete_book(title):

    if title in new_list:
        data_index = new_list.index(title)
        new_list.pop(title)
        data.pop(data_index)
    else:
        cur = mysql.connection.cursor()

        cur.execute("DELETE FROM books WHERE title LIKE %s", [title])

        mysql.connection.commit()

        cur.close()



    flash('The Book is Deleted.', 'success')

    return redirect(url_for('books'))





@app.route('/users')
@check_login
def users():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM users WHERE NOT username='admin'")

    users = cur.fetchall()

    if result > 0:
        return render_template('users.html', users=users)
    else:
        msg = 'No Users Found'
        return render_template('users.html', msg=msg)

    cur.close()



class UserForm(Form):

    issued = StringField('Books Issued', [validators.Length(min=0,max=100)])
    returned = StringField('Books Returned', [validators.Length(min=0,max=100)])
    dues = StringField('Dues', [validators.Length(min=0,max=100)])
    paid = StringField('Dues paid', [validators.Length(min=0,max=100)])


@app.route('/edit_user/<string:id>', methods=['GET', 'POST'])
@check_login
def edit_user(id):

    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM users WHERE id = %s ", [id])

    user = cur.fetchone()
    cur.close()

    form = UserForm(request.form)


    form.issued.data = user['issued']
    form.returned.data = user['returned']
    form.dues.data = user['dues']
    form.paid.data = user['paid']

    if request.method == 'POST' and form.validate():

        issued = request.form['issued']
        returned = request.form['returned']
        dues = request.form['dues']
        paid = request.form['paid']


        cur = mysql.connection.cursor()
        app.logger.info(paid)

        cur.execute("UPDATE users SET issued=%s, returned=%s, dues=%s, paid=%s WHERE id=%s", (issued, returned, dues, paid, id))

        mysql.connection.commit()

        cur.close()

        flash('User Data is Updated Succesfully!', 'success')

        return redirect(url_for('users'))

    return render_template('edit_user.html', form=form)

@app.route('/delete_user/<string:id>', methods=['POST'])
@check_login
def delete_user(id):

    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM users WHERE id = %s", [id])

    mysql.connection.commit()

    cur.close()

    flash('User is Deleted.', 'success')

    return redirect(url_for('users'))


@app.route('/details/<string:username>')
@check_login
def details(username):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM users WHERE  username LIKE %s ", [username])

    user = cur.fetchone()
    cur.close()

    return render_template('details.html', user=user)


class DetailsForm(Form):

    username = StringField('Username', [validators.Length(min=0,max=100)])
    email = StringField('Email', [validators.Length(min=0,max=100)])
    phone = StringField('Phone Number', [validators.Length(min=0,max=10)])


@app.route('/edit_details/<string:id>', methods=['GET', 'POST'])
@check_login
def edit_details(id):

    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM users WHERE id = %s ", [id])

    user = cur.fetchone()
    cur.close()

    form = DetailsForm(request.form)


    form.username.data = user['username']
    form.email.data = user['email']
    form.phone.data = user['phone']

    if request.method == 'POST' and form.validate():

        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']


        cur = mysql.connection.cursor()
        app.logger.info(phone)

        cur.execute("UPDATE users SET username=%s, email=%s, phone=%s WHERE id=%s", (username, email, phone, id))

        mysql.connection.commit()

        cur.close()

        flash('User Data is Updated Succesfully!', 'success')

        return redirect(url_for('home'))

    return render_template('edit_details.html', form=form)

class ChangePwdForm(Form):

    old_password = PasswordField('Old Password', [validators.Length(min=1, max=50)])
    new_password = PasswordField(' New Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match!')
    ])
    confirm = PasswordField('Confirm Password')

@app.route('/edit_pass/<string:id>', methods=['GET', 'POST'])
@check_login
def edit_pass(id):
    form = ChangePwdForm(request.form)
    if request.method == 'POST' and form.validate():

        password_user = form.old_password.data
        new_password = sha256_crypt.encrypt(str(form.new_password.data))


        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM users WHERE id= %s", [id])

        if result > 0:
            data = cur.fetchone()
            password = data['password']

            if sha256_crypt.verify(password_user, password):

                cur.execute("UPDATE users SET password=%s WHERE id=%s", (new_password, id))

                mysql.connection.commit()
                flash('Password is changes successfully!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid password!', 'danger')
                return redirect(url_for('home'))
            cur.close()
        else:
            flash('Error! Please try again after sometime.', 'danger')
            return redirect(url_for('home'))

    return render_template('edit_pass.html', form=form)

@app.route('/mybooks/<string:username>')
@check_login
def mybooks(username):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM issued WHERE  username LIKE %s ", [username])

    issue = cur.fetchall()

    cur.close()

    if result > 0:
        return render_template('mybooks.html', books=issue, result=result)
    else:
        return render_template('mybooks.html', result=result)



@app.route('/issue/<string:title>')
@check_login
def issue(title):

    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM users WHERE username LIKE %s ", [session['username']])

    user = cur.fetchone()

    if user['issued'] is None :
        book_issued = 0
    else:
        book_issued = int(user['issued'])
    cur.close()

    if title in new_list:
        data_index = new_list.index(title)
        data_new = data[data_index]
        book_title = data_new['title']
        book_author = data_new['authors']
        if 'availability' not in data_new.keys():
            data_new['availability'] = 0

        book_availability = int(data_new['availability'])

    else:
        cur = mysql.connection.cursor()

        result = cur.execute("SELECT * FROM books WHERE title LIKE %s ", [title])

        book = cur.fetchone()

        book_title = book['title']
        book_author = book['author']
        book_availability = int(book['availability'])
        cur.close()

    cur = mysql.connection.cursor()
    result1 = cur.execute("SELECT * FROM issued WHERE username LIKE %s",[session['username']])
    check = cur.fetchall()
    now = datetime.datetime.now()
    if book_availability > 0:
        if result1 > 0:
            for a in check:
                check_user = a['username']
                check_title = a['title']
                if session['username'] != check_user and title != check_title:
                    cur = mysql.connection.cursor()

                    cur.execute("INSERT INTO issued (username, title, author) VALUES(%s, %s, %s)", (session['username'], book_title, book_author))

                    mysql.connection.commit()

                    cur.execute("INSERT INTO report (username, title, issued_time) VALUES(%s, %s, %s)", (session['username'], book_title, now))

                    mysql.connection.commit()

                    cur.close()

                    book_availability -= 1
                    book_issued += 1
                    if title in new_list:
                        data_new['availability'] = book_availability

                    else:
                        cur = mysql.connection.cursor()

                        cur.execute("UPDATE books SET availability=%s WHERE title = %s", (book_availability, title))


                        mysql.connection.commit()

                        cur.close()


                    cur = mysql.connection.cursor()

                    cur.execute("UPDATE users SET issued=%s WHERE username = %s", (book_issued, session['username']))

                    mysql.connection.commit()

                    cur.close()

                    flash('The book is added successfully!!', 'success')

                    return redirect(url_for('home'))
                else:
                    flash('The book is already in your list','warning')
                    return redirect(url_for('home'))
        else:
            cur = mysql.connection.cursor()

            cur.execute("INSERT INTO issued (username, title, author) VALUES(%s, %s, %s)", (session['username'], book_title, book_author))

            mysql.connection.commit()

            cur.execute("INSERT INTO report (username, title, issued_time) VALUES(%s, %s, %s)", (session['username'], book_title, now))

            mysql.connection.commit()

            cur.close()

            book_availability -= 1
            book_issued += 1
            if title in new_list:
                data_new['availability'] = book_availability

            else:
                cur = mysql.connection.cursor()

                cur.execute("UPDATE books SET availability=%s WHERE title = %s", (book_availability, title))

                mysql.connection.commit()

                cur.close()

            cur = mysql.connection.cursor()

            cur.execute("UPDATE users SET issued=%s WHERE username = %s", (book_issued, session['username']))

            mysql.connection.commit()

            cur.close()

            flash('The book is added successfully!!', 'success')

            return redirect(url_for('home'))

    else:
        flash('The book is currently unavailable!!', 'danger')

        return redirect(url_for('home'))

@app.route('/delete_book_list/<string:title>', methods=['POST'])
@check_login
def delete_book_list(title):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM users WHERE username LIKE %s ", [session['username']])

    user = cur.fetchone()
    result1 = cur.execute("SELECT * FROM issued WHERE username LIKE %s ", [session['username']])
    return_data = cur.fetchone()
    username_old = return_data['username']
    title_old = return_data['title']

    issued_time = return_data['issued_time']

    if user['returned'] is None:
        book_returned = 0
    else:
        book_returned = int(user['returned'])
    if user['dues'] is None:
        due = 0
    else:
        due = int(user['dues'])
    cur.close()

    if title in new_list:
        data_index = new_list.index(title)
        data_new = data[data_index]
        book_availability = int(data_new['availability'])

    else:
        cur = mysql.connection.cursor()

        result = cur.execute("SELECT * FROM books WHERE title LIKE %s ", [title])

        book = cur.fetchone()

        book_availability = int(book['availability'])
        cur.close()

    now = datetime.datetime.now()
    dues = ((now - issued_time).days * 2)

    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM issued WHERE title = %s", [title])

    mysql.connection.commit()
    cur.close()
    cur = mysql.connection.cursor()
    cur.execute("UPDATE report SET returned_time=%s, due=%s WHERE title = %s AND username = %s", (now, dues, title, session['username']))

    mysql.connection.commit()

    cur.close()

    book_availability += 1
    book_returned += 1

    due += ((now-issued_time).days * 2)
    if title in new_list:
        data_new['availability'] = book_availability
    else:
        cur = mysql.connection.cursor()

        cur.execute("UPDATE books SET availability=%s WHERE title = %s", (book_availability, title))

        mysql.connection.commit()

        cur.close()

    cur = mysql.connection.cursor()

    cur.execute("UPDATE users SET returned=%s, dues = %s WHERE username = %s", (book_returned, due, session['username']))

    mysql.connection.commit()

    cur.close()

    flash('The Book is Returned successfully!!', 'success')

    return redirect(url_for('home'))

@app.route('/report')
@check_login
def report():
    report_id = []

    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM report ")

    report = cur.fetchall()

    for b in report:
        issue_time = b['issued_time']
        return_time = b['returned_time']
        month_issue = issue_time.month
        year_issue = issue_time.year
        if return_time is not None:
            month_return = return_time.month
            year_return = return_time.year
        current_month = datetime.datetime.now().month
        current_year = datetime.datetime.now().year
        if (month_issue == current_month and year_issue ==current_year) or (year_return == current_year and month_return == current_year)  :
            report_id.append(b['id'])

    return render_template("reports.html", id=report_id, report=report)


@app.route('/download')
@check_login
def download():
    report_id = []

    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM report ")

    report = cur.fetchall()

    for b in report:
        issue_time = b['issued_time']
        return_time = b['returned_time']
        month_issue = issue_time.month
        year_issue = issue_time.year
        if return_time is not None:
            month_return = return_time.month
            year_return = return_time.year
        current_month = datetime.datetime.now().month
        current_year = datetime.datetime.now().year
        if (month_issue == current_month and year_issue ==current_year) or (year_return == current_year and month_return == current_year)  :
            report_id.append(b['id'])

    html = render_template("download.html", id=report_id, report=report)
    return render_pdf(HTML(string=html))

@app.route('/logout')
@check_login
def logout():
    session.clear()
    flash('You are successfully logged out', 'success')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)
