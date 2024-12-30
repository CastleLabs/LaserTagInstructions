# Laser Tag Instructional Video Player

This project is designed to run on a Raspberry Pi (with Raspberry Pi OS or a similar Linux distribution). It displays an image on a connected HDMI monitor until a physical button is pressed, at which point it plays a laser tag instructional video. Additionally, it provides a simple web interface (via Flask) to:

- Upload new images or videos
- Select which image or video should be the default
- Trigger playback manually from a browser

## Features

- **Image Display**: Uses `fbi` to display an image on the HDMI screen
- **Video Playback**: Uses `mpv` for full-screen video playback on the HDMI output
- **GPIO Button**: Monitors a physical button (on GPIO pin 17 by default) to trigger video playback
- **Flask Web Server**: Provides a browser-based interface to:
  - Upload images and videos
  - Select which image/video is the default
  - Trigger the video to play instantly
- **Logging**: Logs to both console and a file (default `/home/tech/video_button.log`)

## Hardware Requirements

- Raspberry Pi (any model with GPIO capabilities)
- HDMI display (monitor or TV)
- A momentary push-button switch connected to GPIO 17 (and ground)

## Software Requirements

- **Python 3** (already included on most Raspberry Pi OS versions)
- **Flask**: for the web interface
- **RPi.GPIO**: for GPIO support
- **fbi**: for image display on the framebuffer
- **mpv**: for video playback

Install these with:
```bash
sudo apt-get update
sudo apt-get install -y python3-pip fbi mpv
pip3 install flask RPi.GPIO werkzeug
```

## Installation and Setup

1. **Clone or copy this repository** into a directory on your Raspberry Pi:
```bash
cd /home/pi
git clone https://github.com/yourusername/laser-tag-instructional.git
cd laser-tag-instructional
```

2. **Create necessary directories**:
```bash
sudo mkdir -p /home/tech/uploads
sudo chown pi:pi /home/tech/uploads
sudo touch /home/tech/video_button.log
sudo chown pi:pi /home/tech/video_button.log
```

3. **(Optional) Place default files**:
   - A default image named `default_image.png` in `/home/tech`
   - A default video named `default_video.mp4` in `/home/tech`

4. **Make the Python script executable**:
```bash
chmod +x video_button.py
```

## Wiring the Button

1. Connect one side of the push-button switch to **GPIO 17** (BCM numbering)
2. Connect the other side of the switch to a **ground (GND)** pin on the Pi
3. The code uses an **internal pull-up** (`GPIO.PUD_UP`), so no external resistor should be needed in most cases

**Button Press Behavior**:
- When the button is pressed, GPIO 17 is pulled to ground (reads LOW)
- The script detects this and triggers video playback if not already playing

## Running the Application

1. **Start the script** manually:
```bash
cd /home/pi/laser-tag-instructional
./video_button.py
```
or
```bash
python3 video_button.py
```

2. **Access the web interface**:
   - In a browser, go to `http://<raspberry_pi_ip>:5000`
   - For example, if your Pi's IP is `192.168.1.10`, navigate to:
     ```
     http://192.168.1.10:5000
     ```

3. **GPIO and Display Behavior**:
   - On startup, the default image (`default_image.png`) is displayed if present
   - Pressing the button (or using "Play Video" on the web interface) starts the chosen video
   - After the video finishes, the default image is shown again

## Using the Web Interface

1. **Select Image / Video**:  
   - Use the dropdowns under "Select Image" or "Select Video" to choose a file
   - Click **Set Image** or **Set Video** to make it the new default

2. **Upload File**:  
   - Click **Choose File** under "Upload File" to pick an image (`png`, `jpg`, `jpeg`, `gif`) or video (`mp4`, `mov`, `avi`, `mkv`) from your computer
   - Click **Upload File**. The file will appear in the dropdown lists after upload

3. **Play Video**:  
   - Click the **Play Video** button to start playback immediately

4. **Status Indicator**:  
   - Shows either "Video Playing" (with a spinning icon) or "Ready to Play"
   - Automatically updates every 2 seconds

## Setting Up as a System Service

1. **Create a service file**:
```bash
sudo nano /etc/systemd/system/laser-tag.service
```

Add the following contents:
```ini
[Unit]
Description=Laser Tag Instructional Video Player
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/laser-tag-instructional
ExecStart=/usr/bin/python3 /home/pi/laser-tag-instructional/video_button.py
Restart=always

[Install]
WantedBy=multi-user.target
```

2. **Reload systemd**:
```bash
sudo systemctl daemon-reload
```

3. **Enable and start the service**:
```bash
sudo systemctl enable laser-tag.service
sudo systemctl start laser-tag.service
```

4. **Check status**:
```bash
systemctl status laser-tag.service
```

To stop manually:
```bash
sudo systemctl stop laser-tag.service
```

To restart:
```bash
sudo systemctl restart laser-tag.service
```

## Directory Structure

```
/home/tech/
├── default_image.png (optional)
├── default_video.mp4 (optional)
├── video_button.log (log file)
└── uploads/
    ├── image1.png
    ├── some_video.mkv
    └── ...

/home/pi/laser-tag-instructional/
├── video_button.py
├── templates/
│   └── index.html
├── README.md
└── ...
```

## Troubleshooting

1. **No image displays**:
   - Ensure `fbi` is installed: `sudo apt-get install -y fbi`
   - Verify the chosen image file exists on disk
   - Check logs (`/home/tech/video_button.log`) for errors

2. **Video doesn't play**:
   - Ensure `mpv` is installed: `sudo apt-get install -y mpv`
   - Check wiring of the button, or try the "Play Video" button in the web interface
   - Confirm the selected video file exists and has correct permissions

3. **Permission errors**:
   - If `fbi` or `pkill` require `sudo`, run the script with elevated privileges or adjust permissions accordingly
   - Ensure `/home/tech` and `/home/tech/uploads` are writable by the service user (e.g., `pi`)

4. **App doesn't load in browser**:
   - Confirm the Pi's IP address and that port 5000 is open
   - Check the service status if running via `systemd`

5. **Unexpected errors**:
   - Review `/home/tech/video_button.log`
   - Make sure no other process is hogging the framebuffer or HDMI output

## License

You can apply an open-source license of your choice (MIT, GPL, etc.). If you plan to distribute or open-source this project, include the appropriate license text here. This project is provided "as-is" without warranty.
