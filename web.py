from flask import Flask, request, render_template
from tasks import run_smol_podcaster
import logging

app = Flask(__name__)

app.logger.setLevel(logging.INFO)

@app.route('/')
def index():
    return render_template('index.html')
  
@app.route('/process', methods=['POST'])
def process_form():
    url = request.form.get('url')
    speakers = int(request.form.get('speakers'))
    name = request.form.get('name')
    
    # Check if the checkboxes are checked, but transforming into bool because
    # the checkbox passes `on`, but blank is None
    transcript_only = True if request.form.get('transcript-only') else False
    
    app.logger.info(f"Transcript Only: {transcript_only}")
    
    run_smol_podcaster.delay(url, name, speakers, transcript_only)
    
    return render_template('index.html', confirmation=(f"Now processing {name}"))

if __name__ == '__main__':
    app.run(debug=True)