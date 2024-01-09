import argparse
import requests
from dotenv import load_dotenv
import os
import re
from datetime import datetime
import json

import replicate
import openai
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT

load_dotenv()

openai.api_key = os.environ.get("OPENAI_API_KEY")
anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def call_anthropic(prompt, temperature=0.5):
    try:
        anthropic = Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )
            
        request = anthropic.completions.create(
            model="claude-2",
            max_tokens_to_sample=3000,
            temperature=temperature,
            prompt=prompt,
        )
        
        return request.completion
    except:
        return "An error occured with Claude"

def call_openai(prompt, temperature=0.5):
    try:
        result = openai.ChatCompletion.create(
            model="gpt-4-1106-preview", 
            temperature=temperature,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return result.choices[0].message.content
    except openai.error.InvalidRequestError as e:
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

        # Convert "end" value to seconds and convert to hours, minutes and seconds
        seconds = int(float(entry["end"]))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        timestamp = "[{:02d}:{:02d}:{:02d}]".format(hours, minutes, seconds)

        transcript_strings.append(f"**{speaker}**: {text} {timestamp}")
        
    clean_transcript = "\n\n".join(transcript_strings)
    
    with open(f"./podcasts-clean-transcripts/{episode_name}.md", "w") as f:    
        f.write(clean_transcript)
        
    return clean_transcript
    
 
def create_chapters(transcript):
    prompt = f"I'm going to give you a podcast transcript with timestamps for each speaker section in this format: `SPEAKER: Some transcription [00:00:00]`. Generate a list of all major topics covered in the podcast, and the timestamp where the discussion starts. Make sure to use the timestamp BEFORE the the discussion starts. Make sure to cover topics from the whole episode. Use this format: `- [00:00:00] Topic name`. Here's the transcript: \n\n {transcript}"
    
    claude_suggestions = call_anthropic(prompt, 0.6)
    gpt_suggestions = call_openai(prompt, 0.6)
    
    return "\n".join([claude_suggestions, gpt_suggestions])

def create_show_notes(transcript):
    prompt = f"{HUMAN_PROMPT} I'll give you a podcast transcript; help me create a list of every company, person, project, or any other named entitiy that you find in it. Here's the transcript: \n\n {transcript} {AI_PROMPT}"
    
    return call_anthropic(prompt, 0.4)

def create_writeup(transcript):
    prompt = f"{HUMAN_PROMPT} You're the writing assistant of a podcast producer. For each episode, we do a write up to recap the core ideas of the episode and expand on them. Write a list of bullet points on topics we should expand on, and then 4-5 paragraphs about them. Here's the transcript: \n\n {transcript} {AI_PROMPT}",
    
    return call_anthropic(prompt, 0.7)

def title_suggestions(transcript):
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

    Here's a transcript of the latest podcast episode; suggest 8 title options for it that will be just as successful in catching the readers' attention:
    
    {transcript}
    """
    
    gpt_suggestions = call_openai(prompt, 0.7)
    claude_suggestions = call_anthropic(f"{HUMAN_PROMPT} {prompt} {AI_PROMPT}")

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
    claude_suggestions = call_anthropic(f"{HUMAN_PROMPT} {prompt} {AI_PROMPT}", 0.7)
    
    suggestions = f"GPT-4 tweet suggestions:\n{gpt_suggestions}\n\nClaude's tweet suggestions:\n{claude_suggestions}\n"
    
    return suggestions
    
def main():
    parser = argparse.ArgumentParser(description="Transcribe the podcast audio from an URL like tmpfiles.")
    parser.add_argument("url", help="The URL of the podcast to be processed.")
    parser.add_argument("name", help="The name of the output transcript file without extension.")
    parser.add_argument("speakers", help="The number of speakers on the track.", default=3)
    
    args = parser.parse_args()

    url = args.url
    name = args.name
    speakers_count = args.speakers
    
    raw_transcript_path = f"./podcasts-raw-transcripts/{name}.json"
    clean_transcript_path = f"./podcasts-clean-transcripts/{name}.md"
    results_file_path = f"./podcasts-results/{name}.md"
    substack_file_path = f"./podcasts-results/substack_{name}.md"
    
    # These are probably not the most elegant solutions, but they 
    # help with saving time since transcriptions are the same but we
    # might want to tweak the other prompts for better results.
    
    if not os.path.exists(raw_transcript_path):
        transcript = transcribe_audio(url, name, speakers_count)
    else:
        file = open(raw_transcript_path, "r").read()
        transcript = json.loads(file)['segments']
        
    print("Raw transcript is ready")
        
    if not os.path.exists(clean_transcript_path):
        transcript = process_transcript(transcript, name)
    else:
        transcript = open(clean_transcript_path, "r").read()
        
    print("Clean transcript is ready")
    
    chapters = create_chapters(transcript)
    
    print("Chapters are ready")
    
    show_notes = create_show_notes(transcript)
    
    print("Show notes are ready")
    
    title_suggestions_str = title_suggestions(transcript)
    
    print("Titles are ready")
    
    tweet_suggestions_str = tweet_suggestions(transcript)
    
    print("Tweets are ready")

    with open(results_file_path, "w") as f:
        f.write("Chapters:\n")
        f.write(chapters)
        f.write("\n\n")
        f.write("Writeup:\n")
        f.write(create_writeup(transcript))
        f.write("\n\n")
        f.write("Show Notes:\n")
        f.write(show_notes)
        f.write("\n\n")
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
        f.write(transcript)
    
    print(f"Results written to {results_file_path}")
    

if __name__ == "__main__":
    main()
