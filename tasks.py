from celery.utils.log import get_task_logger

from celery import Celery
import smol_podcaster

logger = get_task_logger(__name__)

app = Celery('tasks')
app.config_from_object('celeryconfig')

@app.task
def run_smol_podcaster(url, name, speakers, transcript_only, generate_extra):
    logger.info(f"Running smol_podcaster for {name}")
    results = smol_podcaster.main(url, name, speakers, transcript_only, generate_extra)
    
    logger.info(f"Results for {name}: {results}")
    return "The path was: " + results

@app.task
def run_video_chapters(chapters, audio_name, video_name):
    logger.info(f"Updating video chapters for {audio_name}")
    results = smol_podcaster.update_video_chapters(chapters, audio_name, video_name)
    
    logger.info(f"Updated video chapters for {audio_name}: {results}")
    return "The path was: " + results

