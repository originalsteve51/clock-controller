"""
MIT License

Copyright (c) 2022 Stephen Harding

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from datetime import datetime
from time import sleep  
import subprocess
import logging

# Lists of hours that chiming is allowed on weekdays and weekends
weekend_chime_times = [8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]
weekday_chime_times = [8,18,19,20,21,22,23]

# Test mode makes the cuckoo chime every 5 minutes
test_mode = True

def get_current_hour():
	return int(datetime.strftime(datetime.now(),"%H"))

def get_current_minute():
	return int(datetime.strftime(datetime.now(),"%M"))

# Start a new process to run aplay for the specified sound file
def play_sound(sound_file):
	p = subprocess.Popen(['aplay',
                        sound_file],
                        stdin=subprocess.PIPE,
                        stdout=None,stderr=None)
	return p

# Return a list of hourly times that depends on whether now is a weekend or
# a weekday 
def adjust_chime_times():
	today = datetime.today().weekday()
	# M=0, Tu=1, W=2, Th=3, F=4, Sa=5, Su=6
	if today in range(5):
		logging.debug(f'Weekday chime times are in effect: {weekday_chime_times}')
		return weekday_chime_times
	else:
		logging.debug(f'Weekend chime times are in effect: {weekend_chime_times}')
		return weekend_chime_times

# Compare the last known hour with the current hour. If they differ, then
# chime depending on whether chiming is permitted now.
# Return the latest hour for which chiming was considered.
def hourly_chime(last_hour):
	current_hour = get_current_hour()
	if current_hour != last_hour:
		chime_times = adjust_chime_times()
		last_hour = current_hour

		# No chiming after midnight or before 8 am
		if current_hour in chime_times:
			if last_hour % 12 == 0:
				chime_count = 12
			else:
				chime_count = last_hour % 12
			sleep(2)
			for _ in range(chime_count):
				play_sound('coocoo.wav')
				sleep(1.0)
			logging.info(f'Chimed {chime_count} times')
		else:
			logging.info('Bypassed hourly_chime because it was not allowed')

	return last_hour

# The test_chime operates every 5 minutes and chimes twice with a different sound 
# than the hourly chime. It does not chime at the top of the hour.
def test_chime(last_minute):
	current_minute = get_current_minute()
	if current_minute != last_minute:
		last_minute = current_minute

		# Sound test chime every 5 minutes except at the top of the hour
		if current_minute != 0 and current_minute % 5 == 0:
			sleep(2)
			for _ in range(2):
				play_sound('G8-1.wav')
				sleep(1.0)
	return last_minute

if __name__ == '__main__':

	try:
		if test_mode:
			log_level = logging.DEBUG
		else:
			log_level = logging.INFO

		logname_suffix = datetime.now().strftime("%s")
		logging.basicConfig(filename=f'chimer{logname_suffix}.log',
                            filemode='w+',
                            level=log_level,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        
		logging.info('The program has started running')

		# Initially say that the chime has already sounded for the present hour
		last_hour_chimed = get_current_hour()
		if test_mode:
			last_minute_chimed = get_current_minute()

		while True:
			if test_mode:
				last_minute_chimed = test_chime(last_minute_chimed)

			# Tell hourly_chime() the last time we chimed and let it see
			# if the hour changed since then. If the hour changed, it
			# will chime if allowed to do so.
			last_hour_chimed = hourly_chime(last_hour_chimed)

			sleep(1)
	except Exception as e:
		logging.error(f'Fatal error: {e}')
	except KeyboardInterrupt:
		logging.info('Program terminated by user')
	finally:
		pass
    