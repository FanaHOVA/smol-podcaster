from flask import Flask, request, render_template
from tasks import run_smol_podcaster, run_video_chapters
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

@app.route('/sync_chapters', methods=['POST'])
def sync_chapters():
    video_name = request.form.get('video_name')
    audio_name = request.form.get('audio_name')
    chapters = request.form.get('chapters')
    
    # Call the `update_video_chapters` function with the provided parameters
    run_video_chapters.delay(video_name, audio_name, chapters)
    
    return render_template('index.html', confirmation=(f"Chapters synced for {video_name} and {audio_name}"))


if __name__ == '__main__':
    app.run(debug=True)