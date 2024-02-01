from flask import Flask, request, render_template
from tasks import run_smol_podcaster

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')
  
@app.route('/process', methods=['POST'])
def process_form():
    url = request.form.get('url')
    speakers = int(request.form.get('speakers'))
    name = request.form.get('name')
  
    run_smol_podcaster.delay(url, name, speakers)
    
    return render_template('index.html', confirmation=(f"Now processing {name}"))

if __name__ == '__main__':
    app.run(debug=True)