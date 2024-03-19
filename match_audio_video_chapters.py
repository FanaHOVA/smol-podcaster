import difflib
import re

def find_times_in_video_transcript(chapter_times_string, audio_transcript_file, video_transcript_file):
    # Split the chapter times string into a list
    audio_chapter_times = [line.split(" ")[0] for line in chapter_times_string.split("\n") if line]

    # Read the transcripts from the files
    with open(audio_transcript_file, 'r') as file:
        audio_transcript = file.read()
    with open(video_transcript_file, 'r') as file:
        video_transcript = file.read()

    # Split the transcripts into lines
    audio_lines = audio_transcript.split("\n")
    video_lines = video_transcript.split("\n")

    # Initialize a dictionary to store the results
    results = {}

    # Process each chapter time
    for audio_chapter_time in audio_chapter_times:
        # Find the text in the audio transcript that corresponds to the chapter time
        audio_chapter_text = ""
        for line in audio_lines:
            if line.find(audio_chapter_time) != -1:
                audio_chapter_text = line.split("]:")[1]
                break

        # Find the corresponding text in the video transcript
        best_match = ""
        best_ratio = 0
        best_line = ""
        for line in video_lines:
            if not line:
                continue
            
            text = line.split("]:")[1]
            # Calculate the similarity ratio
            ratio = difflib.SequenceMatcher(None, audio_chapter_text, text).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = text
                best_line = line

        # Extract the timestamp from the best matching line
        video_chapter_time = re.search(r'\[(\d{2}:\d{2}:\d{2})\]', best_line)

        # Store the result
        results[audio_chapter_time] = video_chapter_time

    return results

# Example usage
chapter_times_string = """
[00:00:00] Introductions
[00:00:51] Extrinsic vs Intrinsic Success
[00:02:58] Importance of Open Source and Its Impact
[00:04:25] PyTorch vs TinyGrad
[00:10:23] Why PyTorch is the Switzerland of frameworks  
[00:12:44] Modular's Mojo + PyTorch?
[00:16:12] PyTorch vs Apple's MLX
[00:19:46] FAIR / PyTorch Alumni
"""
audio_transcript_file = "podcasts-clean-transcripts/Soumith.md"
video_transcript_file = "podcasts-clean-transcripts/SoumithVideo.md"

print(find_times_in_video_transcript(chapter_times_string, audio_transcript_file, video_transcript_file))