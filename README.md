# smol-podcaster

[![Open in StackBlitz](https://developer.stackblitz.com/img/open_in_stackblitz.svg)](https://stackblitz.com/github/fanahova/smol-podcaster)

We use smol-podcaster to take care of most of [Latent Space](https://latent.space) transcription work. What it will do for you:

- Generate a clean, diarized transcript of the podcast with speaker labels and timestamps
- Generate a list of chapters with timestamps for the episode
- Give you title ideas based on previous ones (modify the prompt to give examples of your own, it comes with Latent Space ones)
- Give you ideas for tweets to announce the podcast

To run:

`python smol-podcaster.py AUDIO_FILE_URL GUEST_NAME`

The URL needs to be a direct download link, it can't be a GDrive. For files <100MB you can use tmpfiles.org, otherwise Dropbox. For example: 

`python smol-podcaster.py "https://dl.dropboxusercontent.com/XXXX" "Tianqi"`

The script will automatically switch https://www.dropbox.com to https://dl.dropboxusercontent.com in the link.

# Environment Setup

Activate virtualenv with

`source venv/bin/activate`

Install dependencies with

`pip install -r requirements.txt`

Make a copy of the `.env.sample` and replace it with your keys:

`mv .env.sample .env`

Run with the command above

# License

MIT License
