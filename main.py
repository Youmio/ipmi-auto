#!/usr/bin/env python3

import subprocess
import logging
from apscheduler.schedulers.background import BlockingScheduler

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 假设 ipmitool 已经安装并可以直接在命令行中调用
ip = ''
username = ''
password = ''
interval_seconds = 30


def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing command: {e}\nStandard Error Output: {e.stderr}")
        return ""

def disable_auto():
    command = f'ipmitool -I lanplus -H {ip} -U {username} -P {password} raw 0x30 0x30 0x01 0x00'
    run_command(command)
    logging.info("Auto fan control disabled.")

def set_speed(percent):
    disable_auto()  # Ensure auto control is disabled before setting speed
    command = f'ipmitool -I lanplus -H {ip} -U {username} -P {password} raw 0x30 0x30 0x02 0xff {hex(percent)}'
    run_command(command)
    logging.info(f"Set fan speed to {percent}%")

def get_temp_average():
    command = f'ipmitool -I lanplus -H {ip} -U {username} -P {password} sensor'
    result = run_command(command)
    lines = result.split('\n')
    
    temp_values = []
    for line in lines:
        if 'Temp' in line:
            parts = line.split('|')
            try:
                temp_str = parts[1].strip()
                if temp_str.lower() != 'na':
                    temp_float = float(temp_str)
                    temp_values.append(temp_float)
                    if len(temp_values) == 2:  # We need only the first two temperature readings
                        break
            except ValueError:
                logging.warning(f"Could not convert temperature data '{temp_str}' to float.")
    
    if len(temp_values) == 2:
        average_temp = sum(temp_values) / len(temp_values)
        logging.info(f"Average temperature: {average_temp}°C")
        return average_temp
    else:
        logging.warning("Not enough temperature data to calculate average.")
        return None

def auto_config():
    average_temp = get_temp_average()
    if average_temp is not None:
        if average_temp >= 85:
            set_speed(40)
        elif 75 <= average_temp < 85:
            set_speed(30)
        elif 60 <= average_temp < 75:
            set_speed(20)
        elif 50 <= average_temp < 60:
            set_speed(10)
        elif average_temp < 50:
            set_speed(5)
    else:
        logging.error("Failed to get a valid average temperature. No action taken.")

if __name__ == '__main__':
    scheduler = BlockingScheduler()
    scheduler.add_job(auto_config, 'interval', seconds=interval_seconds)
    scheduler.start()
