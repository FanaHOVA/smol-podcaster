import argparse
import requests
import replicate
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from dotenv import load_dotenv
import os
from datetime import datetime
import json
import openai

load_dotenv()

openai.api_key = os.environ.get("OPENAI_API_KEY")
anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def transcribe_audio(file_url, episode_name):
    output = replicate.run(
        "thomasmol/whisper-diarization:7e5dafea13d80265ea436e51a310ae5103b9f16e2039f54de4eede3060a61617",
        input={
            "file_url": file_url,
            "num_speakers": 3,
            "prompt": "A technical podcast about artificial intelligence and machine learning"
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

        # Divide "end" value by 60 and convert to hours, minutes and seconds
        seconds = int(entry["end"])
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        timestamp = "[{:02d}:{:02d}:{:02d}]".format(hours, minutes, seconds)

        transcript_strings.append(f"**{speaker}**: {text} {timestamp}")
        
    clean_transcript = "\n\n".join(transcript_strings)
    
    with open(f"./podcasts-clean-transcripts/{episode_name}.txt", "w") as f:    
        f.write(clean_transcript)
        
    return clean_transcript
    
 
def create_chapters(transcript):
    anthropic = Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )
        
    chapters = anthropic.completions.create(
        model="claude-2",
        max_tokens_to_sample=3000,
        prompt=f"{HUMAN_PROMPT} Here's a podcast transcript with timestamps. Generate a list of all major topics covered in the podcast, and the timestamp at which it's mentioned in the podcast. Use this format: - [00:00:00] Topic name. Here's the transcript: \n\n {transcript} {AI_PROMPT}",
    )
    
    print(chapters.completion)
    
    return chapters.completion

def title_suggestions(transcript):
    prompt = f"""
    These are some titles of previous podcast episodes we've published:

    1. "From RLHF to RLHB: The Case for Learning from Human Behavior"
    2. "Commoditizing the Petaflop"
    3. "Llama 2: The New Open LLM SOTA"
    4. "FlashAttention 2: making Transformers 800\%\ faster w/o approximation"
    5. "Mapping the future of *truly* Open Models and Training Dolly for $30"

    Here's a transcript of the podcast episode; suggest 8 title options for it:
    
    {transcript}
    """
    
    gpt_suggestions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k", 
        temperature=0.7,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    print("GPT-3.5 16k title suggestions:\n\n")
    print(gpt_suggestions.choices[0].message.content)
    print("\n")
        
    claude_suggestions = anthropic.completions.create(
        model="claude-2",
        max_tokens_to_sample=3000,
        temperature=0.7,
        prompt=f"{HUMAN_PROMPT} {prompt} {AI_PROMPT}",
    )
    
    print("Claude's title suggestions:\n")
    print(claude_suggestions.completion)
    print("\n")
    
def tweet_suggestions(transcript):
    prompt = f"""
    Here's a transcript of our latest podcast episode; suggest 8 tweets to share it on social medias.
    It should include a few bullet points of the most interesting topics. Our audience is technical.
    Use a writing style between Hemingway's and Flash Fiction. 
    
    {transcript}
    """
    
    gpt_suggestions = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k", 
        temperature=0.7,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    print("GPT-3.5 16k tweet suggestions:")
    print(gpt_suggestions.choices[0].message.content)
    print("\n")
    
    anthropic = Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )
        
    claude_suggestions = anthropic.completions.create(
        model="claude-2",
        max_tokens_to_sample=3000,
        temperature=0.7,
        prompt=f"{HUMAN_PROMPT} {prompt} {AI_PROMPT}",
    )
    
    print("Claude's tweet suggestions:")
    print(claude_suggestions.completion)
    print("\n")
    
def main():
    parser = argparse.ArgumentParser(description="Transcribe the podcast audio from an URL like tmpfiles.")
    parser.add_argument("url", help="The URL of the podcast to be processed.")
    parser.add_argument("name", help="The name of the output transcript file without extension.")

    args = parser.parse_args()

    url = args.url
    name = args.name
    
    raw_transcript_path = f"./podcasts-raw-transcripts/{name}.json"
    clean_transcript_path = f"./podcasts-clean-transcripts/{name}.txt"
    
    print(f"Running smol-podcaster on {url}")
    
    # These are probably not the most elegant solutions, but they 
    # help with saving time since transcriptions are the same but we
    # might want to tweak the other prompts for better results.
    
    if not os.path.exists(raw_transcript_path):
        transcript = transcribe_audio(url, name)
    else:
        file = open(raw_transcript_path, "r").read()
        transcript = json.loads(file)['segments']
        
    if not os.path.exists(clean_transcript_path):
        transcript = process_transcript(transcript, name)
    else:
        transcript = open(clean_transcript_path, "r").read()
    
    create_chapters(transcript)
    title_suggestions(transcript)
    tweet_suggestions(transcript)
    

if __name__ == "__main__":
    main()
