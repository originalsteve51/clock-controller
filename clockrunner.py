"""
MIT License

Copyright (c) 2021 Stephen Harding

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
import RPi.GPIO as GPIO  
from time import sleep  
import threading
import logging

# LED pin assignments. All except the white led are simple led connections.
# The white led pin is also connected to the relay so it energizes the
# relay as well as lights the white led.
RELAY_AND_WHITE = 5
LED_BLUE = 26
LED_GREEN = 19
LED_YELLOW = 6
LED_RED = 20
leds = (RELAY_AND_WHITE, LED_BLUE, LED_GREEN, LED_YELLOW, LED_RED)

# Pushbutton pin assignments
# White: Single-step the clock one minute
PB_WHITE = 25

# Time in seconds between repeated pulses to the clock
REPEAT_INTERVAL_SECONDS = 1.2

# Time in seconds to hold the relay each time it is actuated
HOLD_SECONDS = 1.0

# Hold must be less than repeat interval (with some safety factor),
# otherwise repeat will not work!
if HOLD_SECONDS >= REPEAT_INTERVAL_SECONDS - 0.1:
    raise Exception('Invalid setting of hold and repeat times. Contact the developer!')

# Blue: Repeat-step the clock BLUE_COUNT times
PB_BLUE = 24
BLUE_COUNT = 30

# Black: Repeat-step the clock BLACK_COUNT times
PB_BLACK = 27
BLACK_COUNT = 180

# Yellow: Repeat-step the clock YELLOW_COUNT times
PB_YELLOW = 17
YELLOW_COUNT = 60

# Red: Stop the clock, toggle to restart. If stopped with no
# restart, remain stopped 60 minutes (RED_COUNT) before restarting automatically.
PB_RED = 14
RED_COUNT = 60

buttons = (PB_WHITE, PB_BLUE, PB_BLACK, PB_YELLOW, PB_RED)

# Flags that are accessed globally by call-back functions and functions that
# run in their own threads. These flags are used to prevent conflicts when
# two things try to run simultaneously. For example, when the red button is
# pressed, other actions that try to actuate the relay must be blocked. 

# The relay is held down for a set amount of time when it is actuated. During 
# this time the relay_busy flag indicates that it is energized. Other attempts
# to use the relay are blocked until it is released.
relay_busy = False

# The red button prevents anything from actuating the relay, effectively stopping
# the clock. The red button toggles on and off when pressed. It also times out
# 60 minutes after it is pressed. This is how the clock can be stopped for 
# daylight saving time adjustment.
stopped = False

# The blue, black, and yellow buttons cause the clock to advance for predetermined
# number of minutes. During this time other attempts to actuate the relay are blocked.
# The red button stops the auto-advancing of the clock, as it should be expected to.
auto_advancing = False

# All five leds are initially off.
def initialize_leds(leds):
    for led in leds:
        GPIO.setup(led, GPIO.OUT, initial=0)

# All five buttons are set to be low (i.e. 0 volts) until pressed. When pressed,
# each button connects its pin with a high (i.e. 3.3 volts) signal. The rising edge of the
# button press is detected and a function named button_callback is called. This
# function can determine which button was pressed and take appropriate action.
def initialize_pushbuttons(buttons):
    for button in buttons:
        GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(button, GPIO.RISING, callback=button_callback, bouncetime=300)


# Turn on the relay and the white LED. Then start a timer to reset
# the relay and LED.
def relay_pulse():
    global relay_busy
    relay_busy = True
    GPIO.output(RELAY_AND_WHITE, 1)

    # Start an asynchronous timer that calls a function to
    # turn the relay off and led off in 1 second.
    threading.Timer(HOLD_SECONDS, relay_reset).start()

# Turn off the relay and the white LED.
def relay_reset():
    global relay_busy
    GPIO.output(RELAY_AND_WHITE, 0)
    relay_busy = False

def stop_set():
    global stopped
    if not stopped:
        stopped = True
        GPIO.output(LED_RED, 1)
        # Start an asynchronous timer that calls a function to
        # turn the relay off and led off in 3600 seconds (1 hour)
        # which you can do if your clock is ahead or when adjusting 
        # for Daylight Saving Time.
        STOP_SECONDS = RED_COUNT * 60
        threading.Timer(STOP_SECONDS, stop_reset).start()
    else:
        stopped = False
        GPIO.output(LED_RED, 0)

def stop_reset():
    global stopped
    if stopped:
        stopped = False
        GPIO.output(LED_RED, 0)

def repeating_pulses(count, indicator_led):
    global auto_advancing
    # Set flag indicating that repeating pulses are being sent
    auto_advancing = True
    GPIO.output(indicator_led, 1)
    for _ in range(count):
        # The red button sets the stopped flag when pressed to
        # set the stop state. The stopped flag is also cleared by the red 
        # button if it is pressed to reset the stop state.
        if stopped:
            break
        else:
            relay_pulse()
        if relay_busy:
            # The relay is held closed for HOLD_SECONDS seconds. Wait
            # at least that long so it opens before looping to close it again.
            # We enforce REPEAT_INTERVAL_SECONDS to be longer than
            # HOLD_SECONDS at program start-up time.
            sleep(REPEAT_INTERVAL_SECONDS)
            pass
    GPIO.output(indicator_led, 0)
    auto_advancing = False

def repeat_dispatcher(pulse_count, indicator_led):
        # The multi-pulse behavior takes a long time and must
        # be done on a separate thread to keep the button processing
        # responsive. During repeat, only the red button presses
        # are handled. A red button press can set the stopped flag
        # to end a repeat thread.
        global auto_advancing
        if not relay_busy and not stopped and not auto_advancing:
            x = threading.Thread(target=repeating_pulses, args=(pulse_count, indicator_led,))
            x.start()
        else:
            logging.info('repeat_dispatcher: Cannot process request')


# Handle button presses as they occur. Note that this callback can only handle
# one button press at a time. If processing for a button press takes a long time,
# the processing should be done on a separate thread so the buttons remain
# responsive.
def button_callback (channel):
    global relay_busy
    global stopped
    global auto_advancing
    # White button sends a single pulse only when the relay is not already
    # picked and when there is not a repeating operation already running
    if channel == PB_WHITE and GPIO.input(PB_WHITE):
        if not relay_busy and not stopped and not auto_advancing:
            relay_pulse()
        else:
            logging.info(f'Button press {channel} not accepted because the relay was busy or stopped')
    # The red button toggles the stopped state on and off
    elif channel == PB_RED and GPIO.input(PB_RED):
        stop_set()
    # The blue button causes a fixed number of minutes to be advanced
    elif channel == PB_BLUE and GPIO.input(PB_BLUE):
        # Advance BLUE_COUNT minutes
        repeat_dispatcher(BLUE_COUNT, LED_BLUE)
    # Note that PB_BLACK is represented by the green led because I have no
    # green button caps
    # The black button causes a fixed number of minutes to be advanced
    elif channel == PB_BLACK and GPIO.input(PB_BLACK):
        # Advance BLACK_COUNT times
        repeat_dispatcher(BLACK_COUNT, LED_GREEN)
    # The yellow button causes a fixed number of minutes (usually 60)
    # to be advanced
    elif channel == PB_YELLOW and GPIO.input(PB_YELLOW):
        # Advance 1 hour (60 minutes-good for daylight savings time 'fall back')
        # YELLOW_COUNT must be 60 for 1 hour advance
        repeat_dispatcher(YELLOW_COUNT, LED_YELLOW)

    else:
        logging.info(f'button_callback: Unexpected input from channel: {channel}')

 

if __name__ == '__main__':
    try:
        logging.basicConfig(filename='clockrunner.log',
                            filemode='w+',
                            level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

        # Start with Broadcom pin numbering and be sure GPIO is cleaned up
        # from any previous settings
        GPIO.setmode(GPIO.BCM) 

        initialize_leds(leds)

        initialize_pushbuttons(buttons)

        current_minute = int(datetime.strftime(datetime.now(),"%M"))
        last_minute = current_minute    

        while True:
            current_minute = int(datetime.strftime(datetime.now(),"%M"))

            while current_minute != last_minute:
                last_minute = current_minute
                if not relay_busy and not stopped and not auto_advancing:
                    relay_pulse()
                else:
                    logging.info('A regular automatic clock minute pulse was not accepted')
            sleep(5)
    except Exception as e:
        print (e)
    except KeyboardInterrupt:
        pass
    finally:
        print(f'\nResetting all GPIO ports')
        GPIO.cleanup() 
