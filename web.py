from flask import Flask, request, render_template, redirect, url_for
from tasks import run_smol_podcaster, run_video_chapters
import os
import re
import logging
from datetime import datetime
import tempfile
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.logger.setLevel(logging.INFO)

@app.route('/')
def index():
    podcast_results_dir = './podcasts-results'  # Updated directory path
    episodes = []
    
    if os.path.exists(podcast_results_dir):
        for filename in os.listdir(podcast_results_dir):
            if filename.startswith('substack_') and filename.endswith('.md'):
                file_path = os.path.join(podcast_results_dir, filename)
                episode_name = filename[len('substack_'):-3]  # Remove 'substack_' prefix and '.md' suffix
                creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                episodes.append({
                    'name': episode_name,
                    'created_at': creation_time,
                    'created_at_formatted': creation_time.strftime("%b %-d"),
                    'edit_url': url_for('edit_show_notes', episode_name=episode_name)
                })
    
    # Sort episodes by creation time, most recent first
    episodes.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('index.html', episodes=episodes)

@app.route('/process', methods=['POST'])
def process_form():
    file_input = request.files.get('file_input')
    url = request.form.get('url')
    speakers = int(request.form.get('speakers'))
    name = request.form.get('name')
    
    transcript_only = bool(request.form.get('transcript-only'))
    generate_extra = bool(request.form.get('generate-extra'))
    
    app.logger.info(f"Transcript Only: {transcript_only}")
    
    if file_input and file_input.filename:
        # Save the uploaded file to a temporary location
        _, file_extension = os.path.splitext(file_input.filename)
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, secure_filename(f"upload_{name}{file_extension}"))
        file_input.save(temp_file_path)
        file_or_url = temp_file_path
    else:
        file_or_url = url
    
    run_smol_podcaster.delay(file_or_url, name, speakers, transcript_only, generate_extra)
    
    return render_template('index.html', confirmation=(f"Now processing {name}"))

@app.route('/sync_chapters', methods=['POST'])
def sync_chapters():
    video_name = request.form.get('video_name')
    audio_name = request.form.get('audio_name')
    chapters = request.form.get('chapters')
    
    app.logger.info(f"Syncing chapters for {video_name} and {audio_name}")
    # Call the `update_video_chapters` function with the provided parameters
    task = run_video_chapters.delay(chapters, audio_name, video_name)
    
    app.logger.info(f"Task ID: {task.id}")
    
    return render_template('index.html', confirmation=(f"Syncing chapters for {video_name} and {audio_name}"))

@app.route('/edit/<episode_name>', methods=['GET', 'POST'])
def edit_show_notes(episode_name):
    file_path = os.path.join('./podcasts-results', f'substack_{episode_name}.md')
    
    if request.method == 'POST':
        # Handle form submission and save changes
        updated_items = []
        for key, value in request.form.items():
            if key.startswith('item_'):
                item_id = key.split('_')[1]
                url = request.form.get(f'url_{item_id}', '')
                if value:
                   updated_items.append((value, url))
        
        # Update the file content
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Find the show notes section and replace it
        show_notes_pattern = r'### Show Notes.*?(?=### Timestamps)'
        updated_show_notes = "### Show Notes\n" + "\n".join([f"- {item[0]}" if not item[1] else f"- [{item[0]}]({item[1]})" for item in updated_items])
        updated_content = re.sub(show_notes_pattern, updated_show_notes, content, flags=re.DOTALL)
        
        # Write the updated content back to the file
        with open(file_path, 'w') as file:
            file.write(updated_content)
        
        return redirect(url_for('index'))
    
    # Read the current show notes
    with open(file_path, 'r') as file:
        content = file.read()
    
    # Extract the show notes items
    show_notes_pattern = r'### Show Notes(.*?)(?=### Timestamps)'
    show_notes_match = re.search(show_notes_pattern, content, re.DOTALL)
    if show_notes_match:
        show_notes = show_notes_match.group(1).strip()
        items = re.findall(r'^-\s*(?:\[([^\]]+)\]\(([^)]+)\)|(.+))$', show_notes, re.MULTILINE)
        items = [(item[0] or item[2], item[1] or '') for item in items]
    else:
        items = []
    
    return render_template('edit_show_notes.html', episode_name=episode_name, items=items)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))