import os   # 用于数据库配置
import sys  # 用于数据库配置
import time
import click # 命令函数
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, flash
#用flask包导入Flask类
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy     # 导入扩展类
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager,login_user, login_required, logout_user, current_user, UserMixin

from AudioMixer import Mixer

WIN = sys.platform.startswith('win')
if WIN:  # 如果是 Windows 系统，使用三个斜线
    prefix = 'sqlite:///'
else:  # 否则使用四个斜线
    prefix = 'sqlite:////'

app = Flask(__name__)   #实例化Flask类，创建一个程序对象app

# 以下为配置文件
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path, 'data.db')   # 数据库地址
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭对模型修改的监控
app.config['SECRET_KEY'] = 'dev'  # 等同于 app.secret_key = 'dev' 为了flash函数

db = SQLAlchemy(app)    # 初始化扩展，传入程序实例app

login_manager = LoginManager(app)  # 实例化扩展类
login_manager.login_view = 'login' # 为了实现认证保护


# 以下为创建数据库模型
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)    #主键
    name = db.Column(db.String(20))                 #姓名
    username = db.Column(db.String(20))  # 用户名
    password_hash = db.Column(db.String(128))  # 密码散列值

    def set_password(self, password):  # 用来设置密码的方法，接受密码作为参数
        self.password_hash = generate_password_hash(password)  # 将生成的密码保持到对应字段

    def validate_password(self, password):  # 用于验证密码的方法，接受密码作为参数
        return check_password_hash(self.password_hash, password)  # 返回布尔值


class Movie(db.Model):  # 表名将会是 movie
    id = db.Column(db.Integer, primary_key=True)  # 主键
    title = db.Column(db.String(60))  # 电影标题
    year = db.Column(db.String(4))  # 电影年份

class Beat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))

@login_manager.user_loader
def load_user(user_id):  # 创建用户加载回调函数，接受用户 ID 作为参数
    user = User.query.get(int(user_id))  # 用 ID 作为 User 模型的主键查询对应的用户
    return user  # 返回用户对象


@app.cli.command()  # 注册为命令
@click.option('--drop', is_flag=True, help='Create after drop.')  # 设置选项
def initdb(drop):
    """Initialize the database."""
    if drop:  # 判断是否输入了选项
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.')  # 输出提示信息

# 因为有了数据库，我们可以编写一个命令函数把虚拟数据添加到数据库里。下面是用来生成虚拟数据的命令函数：
@app.cli.command()
def forge():
    """Generate fake data."""
    db.drop_all()
    db.create_all()

    # 全局的两个变量移动到这个函数内
    name = 'Zhu jiace'
    movies = [
        {'title': 'My Neighbor Totoro', 'year': '1988'},
        {'title': 'Dead Poets Society', 'year': '1989'},
        {'title': 'A Perfect World', 'year': '1993'},
        {'title': 'Leon', 'year': '1994'},
        {'title': 'Mahjong', 'year': '1996'},
        {'title': 'Swallowtail Butterfly', 'year': '1996'},
        {'title': 'King of Comedy', 'year': '1999'},
        {'title': 'Devils on the Doorstep', 'year': '1999'},
        {'title': 'WALL-E', 'year': '2008'},
        {'title': 'The Pork of Music', 'year': '2012'},
    ]

    user = User(name=name)
    db.session.add(user)
    for m in movies:
        movie = Movie(title=m['title'], year=m['year'])
        db.session.add(movie)

    beats = [
        {'name':'test1.wav'},
        {'name':'test2.wav'},
        {'name':'test3.wav'},
    ]
    for b in beats:
        beat = Beat(name=b['name'])
        db.session.add(beat)

    db.session.commit()
    click.echo('Done.')


@app.cli.command()
@click.option('--username', prompt=True, help='The username used to login.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='The password used to login.')
def admin(username, password):
    """Create user."""
    db.create_all()

    user = User.query.first()
    if user is not None:
        click.echo('Updating user...')
        user.username = username
        user.set_password(password)  # 设置密码
    else:
        click.echo('Creating user...')
        user = User(username=username, name='Admin')
        user.set_password(password)  # 设置密码
        db.session.add(user)

    db.session.commit()  # 提交数据库会话
    click.echo('Done.')

@app.context_processor  # 这个函数返回的变量（以字典键值对的形式）将会统一注入到每一个模板的上下文环境中，因此可以直接在模板中使用。
def inject_user():  # 函数名可以随意修改
    user = User.query.first()
    return dict(user=user)  # 需要返回字典，等同于 return {'user': user}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Invalid input.')
            return redirect(url_for('login'))

        user = User.query.first()
        # 验证用户名和密码是否一致
        if username == user.username and user.validate_password(password):
            login_user(user)  # 登入用户
            flash('Login success.')
            return redirect(url_for('index'))  # 重定向到主页

        flash('Invalid username or password.')  # 如果验证失败，显示错误消息
        return redirect(url_for('login'))  # 重定向回登录页面

    return render_template('login.html')

@app.route('/logout')
@login_required  # 用于视图保护，后面会详细介绍
def logout():
    logout_user()  # 登出用户
    flash('Goodbye.')
    return redirect(url_for('index'))  # 重定向回首页


@app.route('/', methods=['GET', 'POST'])    # 视图函数 用装饰器app.route为函数绑定URL
def index():
    if request.method == 'POST':  # 判断是否是 POST 请求
        if not current_user.is_authenticated:  # 如果当前用户未认证
            return redirect(url_for('index'))  # 重定向到主页
        # 获取表单数据
        title = request.form.get('title')  # 传入表单对应输入字段的 name 值
        year = request.form.get('year')
        # 验证数据
        if not title or not year or len(year) > 4 or len(title) > 60:
            flash('Invalid input.')  # 显示错误提示
            return redirect(url_for('index'))  # 重定向回主页
        # 保存表单数据到数据库

        movie = Movie(title=title, year=year)  # 创建记录
        db.session.add(movie)  # 添加到数据库会话
        db.session.commit()  # 提交数据库会话
        flash('Item created.')  # 显示成功创建的提示
        return redirect(url_for('index'))  # 重定向回主页

    movies = Movie.query.all()
    return render_template('index.html', movies=movies)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form['name']

        if not name or len(name) > 20:
            flash('Invalid input.')
            return redirect(url_for('settings'))

        current_user.name = name
        # current_user 会返回当前登录用户的数据库记录对象
        # 等同于下面的用法
        # user = User.query.first()
        # user.name = name
        db.session.commit()
        flash('Settings updated.')
        return redirect(url_for('index'))

    return render_template('settings.html')

@app.errorhandler(404)  # 传入要处理的错误代码
def page_not_found(e):  # 接受异常对象作为参数
    return render_template('404.html'), 404  # 返回模板和状态码


@app.route('/movie/edit/<int:movie_id>', methods=['GET', 'POST'])
@login_required  # 用于视图保护
def edit(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    if request.method == 'POST':  # 处理编辑表单的提交请求
        title = request.form['title']
        year = request.form['year']

        if not title or not year or len(year) != 4 or len(title) > 60:
            flash('Invalid input.')
            return redirect(url_for('edit', movie_id=movie_id))  # 重定向回对应的编辑页面

        movie.title = title  # 更新标题
        movie.year = year  # 更新年份
        db.session.commit()  # 提交数据库会话
        flash('Item updated.')
        return redirect(url_for('index'))  # 重定向回主页

    return render_template('edit.html', movie=movie)  # 传入被编辑的电影记录


@app.route('/movie/delete/<int:movie_id>', methods=['POST'])  # 限定只接受 POST 请求
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id)  # 获取电影记录
    db.session.delete(movie)  # 删除对应的记录
    db.session.commit()  # 提交数据库会话
    flash('Item deleted.')
    return redirect(url_for('index'))  # 重定向回主页




#上传文件（成功）
# @app.route('/upload', methods=['POST', 'GET'])
# def upload():
#     if request.method == 'POST':
#         f = request.files['file']
#         basepath = os.path.dirname(__file__)  # 当前文件所在路径
#         upload_path = os.path.join(basepath, 'static\\uploads', secure_filename(f.filename))  #注意：没有的文件夹一定要先创建，不然会提示没有该路径
#         f.save(upload_path)
#         return redirect(url_for('upload'))
#     return render_template('upload.html')

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # 设置文件上传的目标文件夹
basedir = os.path.abspath(os.path.dirname(__file__))  # 获取当前项目的绝对路径
ALLOWED_EXTENSIONS = set(['txt', 'png', 'jpg', 'xls', 'JPG', 'PNG', 'xlsx', 'gif', 'GIF', 'wav'])  # 允许上传的文件后缀

BEATS_FOLDER = 'static/beats'
app.config['BEATS_FOLDER'] = BEATS_FOLDER

OUT_FOLDER = 'static/Mixed'
app.config['OUT_FOLDER'] = OUT_FOLDER

# 判断文件是否合法
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# 具有上传功能的页面
@app.route('/test/upload')
def upload_test():
    beats=Beat.query.all()
    return render_template('upload2.html',beats=beats)

@app.route('/api/upload', methods=['POST'], strict_slashes=False)
def api_upload():
    beats=Beat.query.all()
    file_dir = os.path.join(basedir, app.config['UPLOAD_FOLDER'])  # 拼接成合法文件夹地址
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)  # 文件夹不存在就创建
    f=request.files['myfile']  # 从表单的file字段获取文件，myfile为该表单的name值
    b=request.form.get('beat')
    if f and allowed_file(f.filename):  # 判断是否是允许上传的文件类型
        fname=f.filename
        ext = fname.rsplit('.', 1)[1]  # 获取文件后缀
        unix_time = int(time.time())
        new_filename = str(unix_time)+'.'+ext   # 修改文件名
        filepath1 = os.path.join(file_dir, new_filename)
        f.save(filepath1)  #保存文件到upload目录
        

        beats_folder = os.path.join(basedir, app.config['BEATS_FOLDER'])
        filepath2 = os.path.join(beats_folder, b)
        flash(filepath2)

        mixed_name = 'mixed.' + ext
        mixed_folder = os.path.join(basedir, app.config['OUT_FOLDER'])
        filepath3 = os.path.join(mixed_folder, mixed_name)
        flash(filepath3)

        Mixer(filepath1,filepath2,filepath3)

        flash("上传成功")
        #return render_template('upload2.html',beats=beats)
        return redirect(url_for('downloader',filename='mixed.wav'))
        # return jsonify({"errno": 0, "errmsg": "上传成功"})
        
    else:
        flash("上传失败")
        return render_template('upload2.html',beats=beats)
        # return jsonify({"errno": 1001, "errmsg": "上传失败"})

#文件下载
@app.route("/download/<path:filename>")
def downloader(filename):
    dirpath = os.path.join(app.root_path, 'static/Mixed')  # 这里是下在目录，从工程的根目录写起，比如你要下载static/js里面的js文件，这里就要写“static/js”
    return send_from_directory(dirpath, filename, as_attachment=True)  # as_attachment=True 一定要写，不然会变成打开，而不是下载