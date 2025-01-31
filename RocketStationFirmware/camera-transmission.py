import os
import subprocess
import time
import serial
from picamera2 import Picamera2
from PIL import Image

## Function to capture video with resolution 2560x1440 (1440p) at 60fps
def capture_video(camera_instance, output_file, frame_file, duration):
    video_config = camera_instance.create_video_configuration(main={"size": (2560, 1440)})
    camera_instance.configure(video_config)
    camera_instance.start_and_record_video(output_file)
    time.sleep(duration/2)
    
    #Capture and save a frame for image transmission
    request = camera_instance.capture_request()
    request.save("main", frame_file)
    request.release()
    
    time.sleep(duration/2)
    camera_instance.stop_recording()
    
## Function to compress image using JPEG format with quality factor
def compress_image(input_file, output_file, quality=50):
    with Image.open(input_file) as img:
        img.save(output_file, "JPEG", quality=quality)
        print(f"Image {input_file} compressed successfully to {output_file}!")


## Function to encode video using HEVC (H.265) codec with metadata extraction
def encode_video(input_file, output_file, resolution, crf, bitrate_log, ssim_log):
    command_encode = f"ffmpeg -i {input_file} -c:v libx265 -pix_fmt yuv420p -preset medium -crf {crf} -vf scale={resolution} -r 60 {output_file}"
    os.system(command_encode)
    
    # Calculate Bitrate of the output video
    command_bitrate = f"ffmpeg -i {output_file} 2>&1 | grep bitrate > {bitrate_log}"
    os.system(command_bitrate)
    
    # Calculate SSIM (Structural Similarity Index) between input and output video
    command_ssim = f"ffmpeg -i {input_file} -i {output_file} -lavfi \"[0:v][1:v]ssim\" -f null - > {ssim_log} 2>&1"
    os.system(command_ssim)
    
    
## Function to transfer file over to ESP32 for downlink transmission
def transfer_file(file_path, uart_port, baudrate=115200):
    total_size = os.path.getsize(file_path)
    start_time = time.time()
    
    with serial.Serial(uart_port, baudrate, timeout=1) as ser:
        with open(file_path, "rb") as file:
            while True:
                #Read data from file based on input buffer size or 1024 bytes
                data = file.read(ser.in_waiting or 1024)       
                if not data:
                    break
                ser.write(data)
                
    end_time = time.time()
    duration = end_time - start_time
    if duration > 0:
        bitrate = (total_size*8) / (duration*1024)  # in Kbps
        print(f"File {file_path} transferred succesfully. Transfer Bitrate: {bitrate:.2f} Kbps")
    else:
        print(f"Transfer duration too short to calculate bitrate.") 
        

## Function to test camera capture and video encoding for different camera modules
def test_camera(slot, output_prefix, capture_duration, uart_port="/dev/ttyS0"):
    picam2 = Picamera2(camera_num = int(slot))
    video_file = f"{output_prefix}_captured_video.mp4"
    frame_file = f"{output_prefix}_captured_image.jpg"
    compressed_image_file = f"{output_prefix}_compressed_image.jpg"
    
    capture_video(picam2, video_file, frame_file, capture_duration)
    compress_image(frame_file, compressed_image_file)

    resolutions = {"1440p": "2560:1440"}
    crf = 18    # Constant Rate Factor (CRF) acting as VBR (Variable Bitrate) control. Lower: Better Quality, Higher: Lower Bitrate
    output_files = {key: f"{output_prefix}_output_{key}_60fps.mp4" for key in resolutions.keys()}
    bitrate_logs = {key: f"{output_prefix}_bitrate_{key}.log" for key in resolutions.keys()}
    ssim_logs = {key: f"{output_prefix}_ssim_{key}.log" for key in resolutions.keys()}

    for key, resolution in resolutions.items():
        encode_video(video_file, output_files[key], resolution, crf, bitrate_logs[key], ssim_logs[key])
    
    picam2.stop()
    picam2.close()
    print(f"Testing of {output_prefix} completed!")
    time.sleep(2)
    
    transfer_file(output_files['1440p'], uart_port)
    
    
# Duration of the video capture in seconds
capture_duration = 10        # in seconds
uart_port = "/dev/ttyS0"    # UART Port for ESP32

# Test Camera on Slot 0
test_camera("0", "camera0", capture_duration, uart_port)

# Allow some time between tests to change cameras
time.sleep(2)

# Test Camera on Slot 1
test_camera("1", "camera1", capture_duration, uart_port)
