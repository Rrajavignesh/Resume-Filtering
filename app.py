from flask import Flask,render_template,request

app = Flask(__name__)

@app.route('/')
@app.route('/register')
def home():
    return render_template('register.html')

@app.route('/confim',methods=['POST','GET'])
def confim():
    if request.method == 'POST':
        un = request.form['username']
        pw = request.form['password']
        cpw = request.form['confirm_password']
        return render_template('submit.html',username=un,password=pw,confirm_password=cpw)


if __name__ == '__main__':
    app.run(debug=True)