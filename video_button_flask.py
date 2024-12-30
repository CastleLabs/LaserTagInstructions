#!/usr/bin/env python3

import os
import time
import threading
import subprocess
import logging
import RPi.GPIO as GPIO
from werkzeug.utils import secure_filename
from flask import Flask, request, render_template, redirect, url_for, flash

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/home/tech/video_button.log")
    ]
)
logger = logging.getLogger(__name__)

BUTTON_PIN = 17
BASE_DIR = "/home/tech"
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "mov", "avi", "mkv"}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024

IMAGE_PATH = os.path.join(BASE_DIR, "default_image.png")
VIDEO_PATH = os.path.join(BASE_DIR, "default_video.mp4")

is_playing = False
current_process = None
shutting_down = False

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config.update(
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH
)

def check_environment():
    logger.info("Checking environment setup...")
    for prog in ["fbi", "mpv"]:
        try:
            subprocess.run(["which", prog], check=True, capture_output=True)
            logger.info(f"{prog} is installed.")
        except subprocess.CalledProcessError:
            logger.error(f"{prog} is NOT installed or not in PATH.")

    logger.info(f"BASE_DIR exists: {os.path.exists(BASE_DIR)}")
    logger.info(f"UPLOAD_FOLDER exists: {os.path.exists(UPLOAD_FOLDER)}")
    logger.info(f"Default image exists: {os.path.exists(IMAGE_PATH)}")
    logger.info(f"Default video exists: {os.path.exists(VIDEO_PATH)}")

def get_available_files():
    """Get lists of available image and video files"""
    images = []
    videos = []

    # Add default files if they exist
    if os.path.exists(os.path.join(BASE_DIR, "default_image.png")):
        images.append(("default_image.png", os.path.join(BASE_DIR, "default_image.png")))
    if os.path.exists(os.path.join(BASE_DIR, "default_video.mp4")):
        videos.append(("default_video.mp4", os.path.join(BASE_DIR, "default_video.mp4")))

    # Add uploaded files
    if os.path.exists(UPLOAD_FOLDER):
        for file in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, file)
            if is_image_file(file):
                images.append((file, filepath))
            elif is_video_file(file):
                videos.append((file, filepath))

    return images, videos

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def is_video_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"mp4", "mov", "avi", "mkv"}

def is_image_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"png", "jpg", "jpeg", "gif"}

def setup_gpio():
    logger.info("Setting up GPIO...")
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        logger.info("GPIO setup complete.")
    except Exception as e:
        logger.error(f"GPIO setup failed: {e}")
        raise

def kill_processes():
    global current_process
    logger.debug("Attempting to kill existing processes...")

    subprocess.run(["sudo", "pkill", "-9", "fbi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["pkill", "-9", "mpv"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if current_process:
        try:
            current_process.terminate()
        except Exception:
            pass
        current_process = None

def show_image():
    global current_process
    logger.info(f"Attempting to show image: {IMAGE_PATH}")

    try:
        kill_processes()
        if os.path.exists(IMAGE_PATH):
            with open(os.devnull, 'w') as devnull:
                cmd = ["sudo", "fbi", "--noverbose", "-T", "1", "-a", IMAGE_PATH]
                current_process = subprocess.Popen(
                    cmd,
                    stdout=devnull,
                    stderr=devnull
                )
                time.sleep(0.5)
        else:
            logger.error(f"Image file not found: {IMAGE_PATH}")
    except Exception as e:
        logger.error(f"Error showing image: {e}")

def play_video():
    global is_playing, current_process
    logger.info(f"Attempting to play video: {VIDEO_PATH}")

    if not os.path.exists(VIDEO_PATH):
        logger.error(f"Video file not found: {VIDEO_PATH}")
        is_playing = False
        return

    try:
        subprocess.run(["sudo", "pkill", "-9", "fbi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["clear"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        cmd = [
            "mpv",
            "--vo=gpu",
            "--gpu-context=drm",
            "--gpu-api=opengl",
            "--drm-connector=HDMI-A-1",
            "--fullscreen",
            "--no-osc",
            "--loop=no",
            "--no-osd-bar",
            "--no-terminal",
            "--really-quiet",
            "--msg-level=all=no",
            "--audio-device=alsa/hdmi:CARD=vc4hdmi0,DEV=0",
            "--volume=100",
            VIDEO_PATH
        ]

        with open(os.devnull, 'w') as devnull:
            video_process = subprocess.Popen(
                cmd,
                stdout=devnull,
                stderr=devnull,
                env={
                    "SDL_VIDEODRIVER": "drm",
                    "DISPLAY": ""
                }
            )
            video_process.wait()

    except Exception as e:
        logger.error(f"Error playing video: {e}")
    finally:
        is_playing = False
        subprocess.run(["clear"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        show_image()

def button_monitor_loop():
    global is_playing, shutting_down
    logger.info("Starting button monitor loop.")
    last_press_time = 0
    debounce_delay = 2.0

    while not shutting_down:
        try:
            if not is_playing and GPIO.input(BUTTON_PIN) == GPIO.LOW:
                now = time.time()
                if (now - last_press_time) > debounce_delay:
                    last_press_time = now
                    logger.debug("Button press detected (debounced).")
                    is_playing = True
                    threading.Thread(target=play_video, daemon=True).start()
            time.sleep(0.05)
        except Exception as e:
            logger.error(f"Error in button monitor: {e}")
            time.sleep(0.5)

    logger.info("Button monitor loop exiting...")

@app.route("/", methods=["GET"])
def index():
    logger.debug("Index page requested.")
    images, videos = get_available_files()
    return render_template(
        "index.html",
        current_image=IMAGE_PATH,
        current_video=VIDEO_PATH,
        is_playing=is_playing,
        images=images,
        videos=videos
    )

@app.route("/play", methods=["GET"])
def play():
    global is_playing
    logger.debug("Play endpoint triggered.")

    if not is_playing:
        is_playing = True
        threading.Thread(target=play_video, daemon=True).start()
        flash("Video playback triggered!", "success")
    else:
        flash("Video is already playing. Try again later.", "warning")

    return redirect(url_for("index"))

@app.route("/select", methods=["POST"])
def select_file():
    global IMAGE_PATH, VIDEO_PATH
    file_type = request.form.get("type")
    file_path = request.form.get("path")

    if not file_path:
        flash("No file selected.", "error")
        return redirect(url_for("index"))

    if file_type == "image":
        IMAGE_PATH = file_path
        if not is_playing:
            show_image()
        flash("Image selection updated!", "success")
    elif file_type == "video":
        VIDEO_PATH = file_path
        flash("Video selection updated!", "success")

    return redirect(url_for("index"))

@app.route("/upload", methods=["POST"])
def upload():
    logger.debug("Upload endpoint triggered.")
    global IMAGE_PATH, VIDEO_PATH

    if "file" not in request.files:
        logger.warning("No file in request.")
        flash("No file selected.", "error")
        return redirect(url_for("index"))

    file = request.files["file"]
    if file.filename == "":
        logger.warning("Empty filename.")
        flash("No selected file.", "error")
        return redirect(url_for("index"))

    try:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            logger.info(f"File saved to: {filepath}")

            if is_image_file(filename):
                IMAGE_PATH = filepath
                if not is_playing:
                    show_image()
                flash("New image uploaded successfully!", "success")
            elif is_video_file(filename):
                VIDEO_PATH = filepath
                flash("New video uploaded successfully!", "success")
        else:
            logger.warning(f"Invalid file type: {file.filename}")
            flash("File type not allowed.", "error")

    except Exception as e:
        logger.error(f"Error in upload: {e}")
        flash(f"Error uploading file: {str(e)}", "error")

    return redirect(url_for("index"))

@app.errorhandler(413)
def request_entity_too_large(error):
    logger.error("File too large error.")
    flash("File too large! Maximum size is 100MB.", "error")
    return redirect(url_for("index"))

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}")
    flash(f"An error occurred: {str(e)}", "error")
    return redirect(url_for("index"))

def main():
    global shutting_down

    try:
        logger.info("Starting application...")
        check_environment()
        os.makedirs(BASE_DIR, exist_ok=True)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        setup_gpio()

        logger.info("Attempting to show initial image...")
        show_image()

        logger.info("Starting button monitor thread...")
        t = threading.Thread(target=button_monitor_loop, daemon=True)
        t.start()

        logger.info("Starting Flask server on 0.0.0.0:5000...")
        app.secret_key = os.urandom(24)
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        shutting_down = True
        time.sleep(0.5)
        GPIO.cleanup()
        logger.info("Application shutting down...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application terminated by user.")
    finally:
        logger.info("Cleaning up...")
        kill_processes()
        GPIO.cleanup()
