import argparse
import requests
import logging
import Levenshtein

from dotenv import load_dotenv
import os
import re
import json

import replicate
from openai import OpenAI
from anthropic import Anthropic

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL") or "claude-3-5-sonnet-20240620"
GPT_MODEL = os.environ.get("GPT_MODEL") or "gpt-4o-2024-08-06"

# common ML words that the replicate model doesn't know, can programatically update the transcript
fix_recording_mapping = {
    "noose": "Nous",
    "Dali": "DALL·E",
    "Swyggs": "Swyx",
    " lama ": " Llama "
}

def call_anthropic(prompt, temperature=0.5):   
    try:
        anthropic = Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )
            
        request = anthropic.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=3000,
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )
        
        return request.content[0].text
    except Exception as e:
        return f"An error occured with Claude: {e}"

def call_openai(prompt, temperature=0.5):
    try:
        result = client.chat.completions.create(model=GPT_MODEL,
        temperature=temperature,
        messages=[
            {"role": "user", "content": prompt}
        ])
        return result.choices[0].message.content
    except OpenAI.BadRequestError as e:
        error_msg = f"An error occurred with OpenAI: {e}"
        print(error_msg)
        return error_msg

def transcribe_audio(file_url, episode_name, speakers_count):
    # Check if the URL is from Dropbox and replace the domain
    file_url = re.sub(r"https?:\/\/(www\.)?dropbox\.com", "https://dl.dropboxusercontent.com", file_url)

    print(f"Running smol-podcaster on {file_url}")

    output = replicate.run(
        "thomasmol/whisper-diarization:7e5dafea13d80265ea436e51a310ae5103b9f16e2039f54de4eede3060a61617",
        input={
            "file_url": file_url,
            "num_speakers": speakers_count,
            "prompt": "Audio of Latent Space, a technical podcast about artificial intelligence and machine learning hosted by Swyx and Alessio."
        }
    )
    # if directory doesn't exist
    if not os.path.exists("./podcasts-raw-transcripts"):
        os.makedirs("./podcasts-raw-transcripts")
        
    with open(f"./podcasts-raw-transcripts/{episode_name}.json", "w") as f:
        json.dump(output, f)

    return output['segments']

def process_transcript(transcript, episode_name):
    """
    {
        "end": "3251",
        "text": " This was great.  Yeah, this has been really fun.",
        "start": "3249",
        "speaker": "SPEAKER 1"
    }
        
    The transcript argument of this function is an array of these. 
    """
    transcript_strings = []
    
    for entry in transcript:
        speaker = entry["speaker"]
        text = entry["text"]
        
        # replace each word in fix_recording_mapping with the correct word
        for key, value in fix_recording_mapping.items():
            text = text.replace(key, value)

        # Convert "end" value to seconds and convert to hours, minutes and seconds
        seconds = int(float(entry["start"]))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        timestamp = "[{:02d}:{:02d}:{:02d}]".format(hours, minutes, seconds)

        transcript_strings.append(f"**{speaker}** {timestamp}: {text}")
        
    clean_transcript = "\n\n".join(transcript_strings)
    
    with open(f"./podcasts-clean-transcripts/{episode_name}.md", "w") as f:    
        f.write(clean_transcript)
        
    return clean_transcript

# They just need a txt with all text, it will then sync it automatically
def process_youtube_transcript(parts, episode_name):
    formatted_transcriptions = []

    for part in parts:
        formatted_transcriptions.append(part['text'].strip())
            
    with open(f"./podcasts-results/{episode_name}-yt-subtitles.txt", "w") as file:
        file.writelines("\n".join(formatted_transcriptions))

def create_chapters(transcript):
    prompt = f"I'm going to give you a podcast transcript with timestamps for each speaker section in this format: `SPEAKER: Some transcription [00:00:00]`. Generate a list of all major topics covered in the podcast, and the timestamp where the discussion starts. Make sure to use the timestamp BEFORE the the discussion starts. Make sure to cover topics from the whole episode. Use this format: `- [00:00:00] Topic name`. Here's the transcript: \n\n {transcript}"
    
    claude_suggestions = call_anthropic(prompt, 0.6)
    gpt_suggestions = call_openai(prompt, 0.6)
    
    return "\n".join([claude_suggestions, gpt_suggestions])

def clips_picker(transcript):
    prompt = f"I'm about to release my new video podcast and I want to create four 60 second clips for YouTube Shorts. Can you suggest 7-8 passages that would make for good clips and their rough timestamps? They are usually very insightful, funny, or controversial parts of the discussion. Here's the transcript: \n\n {transcript}"
    
    claude_suggestions = call_anthropic(prompt, 0.5)
    gpt_suggestions = call_openai(prompt, 0.5)

    return "\n".join([claude_suggestions, gpt_suggestions])

def create_show_notes(transcript):
    prompt = f"I'll give you a podcast transcript; help me create a list of every company, person, project, research paper, or any other named entitiy that you find in it. Return it as a markdown list. If it references a company or person that you know, add a link to their website or online profile. Here's the transcript: \n\n {transcript}"
    
    claude_suggestions = call_anthropic(prompt, 0.4)
    gpt_suggestions = call_openai(prompt, 0.4)

    return "\n".join([claude_suggestions, gpt_suggestions])

def create_writeup(transcript):
    prompt = f"You're the writing assistant of a podcast producer. For each episode, we do a write up to recap the core ideas of the episode and expand on them. Write a list of bullet points on topics we should expand on, and then 4-5 paragraphs about them. Here's the transcript: \n\n {transcript}"
    
    claude_suggestions = call_anthropic(prompt, 0.7)
    gpt_suggestions = call_openai(prompt, 0.7)

    return "\n".join([claude_suggestions, gpt_suggestions])

def title_suggestions(writeup):
    prompt = f"""
    These are some titles of previous podcast episodes we've published:

    1. "From RLHF to RLHB: The Case for Learning from Human Behavior"
    2. "Commoditizing the Petaflop"
    3. "Llama 2: The New Open LLM SOTA"
    4. "FlashAttention 2: making Transformers 800\%\ faster w/o approximation"
    5. "Mapping the future of *truly* Open Models and Training Dolly for $30"
    6. "Beating GPT-4 with Open Source LLMs"
    7. "Why AI Agents Don't Work (yet)"
    8. "The End of Finetuning"

    Here's a write up of the latest podcast episode; suggest 8 title options for it that will be just as successful in catching the readers' attention:
    
    {writeup}
    """
    
    gpt_suggestions = call_openai(prompt, 0.7)
    claude_suggestions = call_anthropic(prompt)

    suggestions = f"\n\nGPT-4 title suggestions:\n\n{gpt_suggestions}\n\nClaude's title suggestions:\n{claude_suggestions}\n\n"

    return suggestions
    
def tweet_suggestions(transcript):
    prompt = f"""
    Here's a transcript of our latest podcast episode; suggest 8 tweets to share it on social medias.
    It should include a few bullet points of the most interesting topics. Our audience is technical.
    Use a writing style between Hemingway's and Flash Fiction. 
    
    {transcript}
    """
    
    gpt_suggestions = call_openai(prompt, 0.7)
    claude_suggestions = call_anthropic(prompt, 0.7)
    
    suggestions = f"GPT-4 tweet suggestions:\n{gpt_suggestions}\n\nClaude's tweet suggestions:\n{claude_suggestions}\n"
    
    return suggestions

def upload_file_and_use_url(file_path):
    """
    Uploads a file to the temporary file hosting service and prints the downloadable file URL.

    Parameters:
    - file_path: The local path to the file you want to upload.

    Returns:
    The URL of the uploaded file.
    """
    # check if url is file with os, upload to tmpfiles if is
    if os.path.exists(file_path):
        print("Uploading local file to send to API.")
        upload_url = 'https://tmpfiles.org/api/v1/upload'
        # Open the file in binary mode
        with open(file_path, 'rb') as file:
            # The 'files' parameter takes a dictionary with the form field name as the key
            # and a tuple with filename and file object (or content) as the value.
            files = {'file': (file_path, file)}
            response = requests.post(upload_url, files=files)
            
            # Check if the file was uploaded successfully
            if response.status_code == 200:
                # Assuming the API returns a JSON response with the URL of the uploaded file
                # under a key named 'url'. Adjust the key as per the actual API response.
                file_url = response.json()
                print(f"File uploaded successfully. URL: {file_url}")
                # convert url by adding dl/ after https://tmpfiles.org/
                return file_url['data']['url'].replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
            else:
                print("Failed to upload the file. Please check the error and try again.")
                return None
    else:
        print("Using file at remote URL.")
        return file_path

def update_video_chapters(audio_chapters, audio_file_name, video_file_name):
    video_transcript_path = f"./podcasts-clean-transcripts/{video_file_name}.md"
    audio_transcript_path = f"./podcasts-clean-transcripts/{audio_file_name}.md"

    with open(video_transcript_path, "r") as f:
        video_transcript = f.read()

    with open(audio_transcript_path, "r") as f:
        audio_transcript = f.read()
        
    logging.info(f"Updating video chapters for {audio_file_name}")

    updated_chapters = []

    for chapter in audio_chapters.split("\n"):
        if chapter.strip() == "":
            continue

        timestamp, topic = chapter.split("]", 1)
        timestamp = timestamp.strip("[]").strip()

        # Find the corresponding segment in the audio transcript
        # We go over every individual timestamps
        audio_segment = None
        for segment in audio_transcript.split("\n"):
            if timestamp.strip() in segment.strip():
                audio_segment = segment
                break

        if audio_segment is not None:
            # Find the closest matching segment in the video transcript
            closest_segment = None
            min_distance = float("inf")
            for segment in video_transcript.split("\n"):
                distance = Levenshtein.distance(segment, audio_segment)
                
                if distance < min_distance:
                    min_distance = distance
                    closest_segment = segment

            if closest_segment is not None:
                video_seconds = closest_segment.split("]")[0]

                updated_chapters.append(f"[{video_seconds.split('[')[1]}] {topic}")
            else:
                updated_chapters.append(f"Couldn't find a match for {timestamp}")
        else:
            updated_chapters.append(f"Couldn't find a match for {timestamp}")

    spaced = "\n".join(updated_chapters)
    
    logging.info(f"Updated video chapters for {audio_file_name}: {spaced}")
    
    substack_file_path = f"./podcasts-results/substack_{audio_file_name}.md"

    with open(substack_file_path, "r") as f:
        existing_content = f.read()

    updated_content = "\n".join(updated_chapters) + "\n\n" + existing_content

    with open(substack_file_path, "w") as f:
        f.write(updated_content)
        
    return spaced
    

def main(url, name, speakers_count, transcript_only, generate_extra): 
    raw_transcript_path = f"./podcasts-raw-transcripts/{name}.json"
    clean_transcript_path = f"./podcasts-clean-transcripts/{name}.md"
    results_file_path = f"./podcasts-results/{name}.md"
    substack_file_path = f"./podcasts-results/substack_{name}.md"
    youtube_subs_path = f"./podcasts-results/{name}-yt-subtitles.srt"
    
    # These are probably not the most elegant solutions, but they 
    # help with saving time since transcriptions are the same but we
    # might want to tweak the other prompts for better results.
    
    print('Starting transcription')
    
    # function that uploads if it is a file, or just returns the url
    if not os.path.exists(raw_transcript_path):
        url = upload_file_and_use_url(url)
        transcript = transcribe_audio(url, name, speakers_count)
    else:
        file = open(raw_transcript_path, "r").read()
        transcript = json.loads(file)['segments']
        
    print("Raw transcript is ready")
    
    if not os.path.exists(youtube_subs_path):
        process_youtube_transcript(transcript, name)
    
    print("YouTube subtitles generated")
    
    if not os.path.exists(clean_transcript_path):
        transcript = process_transcript(transcript, name)
    else:
        transcript = open(clean_transcript_path, "r").read()
        
    print("Clean transcript is ready")

    if transcript_only:
        return
    
    chapters = create_chapters(transcript)
    
    print(chapters)
    
    print("Chapters are ready")
    
    show_notes = create_show_notes(transcript)
    
    print("Show notes are ready")
    
    clips_picker(transcript)
    
    print("Clips are ready")
    
    writeup = create_writeup(transcript)
    
    print("Writeup is ready")
    
    if generate_extra:
        title_suggestions_str = title_suggestions(writeup)
    
        print("Titles are ready")
        
        tweet_suggestions_str = tweet_suggestions(transcript)
        
        print("Tweets are ready")

    with open(results_file_path, "w") as f:
        f.write("Chapters:\n")
        f.write(chapters)
        f.write("\n\n")
        f.write("Writeup:\n")
        f.write(writeup)
        f.write("\n\n")
        f.write("Show Notes:\n")
        f.write(show_notes)
        f.write("\n\n")
        
        if generate_extra:
            f.write("Title Suggestions:\n")
            f.write(title_suggestions_str)
            f.write("\n\n")
            f.write("Tweet Suggestions:\n")
            f.write(tweet_suggestions_str)
            f.write("\n")
        
    with open(substack_file_path, "w") as f:
        f.write("### Show Notes\n")
        f.write(show_notes)
        f.write("\n\n")
        f.write("### Timestamps\n")
        f.write(chapters)
        f.write("\n\n")
        f.write("### Transcript\n")
        
        # This is a fair compromise between open source usability while being the easiest for me, sorry reader
        if "Alessio" in transcript:
            f.write("**Alessio** [00:00:00]: Hey everyone, welcome to the Latent Space podcast. This is Alessio, partner and CTO-in-Residence at [Decibel Partners](https://decibel.vc), and I'm joined by my co-host Swyx, founder of [Smol AI](https://smol.ai).")
        
        f.write(transcript)
    
    print(f"Results written to {results_file_path}")
    
    return results_file_path
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe the podcast audio from an URL like tmpfiles.")
    parser.add_argument("url", help="The URL of the podcast to be processed.")
    parser.add_argument("name", help="The name of the output transcript file without extension.")
    parser.add_argument("speakers", help="The number of speakers on the track.", default=3)
    parser.add_argument("--transcript_only", help="Whether to only generate the transcript.", default=False, nargs='?')
    parser.add_argument("--generate_extra", help="Whether to generate extra content like titles and tweets.", default=False, nargs='?')
    args = parser.parse_args()

    url = args.url
    name = args.name
    speakers_count = int(args.speakers)
    transcript_only = args.transcript_only
    generate_extra = args.generate_extra
    
    main(url, name, speakers_count, transcript_only, generate_extra)

