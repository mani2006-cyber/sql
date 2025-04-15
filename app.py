from flask import Flask, render_template, request, url_for,jsonify
app = Flask(__name__)

content = [{
    'name': 'John Doe',
    'email': 'john.doe@example.com',
    'phone': '123-456-7890',
    'address': 's. chintamani ,nagar, hyderabad, telangana, 500049'
}]

@app.route('/')
def index():
    return render_template('index.html' ,content = content)

@app.route('/jobs')
def jobs():
    return jsonify(content)
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
