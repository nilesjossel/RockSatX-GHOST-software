import os
import subprocess
import time
from picamera2 import Picamera2

def capture_video(camera_instance, output_file, duration):
    video_config = camera_instance.create_video_configuration(main={"size": (1920, 1080)})
    camera_instance.configure(video_config)
    camera_instance.start_and_record_video(output_file)
    time.sleep(duration)
    camera_instance.stop_recording()

def encode_video(input_file, output_file, resolution, crf, bitrate_log, ssim_log):
    command_encode = f"ffmpeg -i {input_file} -c:v libx265 -pix_fmt yuv420p -preset medium -crf {crf} -vf scale={resolution} -r 60 {output_file}"
    os.system(command_encode)
    
    command_bitrate = f"ffmpeg -i {output_file} 2>&1 | grep bitrate > {bitrate_log}"
    os.system(command_bitrate)
    
    command_ssim = f"ffmpeg -i {input_file} -i {output_file} -lavfi \"[0:v][1:v]ssim\" -f null - > {ssim_log} 2>&1"
    os.system(command_ssim)

def test_camera(slot, output_prefix, capture_duration):
    picam2 = Picamera2()
    camera_capture_file = f"{output_prefix}_captured_video.mp4"
    
    capture_video(picam2, camera_capture_file, capture_duration)

    resolutions = {"1080p": "1920:1080", "1440p": "2560:1440"}
    crf = 28
    output_files = {key: f"{output_prefix}_output_{key}_60fps.mp4" for key in resolutions.keys()}
    bitrate_logs = {key: f"{output_prefix}_bitrate_{key}.log" for key in resolutions.keys()}
    ssim_logs = {key: f"{output_prefix}_ssim_{key}.log" for key in resolutions.keys()}

    for key, resolution in resolutions.items():
        encode_video(camera_capture_file, output_files[key], resolution, crf, bitrate_logs[key], ssim_logs[key])
    
    picam2.stop()
    picam2.close()
    print(f"Testing of {output_prefix} completed!")
    time.sleep(2)
    
# Duration of the video capture in seconds
capture_duration = 8

# Test Camera on Slot 0
test_camera("0", "camera0", capture_duration)

# Allow some time between tests to change cameras
time.sleep(2)

# Test Camera on Slot 1
test_camera("1", "camera1", capture_duration)
