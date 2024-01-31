from celery import Celery
import smol_podcaster

app = Celery('tasks')
app.config_from_object('celeryconfig')

@app.task
def run_smol_podcaster(url, name, speakers):
    results = smol_podcaster.main(url, name, speakers)
    
    return "The path was: " + results