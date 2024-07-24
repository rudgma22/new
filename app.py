from flask import Flask
from views import views_bp
from auth import auth_bp

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.register_blueprint(views_bp, url_prefix='/')
app.register_blueprint(auth_bp, url_prefix='/auth')

if __name__ == '__main__':
    app.run(debug=True)
