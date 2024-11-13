import tkinter
from time import sleep, time
from datetime import date, datetime, time, timedelta
from tkinter import *
import serial
import threading

def main():
    #set up GUI window
    window = Tk()
    window.title("Rate Table Sweep")
    window.geometry('250x150')
    now = datetime.now()
    currentTime = now.strftime("%H:%M:%S")
    lblCurrentTime1 = Label(window, text="Current Time: ")
    lblCurrentTime2 = Label(window, text=currentTime)
    lblCurrentTime1.grid(column=0, row=0)
    lblCurrentTime2.grid(column=1, row=0)
    lblHr = Label(window, text="Enter Start Hour")
    lblHr.grid(column=0, row=1)
    txtHr = Entry(window, width=10)
    txtHr.grid(column=1, row=1)
    lblMn = Label(window, text="Enter Start Minute")
    lblMn.grid(column=0, row=2)
    txtMn = Entry(window, width=10)
    txtMn.grid(column=1, row=2)
    lblCom = Label(window, text="Enter ComPort (i.e. comx)")
    lblCom.grid(column=0, row=3)
    txtCom = Entry(window, width=10)
    txtCom.grid(column=1, row=3)
    #set up global variable for mid execution stops
    global testRunning
    testRunning = False

    #run sweep function that runs on separate thread
    def runSweep():
        startButton.config(state=tkinter.DISABLED)
        global testRunning
        testRunning = True
        #rudimentary input checks
        if len(txtMn.get()) == 0 or len(txtHr.get()) == 0 or len(txtCom.get()) == 0:
            print("One or more fields are empty.")
            startButton.config(state=tkinter.NORMAL)
            return

        try:
            startMin = int(txtMn.get())
            startHr = int(txtHr.get())
            com1 = txtCom.get()
        except:
            print("One or more fields are invalid.")
            startButton.config(state=tkinter.NORMAL)
            return
        if startMin > 59 or startMin < 0:
            print("Please enter a valid start minute.")
            startButton.config(state=tkinter.NORMAL)
            return
        if startHr > 23 or startHr < 1:
            print("Please enter a valid start hour.")
            startButton.config(state=tkinter.NORMAL)
            return
        n = datetime.now()
        # Setup start time
        startTime = datetime(n.year, n.month, n.day, startHr, startMin, 0)
        # Calculate test duration
        startDegperSec = 0
        stopDegperSec = 1900
        deltaDegperSec = 100
        cycleDelay = 12
        dt = (stopDegperSec - startDegperSec) / deltaDegperSec * cycleDelay
        hours = dt / 3600
        minutes = (dt - hours * 3600) / 60
        seconds = (dt - hours * 3600 - minutes * 60)
        completeTime = startTime + timedelta(seconds=dt)
        #wait for start time to be reached
        try:

            while datetime.now() < startTime:
                print("Completion Time: ", completeTime)
                print("     Start Time: ", startTime)
                print("   Current Time: ", datetime.now())
                sleep(1)
                if not testRunning:
                    return

            with IdealAerosmithTable(com1, debug=False) as atl:

                try:
                    atl.stop()
                    #run rate table in counterclockwise direction
                    for speed in range(startDegperSec, stopDegperSec + 1, deltaDegperSec):
                        for i in range(cycleDelay):
                            #stop rate table if stop button is clicked
                            if not testRunning:
                                atl.stop()
                                sleep(2)
                                exit(0)
                            atl.jog(-speed)
                            print("Completion Time: ", completeTime)
                            print("   Current Time: ", datetime.now())
                            print("   Current Speed:  %d degrees/second" % speed)
                            sleep(1)
                    atl.stop()
                    sleep(60)
                    #run clockwise
                    for speed in range(startDegperSec, stopDegperSec + 1, deltaDegperSec):
                        for j in range(cycleDelay):
                            #if stop button is clicked, stop rate table
                            if not testRunning:
                                atl.stop()
                                sleep(2)
                                exit(0)
                            atl.jog(speed)
                            print("Completion Time: ", completeTime)
                            print("Current Time: ", datetime.now())
                            print("  Current Speed:  %d degrees/second" % speed)
                            sleep(1)

                    atl.stop()
                except:
                    print("Rate table operation halted. We'll blame Joe Nguyen or Josh Gibson")
                    startButton.config(state=tkinter.NORMAL)
                    atl.stop()
                    sleep(2)
        except:
            print("There was a com port error. Please check the com port and try again.")
            testRunning = False
            startButton.config(state=tkinter.NORMAL)
            return
    #set global variable to stop the rate table if stop button is clicked
    def stopClicked():
        startButton.config(state=tkinter.NORMAL)
        global testRunning
        testRunning = False
    #run sweep on separate thread when start is clicked
    def startClicked():
        t1 = threading.Thread(target=runSweep, daemon=True)
        t1.start()
    #loop to update time in separate thread
    def update_time():
        while True:
            sleep(1)
            lblCurrentTime2.configure(text=datetime.now().strftime("%H:%M:%S"))

    #set up button associations
    startButton = Button(window, text="Start Test", command=startClicked)
    startButton.grid(column=0, row=4)
    stopButton = Button(window, text="Stop Test", command=stopClicked)
    stopButton.grid(column=1, row=4)
    #starts thread to update in app timer
    t2 = threading.Thread(target=update_time, daemon=True)
    t2.start()
    window.mainloop()












class IdealAerosmithTable:
    def __init__(self, port, debug=False):
        self.serial = serial.Serial(port)
        self.debug = debug
        self.buffer = ''
        self.eatReturn = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.serial.close()

    def readline(self):
        while '\r' != self.buffer[-1:]:
            self.buffer += self.serial.read(1)
        line = self.buffer.strip()
        self.buffer = ''
        return line

    def request(self, buf):
        if self.debug:
            print(buf)
        self.serial.flush()
        if self.eatReturn:
            cmd1 = 'STA\r\n'
            self.serial.write(cmd1.encode())
            self.serial.flush()
            line = self.readline()
            if self.debug:
                print(line)
            line = self.readline()
            if self.debug:
                print(line)
            self.eatReturn = False
        cmd2 = '%s\r\n' % buf
        self.serial.write(cmd2.encode())
        self.serial.flush()
        response = self.readline()
        if self.debug:
            print(response)
        prompt = self.readline()
        if self.debug:
            print(prompt)
        return response

    def setAcceleration(self, degreesPerSecondSquared):
        self.request('ACL%d' % degreesPerSecondSquared)

    def setDirection(self, clockwise):
        self.request('DIR1' if clockwise else 'DIR0')

    def setHomeOffset(self, degrees):
        self.request('HOF%f' % degrees)

    def isMoving(self, tolerance=1):
        return False if '1' == self.request('MCO%d' % tolerance) else True

    def getPosition(self):
        return float(self.request('PPO'))

    def getVelocity(self):
        return float(self.request('PVE'))

    def relationalMove(self, position):
        self.request('RMO%d' % position)

    def saveSettings(self):
        self.request('SAV')

    def getStatus(self):
        return int(self.request('STA'))

    def setVelocity(self, degreesPerSecond):

        self.request('VEL%d' % degreesPerSecond)

    def setZero(self, degrees):
        self.request('ZER%d' % degrees)

    # motion commands
    def home(self):
        self.request('HOM')

    def jog(self, degreesPerSecond):
        line = 'JOG%d' % degreesPerSecond
        if self.debug:
            print(line)
        cmd3 = '%s\r\n' % line
        self.serial.write(cmd3.encode())
        self.serial.flush()
        self.eatReturn = True

    def move(self, position):
        self.request('MOV%d' % position)

    def stop(self):
        cmd = 'STO'
        self.serial.write(cmd.encode())
        sleep(1)
        self.serial.flush()

    # sinusoidal motion operations
    def setAmplitude(self, degrees):
        self.request('AMP%f' % degrees)

    def setFrequency(self, hertz):
        self.request('FRQ%f' % hertz)

    def setPeriod(self, seconds):
        self.request('PER%d' % seconds)

    def setNumberOfCycles(self, cycles):
        self.request('CYC%d' % cycles)

    def start(self):
        line = 'SGO'
        if self.debug:
            print(line)
        cmd = '%s\r\n' % line
        self.serial.write(cmd.encode())
        self.serial.flush()
        self.eatReturn = True

    def sinusoid(self, amplitude, frequency, cycles=0):
        self.setAmplitude(amplitude)
        self.setFrequency(frequency)
        self.setNumberOfCycles(cycles)
        self.start()


if __name__ == "__main__":
    main()

