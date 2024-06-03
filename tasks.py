from celery import Celery
import smol_podcaster

app = Celery('tasks')
app.config_from_object('celeryconfig')

@app.task
def run_smol_podcaster(url, name, speakers, transcript_only):
    results = smol_podcaster.main(url, name, speakers, transcript_only)
    
    return "The path was: " + results

@app.task
def run_video_chapters(video_name, audio_name, chapters):
    results = smol_podcaster.update_video_chapters(video_name, audio_name, chapters)
    
    return "The path was: " + results