# Clock Controller with Chimes
This is a Raspberry Pi based controller for a vintage IBM remote clock. Besides running a clock, this program demonstrates how to use GPIO event-driven input and Python threading to asynchronously operate long-running functions from a set of pushbutton inputs. Button presses initiate activity on threads leaving the buttons active. By keeping the buttons active, long-running functions can be altered by subsequent button presses.
An option is to also run the chime program, which allows hourly chiming. The default chimes are cuckoo sounds.
