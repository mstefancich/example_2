# minimal package dependencies verification
# deps_bootstrap.py
import subprocess, sys, os, time, socket
from pathlib import Path

BASE_DIR =Path('/home/pi') # hardcoded... bad..
os.chdir(BASE_DIR)
print("Base dir:", BASE_DIR)

REQ_FILE = Path("/home/pi/requirements.txt")
FLAG_FILE = Path("/home/pi/requirements_satisfied.txt")

def wait_for_dns(host="pypi.org", timeout=120, interval=2):
    t0 = time.time()
    i=0
    while time.time() - t0 < timeout:
        try:
            socket.gethostbyname(host)
            return True
        except OSError:
            print("DNS not ready at: ",time.asctime())
            i=i+1
            try: # attempting to put something on screen without any library
                subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", str(i+10), "--y", "130", "--t", ".", "--f", "3"],check=True)
            except:
                pass # nevermind...

            time.sleep(interval)
    print("Timeout while waiting for DNS at:",time.asctime())
    return False

def ensure_requirements():
    # read current flag
    current=""
    if FLAG_FILE.is_file():
        try:
            current = FLAG_FILE.read_text().strip() if FLAG_FILE.exists() else ""
        except:
            pass
    else:
        print("Flag File does not exist")

    if current == "True":
        print("Requirements already satisfied, skipping install")
        return

    if (not REQ_FILE.is_file()):
        print("Requirements.txt does not exist.")
        print("Unable to test for requirements")
        return(-1)
        
    print("Installing/updating dependencies...")

    try: # attempting to put something on screen without any library
        subprocess.run(["/home/pi/fbdisplay/clearscreen"],check=True)
        subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", "20", "--y", "10", "--t", "Updating", "--f", "3"],check=True)
        subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", "20", "--y", "50", "--t", "dependencies", "--f", "3"],check=True)
        subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", "20", "--y", "90", "--t", "be patient...", "--f", "3"],check=True)
    except:
        pass # nevermind...
    # wait up to 1 minute for DNS
    if not wait_for_dns():
        print("Network/DNS not ready; skipping requirements install for now")
        try: # attempting to put something on screen without any library
            subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", "20", "--y", "130", "--t", "DNS failure", "--f", "3"],check=True)
            subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", "20", "--y", "170", "--t", "Skipping update", "--f", "3"],check=True)
        except:
            pass
        return False
    
    try:
        #subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(REQ_FILE)])
        cmd = [sys.executable, "-m", "pip", "install", "--no-input", "-r", str(REQ_FILE)]
        r = subprocess.run(cmd, check=True, text=True, stdout=sys.stdout, stderr=sys.stderr)
    except Exception as e:
        print("Unable to test for requirements: ",e)
        return(-1)

    try:
        subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", "20", "--y", "130", "--t", "Done!", "--f", "3"],check=True)
    except:
        pass

    # mark as satisfied
    FLAG_FILE.write_text("True\n")
    print("Dependencies installed, flag file updated")

if __name__ == "__main__":
    try:
        ensure_requirements()
    except:
        print("Unable to verify status of needed libraries")


# now we import the other standard packages
import pprint, zipfile
import http.client
import asyncio, json
from random import uniform as un
from time import sleep
#import time
#import socket
#subprocess
import re, datetime, importlib

#now we import the packages we just updated
extra_packages=['websockets','requests','pigpio','packaging']

for name in extra_packages:
    try:
        globals()[name] = importlib.import_module(name)  # attach so you can use `requests.get`, etc.
    except Exception as e:
        print("Unable to import: ",name)
        print("With error: ",e)
 
# import websockets
# import requests
# # for the on-board hardware elements
# import pigpio
# import packaging

try:
    from gpiozero import MCP3008
except:
    print("Failed to import MCP3008 from gpiozero")
try:
    from PIL import Image
except:
    print("Failed to import Image from pil")
try:
    from packaging import version
except:
    print("Failed to import version from packaging")
    
#import numpy not needed here
#import matplotlib not needed here
# import scikit-image not needed here

# Force working directory to the home directory /home/pi regardless of the way the
# script was started (either as service or from command line) and where from
# try:
#     script_dir = os.path.dirname(os.path.abspath(__file__))
# except NameError:
#     # fallback: use current working directory
#     script_dir = os.getcwd()

# adds an entry to the import path, avoids duplication
def _front(path):
    #Put path at the *front* of sys.path (deduping if needed).
    p = str(path)
    while p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

# Ensure the same two roots are always first:
_front(Path('/home/pi/.local/lib/python3.9/site-packages/'))
_front(BASE_DIR / "local_packages") # adds it at the beginning, so it always wins
_front(Path.cwd())                  # the current working dir (now /home/pi)
_front(BASE_DIR)                    # explicitly /home/pi (redundant but harmless)

    
# # debugging.. comparing paths
# print("sys.path:")
# try:
#     pprint.pprint(sys.path)
# except:
#     print(sys.path)



ModuleProblem=False # will change to true any time a problem appears in import

# added may 9th 2025 a set of functions handling the SPI display
try:
    #from local_packages.DisplayFunctions import clearScreen, writeText, displayImage
    #from local_packages import DisplayFunctions
    #print("Display function source: ",DisplayFunctions.__file__)   # full path to the module/package
    from local_packages.DisplayFunctions import *
except Exception as e:
    print("Errors in importing local_packages.DisplayFunctions *: ",e)
    ModuleProblem=True
    

# added Sept 8th for the GerberTranslator part
try:
    from local_packages.config_dir import ConfigFile
    ConfigDir=ConfigDir = BASE_DIR / "local_packages" / "config_dir"
    global ConfigDict, OldConfigDict
    ConfigDict=ConfigFile.dict
    OldConfigDict=ConfigFile.dict
except Exception as e:
    print("Error in importing ConfigFile: ",e)
    ModuleProblem=True

try:
    import local_packages.GerberTranslator_1_4_3_integrated as Translator
except Exception as e:
    print("Error in importing local_packages.Gerbertranslator: ",e)
    ModuleProblem=True

try:
    import local_packages.G_CodeGenerator_1_2_1_integrated as GcodeGenerator
except Exception as e:
    print("Error in importing Gcode generator: ",e)
    ModuleProblem=True

# added 25 Sept 2025 for SVG translator
try:
    import local_packages.SVGTranslator_5_5 as SVGTranslator
except Exception as e:
    print("Error in importing local_packages.SVGTranslator: ",e)
    ModuleProblem=True


# added 12th August 2025 to handle the waitForIpAddress() function in case of AP mode
# also added to handle the request of available WiFi
PREFERRED_IFACES = ("wlan0", "uap0", "ap0", "eth0")  # adjust to your setup

# end of 12th August 2025 addition

# global variables for auto-updating from git repo
# can be sustained this way only if few systems are attached
#remDir="https://mstefancich.github.io/example_2/" # until version 20250921_1
remDir="https://mstefancich.github.io/UpdateFolder/" # from version 20250921_2
remIndexFile=remDir+"README.md"
#the following are the base names of the elements to update
fileNameRoot='Websocket_Backend_4_' # the files of interest must start with this root
pageFileNameRoot='index_'
dst = "/var/www/html/index.html" # this is the target for the webpage
downloadFolder="." # dangerous as it is not an absolute path e.g. /home/pi
localFileName="" # will contain the fully qualified path of it and is the target of the  updated symlink
symlink_path = "controller.py" # the code is run from a symlink placed in /home/pi
# Added 1st September 2025 - AutoUpdater
# CheckAndUpdate() moved inside main as it needs to run only if a connection is available
# verifies if updates are available (based on names) and if so gets and updates


# version control
#print("Version 9 May 2025 17:00")
print("Version 21st September 2025 11:00")
try:
    print("Symlink path:", __file__)
    print("Resolved path:", os.path.realpath(__file__))
except:
    pass

#debug Screen Print
# clearScreen()
# writeText("117 Symlink part done",pos=(50,20))
# sleep(1)


# Here we want to send continuously data to a client using websockets and, at the same time,
# receive and manage the messages being sent by the client to the server via the same channel.
# Here we also add a file selection field in the client and a websocket based
# file upload process from the client (working at least for text files)
# 
# on May 12 we try to add an async write_WS(queue,websocket) task that writes out the data that are put in the queue
# We, at the same time, remove all the part from handle_WS where is writes out stuff, using the queue instead
# more info: https://docs.python.org/3/library/asyncio-queue.html
# 
# It works as intended, now, to write out a message, any routine has simply to FrontEndQueue.put_nowait("whatever it wants")
# and the write_WS will dispatch it
# 
# NB: client disconnection is handled somewhat gracefully now with the systems returning to a wait state and allowing for
# a new client connection
# 
# Multiple connections are not supported as of now (would not be too difficult but the queues should indicate which
# websocket sent the message or to which one the message is destined...).
# 
# On May 18th we added a function called ELECTRICALS(I,HV,LV) that sends, via the usual JSON method, a list of the system
# electrical data (in order, Current in mA, High Voltage in Volt, Drain Voltage in Volt) that is exposed by the client
# (Buttons_on_table_1.html) in the relevant cells on the monitoring section of the page.
# 
# The function is, currently, invoked periodically by the main with random numbers as parameters
# (easily solved once the data come in).
# 
# The file upload function works (solely for text files) and the file print part as well (the interface with the printer is
# not currently implemented at the server side).
# 
# The pump and generator command are not implemented in term of ws messages at neither client nor server side
# but the keys and controls are bound (in the client) to the send function (currently they just print an alert)
# 
# The printer controls (as of May 19th) are now implemented and commands can be sent to the printer by simply pushing
# them in the "Printerws" queue in the format {'command':'G00 X 20'} [e.g. PrinterQueue.put_nowait("G00 X "+"20") ]
# The http session is kept open (we need to take care of clising it when we shut down operations)
# 
# May 20: added some minor Exceptions handling points and streamlined the code a bit.
# 
# June 11th:
# We decided to embed the commands for pumps and generator inside the G-code file as M118 (Serial Print)
# G-code commands.
# This allows us to avoid printer-generator-pump synchronization problems (as everything is handled at the Printer
# side).
# The printer will issue, with a "echo: CMD:" header, the commands with the same format being used by the
# front-end. This incoming commands will be received by "async get_data_Printer(auth): " function and, when the
# proper header is identified, the command will be parsed and injected in the commands pipe as it is done with
# those coming from the front-end.
# This is done simply, after stripping the header, by invoking the function "parse_data(incoming_command_string)"
# as done by "async handle_WS(websocket, uri):" for those coming from the front-end.
# Example:
#             # the intended command is: "GEN_SET_CURRENT: 25"
#             # the G-code will look line: "M118 E1 CMD:GEN_SET_CURRENT: 25" (note the CMD:)
#             # the returning line will look like "Recv: echo:CMD:GEN_SET_CURRENT: 25"
# For a full list of commands and formats see "Front End messages for reference" in this file
# The beauty of this approach is that the command processing pipeline remains the same regardless of the command
# source.
# 
# BUG?: The only drawback, at this time, is that when a command is receied from the printer, the front-end page is not
# updated with the relevant values
# 
# Added a function UploadFileToPrinter(FileName='test.gcode') that is invoked when, in the
# front-end, a file is uploaded from the remote client.
# This function uses the Octoprint POST API to upload
# the selected file to the Octoprint upload dir, making it available for a subsequent Print command.
# The uploaded file is not automatically marked for printing...
# 
# The file is then selected in Octoprint for printing via SelectFileInPrinter(FileName)
# when the "select file to print" field is set in the Front End.
# 
# Finally, the above selected file is printed when the front end button "Initiate Print" is
# pressed. This is done via the function StartPrintInPrinter().
# 
# The implementation has some very basic error control and works only with files having ".gcode" extension.
# A comprehensive Exception handling is due...
# 
# June 12th
# We integrate now, in version 4 of the backend, the hardware controls for the pump (via http requests) [DONE]
# We integrate then the codes for the on board hardware (HV generator and Current controller) as created in
# C:\Users\Marco\Documents\Python - Hardware Modules on RPi\Hardware_controller.py that does work on the RPI
# 
# June 13th:
# added the part relative to the Current Controller
#
# Dec 4th 2024:
# we are picking up this code again and reworking the section defining the commands for the printer.
# we create a new code version being Websocket_Backend_4_20241204 where we can apply modifications.
# dec 7th 2024:
# corrected the parser of the commands coming from the M118 backchannel from the printer as it would not capture the new
# data format generated by the G-code generator.
# May 9th 2025:
# added the import of local_packaged DisplayFunctions.py package containing  tested functions to output text
# and graphical object to the SPI display
# see "Update 12th Jan 2025 - GUI on the SPI display" for details on the functions
# clearScreen, writeText, displayImage, displayRectangle, setCursor
# as of August 20th, a new method to detetermine the pump IP is defined.
# with the controller in WiFi client mode (and answering to "raspberrypi2B.local")
# the pump, when connected to the same WiFi, will send a GET request to the server
# that (via CGI Scripts) will be forwarded via WS as "CallFromPump 102.x.x.x"
# the Backend from 20th August onward will handle this and set the proper pump address
# from 1St september 2025 the code will auto-update from github repo if
# a code with a more recent version number is there uploaded and linked in
# the README.md document.
# for details of the code, see the project "Auto_Updater" in my local folders
# and also on the RPI
# On Sept 8th we start with the integration of the gerber translator (GerberTranslator_1_4_2.py)
# and gcode generator (G_CodeGenerator_1_1_1.py) in the system.
# The webpage (from version index_20250906_1.html) returns a command "TRANSLATOR_PARAMETERS: "
# followed by a json document containing a set of keyowrds corresponding to the
# converter and generator parameters as stored in ConfigFile.py
# so we need first to intercept the command, extract the parameters and uodate the
# dict contained in the ConfigFile.py (that rests in the subdir "config_dir")
# done on Sept 9th for both the Gerber translator and the Gcode Generator
# some extra directories need to be generated 

UPLOAD_FOLDER = '/home/pi/uploads/' # it is an absolute path
try: # let's make the dir if it does not exist
    os.makedirs(each, exist_ok=True)
except:
    pass

#UPLOAD_FOLDER = "C:\\Users\\Marco\\Downloads\\Upoads"
PUMP_IP='0.0.0.0' # Assigned via notification when pump is connected
PUMP_PORT='80'

i=1
websocket_list=set()
target_set=set()
message_received=0
FileNameToPrint="" # as returned from the client
FileName="" # used as a temporary storage between two calls to the FileUpload function
J={} # dict object that will contain the printable file names in the upload directory
end_in_sight=False
PrinterMoveRelative=False
PrinterHTMLConnection=""
outMessage=""
PrinterConnected=False # set to true to enable all the process part relative to the printer
ProcessShutDown=False # set to perform a main based cleanup upon code termination. TO BE IMPLEMENTED
PackageUpdated=False # this is set when any of the necessary packages are installed or updated

# Keywords to Functions connection for Front End to Back End interaction 
keywords=["BUTTON_1: ","BUTTON_2: ","FILE_NAME: ","SELECT: ",
          "START_PRINT","GEN_SET_","PUMP_SET_","PRINTER_","RequestWifiList",
          "{\"type\":\"wifi_config\"","CallFromPump","SHUTDOWN_SYSTEM",
          "TRANSLATE: COMMAND", "TRANSLATOR_PARAMETERS: ","CHECK_DEPENDENCIES"]
functions=["BUTTON_1_pressed","DIR_command","Receive_file","Select_local_file",
           "Initiate_print","SetGenerator","SetPump","ControlPrinter","scan_wifi_ssids",
           "wifi_config","CallFromPump","shutdown_system","translateFile","setTranslatorParameters","CheckDependencies"]



# this is the list of identifiers that the client prepends to messages coming from different
# sources and that we will use to trigger the right function and remove from the messages themselves
# the corresponding (by position) list of function is invoked when the corresponding indicator is found
# this is done by the function parse_data() that is a basic a command interpreter where each
# identifier is actually a command (so we should use proper "commands-like-names" for each identifier

OCTOPRINTUSER="OctoAdmin"
OCTOPRINTPASS="H725d548r"
OCTOPRINTAPI_KEY="58612A874FD343C6810532DD1C169DA5"
#OCTOPRINTHOST="raspberrypi2b.local" #does not work if network does not resolve names
OCTOPRINTHOST="127.0.0.1" # as octoprint runs in any case from the local system
OCTOPRINTPORT=5000 # port can be 80 or 5000
#OCTOPRINTuri = "ws://raspberrypi2b.local:5000/sockjs/websocket" # dangeous as rests on name resolution
OCTOPRINTuri = "ws://127.0.0.1:5000/sockjs/websocket"
Printerws="" # global handle to the printer websocket

# on board hardware definitions
# generic mnemonic
OFF = False
ON = True
LOW = 0
HIGH = 1

# list of relevant GPIO_pins with mnemonic names
HV_DIS = 4
HV_V_SEL = 23
HT_EN= 26
ADC_CS = 6
TP_CS = 7
LCD_CS = 8
PWM_IN = 18 # PWM pin to the current controller
RPI_Freq = 50000 # frequency on the PWM_IN pin
ADC_V_REF=3.2999 # Vref provided to the ADC that should correspond fo a reading of 1
#HV_scaling = 0.01028 # theoretical scaling value of HV by the resistive divider.
HV_scaling = 0.010576 # effective scaling based on multimeter measurements
MV_scaling = 0.00985 # from some preliminary measurements.... unreliable
I_scaling = 2.317 # from some preliminary, indirect, measurements. Unreliable
V_DRAIN=1
V_GEN=2
I_D=0

# intial status
GEN_HV=HIGH
GEN_ON=OFF

# END of on board hardware definitions 

# different subscription models depending on how much, and which, data we want.
# change the "subscription" in the get_data() coroutine

subscription={"subscribe":{ "current":True}}
#      "logs": "^Recv: Cap",
subscription1={
  "subscribe": {
    "state": {
      "logs": "^Recv: ",
      "messages": False
    },
    "events": False,
    "plugins": False
  }
}
subscription2={
  "subscribe": {
    "plugins": ["example"]
  }
}




### routine to restart, rests on subprocess

def restart_self_systemd(unit="myscript.service"):
    print(">>>> After package installation")
    print(">>>> System needs restart...")
    try:
        sleep(2)
        sys.stdout.flush(); sys.stderr.flush()
    except Exception:
        pass
    # Ask systemd to restart this unit and exit quickly
    try:
        clearScreen()
        writeText("After packages update",text_color=0b0000011111100000,pos=(10,20))
        writeText("Code needs to restart..",text_color=0b0000011111100000,pos=(40,20))
        sleep(3)
    except:
        pass
    print("trying to restart the process..")
    try: # attempting to put something on screen without any library
        subprocess.run(["/home/pi/fbdisplay/clearscreen"],check=True)
        subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", "20", "--y", "10", "--t", "Restarting", "--f", "3"],check=True)
        subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", "20", "--y", "50", "--t", "be patient...", "--f", "3"],check=True)
    except:
        pass # nevermind...

    try:
        subprocess.Popen(["/bin/systemctl", "--no-block", "restart", unit])
        sleep(0.2)
        os._exit(0)
    except:
        print("Failed to restart..")
        print("Attempting to reboot")
        try:
            clearScreen()
            writeText("Failed to restart service",text_color=0b0000011111100000,pos=(10,20))
            writeText("Rebooting the full system",text_color=0b0000011111100000,pos=(40,20))
        except:
            try: # attempting to put something on screen without any library
                subprocess.run(["/home/pi/fbdisplay/clearscreen"],check=True)
                subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", "20", "--y", "10", "--t", "Restart failed", "--f", "3"],check=True)
                subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", "20", "--y", "50", "--t", "Robooting...", "--f", "3"],check=True)
            except:
                pass # nevermind...
        try:
            subprocess.run(["/sbin/shutdown", "-h", "now"], check=True)
        except Exception as e:
            print(f"Shutdown failed: {e}")
            try:
                writeText("Failes shutdown",text_color=0b0000011111100000,pos=(70,20))
                writeText("Turn system off and on",text_color=0b0000011111100000,pos=(100,20))
                writeText("manually please...",text_color=0b0000011111100000,pos=(130,20))
            except:
                try: # attempting to put something on screen without any library
                    subprocess.run(["/home/pi/fbdisplay/clearscreen"],check=True)
                    subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", "20", "--y", "10", "--t", "Reboot failed!", "--f", "3"],check=True)
                    subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", "20", "--y", "50", "--t", "Turn off", "--f", "3"],check=True)
                    subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", "20", "--y", "90", "--t", "... and ON", "--f", "3"],check=True)
                    subprocess.run(["/home/pi/fbdisplay/fbtext", "--x", "20", "--y", "130", "--t", "manually", "--f", "3"],check=True)
                except:
                    pass # nevermind...
            

#def ensure_package # Removed from Version 20250921_1



def fixPackages():
    if not ModuleProblem:
        print("Modules import ok, no package upgrades are needed")
        return(0)
    try:
        clearScreen()
        writeText(text="Some packages needs update..",text_color=0b0000011111100000,pos=(10,20),angle=0)
        # be sure that the packages used by ensure_package exist
        writeText(text="checking importlib",text_color=0b0000011111100000,pos=(40,20),angle=0)
    except:
        pass
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "importlib"])
    except:
        pass
    try:
        writeText(text="checking packaging",text_color=0b0000011111100000,pos=(70,20),angle=0)
    except:
        pass
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "packaging"])
    except:
        pass
    try:
        writeText("done",text_color=0b0000011111100000,pos=(100,20))
        sleep(3)
    except Exception as e:
        print("Exception while writing to screen in fixPackages: ",e)
    print("done with fixPackages")
    # at the end of this, if any update has been performed
    # the global variable PackageUpdated is True, otherwise remains False
    try:
        # as some package has been updated, it is better to restart the service
        # and reload everything
        restart_self_systemd()
    except:
        pass
    

### Routines for ON-BOARD hardware subsystems: HV generator, Current Controller and ADC module

def GPIO_init():
    global RPi, ADC0, ADC1,ADC2
    #GPIO.setup(HV_DIS,GPIO.OUT)
    #GPIO.setup(HV_V_SEL,GPIO.OUT)
    #GPIO.setup(HT_EN,GPIO.OUT)
    # the ADC is set on the second SPI channel, here we use software SPI
    ADC2 = MCP3008(channel=2, clock_pin=21, mosi_pin=20, miso_pin=19, select_pin=6)
    ADC1 = MCP3008(channel=1, clock_pin=21, mosi_pin=20, miso_pin=19, select_pin=6)
    ADC0 = MCP3008(channel=0, clock_pin=21, mosi_pin=20, miso_pin=19, select_pin=6)
        
    RPi=pigpio.pi()   # Define pwmobj as pigpio.pi()
    RPi.set_mode(PWM_IN, pigpio.OUTPUT)
    RPi.set_mode(HT_EN, pigpio.OUTPUT)
    RPi.set_mode(HV_DIS, pigpio.OUTPUT)
    RPi.set_mode(HV_V_SEL, pigpio.OUTPUT)
    RPi.set_mode(ADC_CS, pigpio.OUTPUT)
    RPi.set_mode(LCD_CS, pigpio.OUTPUT)
    RPi.set_mode(HV_V_SEL, pigpio.OUTPUT)

def HT_switch(status=OFF):
    #GPIO.output(HT_EN,int(status)) # active high
    RPi.write(HT_EN, int(status)) # active high
        
def HV_gen(status=OFF,voltage=LOW):
    #GPIO.output(HV_DIS,int(not status)) # active low
    #GPIO.output(HV_V_SEL,int(voltage)) # high voltage at high logic value    
    RPi.write(HV_DIS,int(not status)) # active low
    RPi.write(HV_V_SEL,int(voltage)) # high voltage at high logic value    

def CURRENT_set(Current=0.0): # current in mA
    # a better calibration must be done but for now a simple formula is used
    DC=int(100.0*Current/97.0)
    if(DC>100):
        DC=100
    if(DC<0):
        DC=0
# modified 10 Jan 2025 to adapt to correct for a current setting issue
# on Motherboard_V3 20241022
    res=RPi.hardware_PWM(PWM_IN, RPI_Freq, DC * 1000)
    if (int(res)==0):
        print("PWM set Success")
    else:
        print("ERR!!: PWM Set failed with code: ",res)

def ADC_read(LineToRead=-1):
    if LineToRead==2:
            #print("Reading Value 2: "+str(ADC2.value*ADC_V_REF/HV_scaling))
            return(ADC2.value*ADC_V_REF/HV_scaling)
    if LineToRead==1:
            #print("Warning: reporting unscaled measured voltage")
            #print("Reading Value 1: "+str(ADC1.value*ADC_V_REF/MV_scaling))
            return(ADC1.value*ADC_V_REF/MV_scaling)
    if LineToRead==0:
            #print("Warning: reporting unscaled measured voltage")
            #print("Reading Value 0: "+str((ADC0.value*ADC_V_REF/I_scaling)*1000))
            return(ADC0.value*ADC_V_REF/I_scaling)*1000 # in mA
    return(-1) 

def meanI_D(nr=100):
    IT=0
    for i in range(0,nr):
        IT=IT+ADC_read(I_D)
    return(IT/nr)

def meanV_D(nr=100):
    IT=0
    for i in range(0,nr):
        IT=IT+ADC_read(V_DRAIN)
    return(IT/nr)

def meanV_GEN(nr=100):
    IT=0
    for i in range(0,nr):
        IT=IT+ADC_read(V_GEN)
    return(IT/nr)


### END of Routines for ON-BOARD hardware subsystems


def UploadFileToPrinter(FileName=''):
   FullFileName=UPLOAD_FOLDER+"/"+FileName # system dependent!
   print("Full File Name is: "+FullFileName)
   FileHandler=open(FullFileName, 'rb')
   print("File Handler is: "+str(FileHandler))
   fle={'file': FileHandler, 'filename': FileName}
   url='http://localhost:5000/api/files/{}'.format('local')
   payload={'select': 'false','print': 'false' } # if I put 'print': 'true' the print starts immediately
   header={'X-Api-Key': OCTOPRINTAPI_KEY }
   response = requests.post(url, files=fle,data=payload,headers=header)
   if response.ok:
       print("Success uploading to server")
   else:
       print("Error uploading to file:")
       print(response)    
#  print(response,type(response),response.ok,response.text)

def SelectFileInPrinter(FileName=''):
   location='local/'+FileName # verified. If different I get [400] "No file to upload and no folder to create"
   print("SELECTED FILE NAME=: "+location)
   #location='local'
   url='http://localhost:5000/api/files/{}'.format(location)
   print("Octprint file URL is: ",url)
   header={'Content-Type': 'application/json' , 'X-Api-Key': OCTOPRINTAPI_KEY }
   # verified the API_KEY, if changed I get unauthorized
   #payload={'select': 'true' } # getting 400: "The browser (or proxy) sent a request that this server could not understand."
   #payload={'command': 'select' , 'print': 'True' } # getting 400: "The browser (or proxy) sent a request that this server could not understand."
   #payload={'command': 'select' } # getting 400: "The browser (or proxy) sent a request that this server could not understand."
   #payload={'command': 'select'} # getting 400: "The browser (or proxy) sent a request that this server could not understand."
   # if the selection box is cleared, the file is unselected from octoprint TODO
   payload=json.dumps({'command': 'select'}) # works as intended..... it NEEDS to be a JSON
   response = requests.post(url, data=payload, headers=header)
   print(response,type(response),response.ok,response.text)
       
def StartPrintInPrinter(FileName=''):
   url='http://localhost:5000/api/job'
   # verified, if changed I get a 404: NOT FOUND, I added the {} and got 404, .format(local) seems to make no diff
   header={'Content-type': 'application/json' , 'X-Api-Key': OCTOPRINTAPI_KEY }
   # verified the API_KEY, if changed I get unauthorized
   # not sure if 'content-type' is needed/ problematic
   payload={'command': 'start' }
   payload=json.dumps({'command': 'start' }) # does WORK!!!! F@@K... the header MUST be just a dict
   # BUT THE PAYLOAD MUST BE A REAL JSON!
   response = requests.post(url, data=payload, headers=header)
   print(response,type(response),response.ok,response.text)
   

# added August 12 2025 for the provisioning process.
#this function formats the ssids list in a format suitable for the frontend
def make_wifi_scan_result(ssids):
    # de-dup, drop empties, sort
    uniq = sorted({s.strip() for s in ssids if s and s.strip()})
    payload = {
        "type": "wifi_scan_result",
        "networks": [{"ssid": s} for s in uniq]   # rssi/security omitted
    }
    return json.dumps(payload)

# version of August 12th 2025 to handle the case of AP mode
def get_ip_address():
    """
    Return the most relevant IPv4 address:
    - Prefer dynamic (DHCP) IPs
    - Fallback: static IPs (AP mode)
    Works in both client and AP modes.
    """
    try:
        out = subprocess.check_output(["ip", "-4", "-o", "addr", "show"], text=True)
    except Exception:
        return "127.0.0.1"

    ips_by_iface = {}
    for line in out.splitlines():
        m = re.search(r"^\d+:\s+(\S+)\s+inet\s+(\d+\.\d+\.\d+\.\d+)/", line)
        if not m:
            continue
        iface, ip = m.group(1), m.group(2)
        if ip == "127.0.0.1":
            continue
        dynamic = " dynamic " in line  # detect DHCP-assigned IPs
        ips_by_iface.setdefault(iface, []).append((ip, dynamic))

    for name in PREFERRED_IFACES:
        if name in ips_by_iface:
            # prefer dynamic IPs
            dyn_ips = [ip for ip, dyn in ips_by_iface[name] if dyn]
            if dyn_ips:
                return dyn_ips[0]
            # fallback: first static
            return ips_by_iface[name][0][0]

    # fallback: any IP, prefer dynamic
    for lst in ips_by_iface.values():
        dyn_ips = [ip for ip, dyn in lst if dyn]
        if dyn_ips:
            return dyn_ips[0]
        if lst:
            return lst[0][0]

    return "127.0.0.1"


# this routine switches from AP to WiFi mode once a new WiFi has been added
def switch_to_client_mode():
    # sets a message
    try:
        img = Image.open('/home/pi/local_packages/owl.png')
        displayImage(img)
    except:
        clearScreen()
        
    color=0b0000011111100000
    #writeText("Connecting to Local WiFi",color,(180,20),0) # welcome message
    writeText("Please wait....",color,(230,20),0) # welcome message
    
    subprocess.run(["sudo", "systemctl", "stop", "hostapd"])
    subprocess.run(["sudo", "systemctl", "stop", "dnsmasq"])
    subprocess.run(["sudo", "ip", "link", "set", "wlan0", "down"])
    subprocess.run(["sudo", "ip", "link", "set", "wlan0", "up"])
    subprocess.run([
        "sudo", "wpa_supplicant", "-B", "-i", "wlan0",
        "-c", "/etc/wpa_supplicant/wpa_supplicant.conf"
    ])
    subprocess.run(["sudo", "systemctl", "restart", "dhcpcd"])
    # wisualizes a wait message
    writeText("Connecting to Local WiFi",color,(180,20),0) # welcome message
    #writeText("Please wait....",color,(230,20),0) # welcome message

    # waiting until a WiFi connection is established
    # WARNING: Edge case of ssid with WRONG pawword is not handled gracefully
    ntw=wait_until_connected() # ntw['ip'] may be wrong
    ip=get_ip_address()
    try:
        TextSsid='Network: '+ntw['ssid']
        TextIp='With IP: '+str(ip)
    except:
        TextSsid='Not Connected to WiFi'
        TextIp='No Ip'
    
    # visualizes the new IP on the wifi network
    displayImage(img)
    color=0b0000011111111111
    writeText("Welcome to your new Etcher!",text_color=color,pos=(180,10),dim=20) # welcome message
    writeText(TextSsid,text_color=color,pos=(230,10),dim=20)
    writeText(TextIp,text_color=color,pos=(280,10),dim=20)

    

# this routine reads the priorities of the existing networks and returns the
# next higher priority for a new network
def calculate_network_priority(conf_path="/etc/wpa_supplicant/wpa_supplicant.conf"):
    # sets file permissions to normal ones
    subprocess.run(["sudo", "chmod", "644", conf_path])
    
    result = subprocess.run(
        ["grep", "priority", conf_path],
        capture_output=True,
        text=True)
    q=str(result).split("stdout='")[-1].strip().replace("\\n","\n").replace(" ","")
    q=q.replace("priority=","").splitlines()[0:-1]
    r=[]
    for each in q:
        if each.isdecimal():
            r.append(int(each))
    # protect always the value 99 as it is the fallback "raven" network
    # that must maintain highest priority
    try:
        r.remove(99)
    except: # DANGEROUS may create a security vulnerability
        print("Adding fallback network 'raven' with password 'londra123'")
        add_wifi_network("raven", "londra123", priority=99, conf_path="/etc/wpa_supplicant/wpa_supplicant.conf")
    return(min(max(r)+1,98)) # no priorities can be set higher than 98
    
    
# this function resting on the OS command "sudo iw dev wlan0
# the dummy parameter is needed as the function is called from handle_ws as the other
# function and the call format adds a parameter (even if none is needed here)
def scan_wifi_ssids(dummy): 
    #print("Invoked RequestWifiList")
    try:
        output = subprocess.check_output(
            ["sudo", "iw", "dev", "wlan0", "scan"], text=True
        )
    except subprocess.CalledProcessError as e:
        print("Wi-Fi scan failed:", e)
        return []

    ssids = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("SSID:"):
            ssid = line.split("SSID:", 1)[1].strip()
            if ssid and ssid not in ssids:  # skip hidden & duplicates
                ssids.append(ssid)
    #print(ssids)
    payload=make_wifi_scan_result(ssids) # creates the payload
    print("Debug. SSIDs payloads: ",payload)
    FrontEndQueue.put_nowait(payload)
    return ssids

# this function gets a ssid and password (and possibly a conf_path)
# and adds the network to the wpa_supplicant list
def add_wifi_network(ssid, password, priority=0, conf_path="/etc/wpa_supplicant/wpa_supplicant.conf"):
    block = f'''
network={{
    priority={priority}
    ssid="{ssid}"
    psk="{password}"
}}
'''
    print(block)
    
    # extend file permissions for the update
    subprocess.run(["sudo", "chmod", "666", conf_path])
    print("permission extended")

    with open(conf_path, "a") as f:
        f.write(block)
    print("block added")

    # revert file permissions to normal ones
    subprocess.run(["sudo", "chmod", "644", conf_path])
    print("permission restored")

    # Tell wpa_supplicant to reload without reboot
    subprocess.run(["sudo", "wpa_cli", "-i", "wlan0", "reconfigure"])
    print("wpa_supplicant reloaded")
    
    # tries to switch mode to WiFi
    print("Attempting to switch to WiFi client mode")
    try:
        switch_to_client_mode()
    except:
        print("Switch failed")
        



# this function receives a string of this kind
# ",\"ssid\":\"Wind3 HUB MiriHOME\",\"password\":\"test1\"}"
# and returns a dict like: {'ssid': 'Wind3 HUB MiriHOME', 'password': 'test1'}
# where the ssid and password are those for the selected network.
def wifi_config(param):
    param="{"+param[1:] # getting rid of the initial comma
    wifi =eval(param)
    print("Wifi config received: ",wifi)
    print("Selected Network: ",wifi["ssid"])
    print("Password: ",wifi["password"])
    try:
        priority=calculate_network_priority()
    except:
        priority=0
    print("priority set to: ",priority)
    add_wifi_network(wifi["ssid"],wifi["password"],priority)
    return(wifi)
    

def GetTokenFromOctoprint():
    global OCTOPRINTHOST
    # let's start getting an HTTP session from octoprint to get our one-time authentication token
    # by loggin in with our username and password
    # the returned token is then used to establish the websockets session
    # failure is handled somewhat gracefulyl by printing out errors and trying again (ad  infinitum)
    headers = {'Content-type': 'application/json'}
    data = {'passive': 'true','user':OCTOPRINTUSER,'pass':OCTOPRINTPASS,'remember':'true'}
    json_data=json.dumps(data)
    Connected=False
    # sept 10. Code gets stuck here and loops foerever
    while not Connected:
        connection=http.client.HTTPConnection(OCTOPRINTHOST,OCTOPRINTPORT,timeout=10) 
        try:
            connection.request('POST', '/api/login?apikey='+OCTOPRINTAPI_KEY, json_data, headers)
            response=connection.getresponse()
            data = response.read().decode("utf-8")
            print("Status: {} and reason: {}".format(response.status, response.reason))
            connection.close()
            if response.status==200: # everything went fine 
                json_data=json.loads(data)
                auth={'auth':json_data['name']+":"+json_data['session']}
                Connected=True # as we now have it, we can get out
            else:
                print("I got an unexpected response while attemoting to connect to Octoprint Server")
        except Exception as er:
            print("Failed with: "+str(er))
            # this is a workaround...
            OCTOPRINTHOST="127.0.0.1"
        if not Connected:
            print("Retrying in 10 seconds")
            sleep(10)
            # TODO Check as it seems that, if it gets here, it gets stuck forever
            # actually, the entire OS goes down! 
    return(auth)

    
async def get_data_Printer(auth):
    # here we connect to the ws and wait for incoming data.
    # when data come in, we (as of now) print them out.
    # in the meantime, the main coroutine is running happily unaware of the get_data existance
    if(auth==""):
        print("No Auth token available for websocket connection: terminating")
        return(-1)
    async with websockets.connect(OCTOPRINTuri) as ws:
        await asyncio.sleep(0.1)
        await ws.send(json.dumps(subscription1)) # change to see different data amounts and types
        await asyncio.sleep(0.1)
        await ws.send(json.dumps(auth))
        await asyncio.sleep(0.1)
        # now, if everything worked, we have an open websockets session and we can suck out data
        while True:
            # TODO we could place a Exception catcher here as, upon shutdown, this causes error
            data = await ws.recv() 
            try:
                Jdata=json.loads(data)
            except:
                print("Failed to jsonify data...")

            # June 11th: add here some method to capture printer generated strings that, based
            # on the Gcode content, instruct the system to perform tasks (e.g. turn on the current) to
            # non printer system parts.
            # the intended command is: "GEN_SET_CURRENT: 25"
            # the G-code will look line: "M118 E1 CMD:GEN_SET_CURRENT: 25" (note the CMD:)
            # the returning line will look like "Recv: echo:CMD:GEN_SET_CURRENT: 25"
            # for a full list of commands and formats see "Front End messages for reference" in this file            
            JselError=False
            try:
                Jsel=Jdata['current']['logs']
                print("Found!")
            except Exception as e:
                JselError=True
                print("Error in Topic extraction from Jdata: "+str(e))
            if(not JselError):
                for each in Jsel:
                    if (each.find("CMD:")>-1): # pattern found (actually, due to the definition of the topic subscription, this
                        cmd=str(each).split("CMD:")[1] # what follows CMD is the actual command
                        print("!! COMMAND RECEIVED:>> "+cmd)
                        PrinterQueue.put_nowait("M117 Command Received")
                        try:
                            parse_data(cmd) # here is where the cmd causes an effect
                        except Exception as e:
                            print("Exception in command execution: "+str(e))
                    else:
                        pass
                        #print(each)
#             pos=data.find("Send: ") # not sure when this is triggered... is it a remnant? removed on June 11th
#             if pos>=0:
#                 print(">>",data[pos:pos+20])
#                 saved_data=Jdata
#             await asyncio.sleep(0.1)

async def WriteToPrinter(queue):
    # to send commands to Octoprint, the API endpoint is used
    # we need to verify if the printer is availlable, if not we pass
    # otherwise we send stuff to the printer
    headers = {'Content-type': 'application/json'}
    auth_param='/api/printer/command?apikey='+OCTOPRINTAPI_KEY # api key needs to be changed for 
    #connection=http.client.HTTPConnection(OCTOPRINTHOST,OCTOPRINTPORT,timeout=10)
    # verify that connection is possible
    try:
        connection=http.client.HTTPConnection(OCTOPRINTHOST,OCTOPRINTPORT,timeout=10)
        connection.connect()
    except Exception as er:
        print("Initial connection to Octoprint client failed with: "+str(er))
    running=True
    while running: # this variable can be used to terminate gracefully if something goes wrong
        InData = await queue.get()
        # here we build the data sting from the received command
        data = {'command': str(InData)}
        json_data=json.dumps(data)
        #print("DEBUG: Data being sent to printer: "+str(json_data))
        try:
            connection.request('POST',auth_param, json_data, headers)
            response=connection.getresponse()
            responseText=response.read()
            # Use the response.status and response.reason to understand if everythign is going ok or not
            # e.g. "204 NO CONTENT" is a good response, everything is ok
            # e.g. "409 CONFLICT" happens if the printer is off
            # e.g. "403 FORBIDDEN" happens if the apy key is wrong
            if( not response.status == 204):
                print("Warning. While sending command "+json_data+ " Octoprint responded: "+str(response.status)+" "+str(response.reason))
        except Exception as er: # this should happen if the connection to Octoprint itself is lost
            print("Connection to Octoprint failed with: "+str(er))
            print("Command "+json_data+" could not be sent")
            #running=False # breaks out of the write loop if we want so... 
        queue.task_done() # in case we had an error, the command is lost
    connection.close()


''' end of octoprint client part '''

def Initiate_print(data="No Data"):
    if FileNameToPrint=="":
        print("Please select file first")
        return    
    print("Initiating Print! with file: "+FileNameToPrint)
    #SelectFileInPrinter(FileNameToPrint)
    StartPrintInPrinter()
    #print("To Be Implemented")

def DIR_command(data="No Data"): # can be explicitly invoked when receiving the BUTTON_2 command
    # but is automatically invoked when the link with the client is established and when a new file is uploaded.
    # threfore, invoking this explicitly is useless.
    #print("DIR_command invoked")
    global outMessage, J
    J={}
    list_dir=os.listdir(UPLOAD_FOLDER) # this is a list
    i=0 ;
    # '{ "V0":"file_0.txt", "V1":"file_1.txt", "V2":"new.txt", "V3":"anot.txt", "V4":"myf.txt" }'
    for each in list_dir:
        J["V"+str(i+1)]=each
        i=i+1
    json_data=json.dumps(J)
    FrontEndQueue.put_nowait("DIR: "+json_data)
    
def BackupDict(data=""): #backups OldConfigDict
    print(">>> Creating ConfigDict backup")
    # stuck here....
    try:
        BackupFileName = str(datetime.datetime.now().strftime("%Y%m%d_%H%M%S")+'_ConfigFile.py')
        BackupFullFileName=Path(ConfigDir) / BackupFileName
        print("Backup filename created: ",BackupFullFileName)
    except Exception as e:
        print("Error in creating BackupFileName: ",e)
    try:
        with open(BackupFullFileName, "w") as f:
            f.write("dict = " + pprint.pformat(OldConfigDict) + "\n")
    except Exception as e:
        print("Error saving BackupFileName: ",e)
        

def SaveDict(data=""): #Saves ConfigDict
    print(">>> Creating new ConfigDict file -> ConfigFile.py")
    try:
        ConfigDict['ConfigDate']=str(datetime.datetime.now().strftime('%Y_%m_%d'))
        FileName = 'ConfigFile.py'
        FullFileName=Path(ConfigDir) / FileName
    except Exception as e:
        print("Error in creating dict name: ",e)
        return
    try:
        with open(FullFileName, "w") as f:
            f.write("dict = " + pprint.pformat(ConfigDict) + "\n")
        print("Saved ConfigFile")
    except Exception as e:
        print("Error saving Dict: ", e)

def translateFile(data=""):
    print(">>> TranslateFile invoked")
    global verbose
    verbose=1
    # creates the directory structure if needed
    try:
        Translator.setup_dirs(ConfigDict)
        print("Translator.setup_dirs(ConfigDict) OK")
    except Exception as e:
        print("!! Exception in Translator.setup_dirs(ConfigDict): ",e)
    # creates a backup of the dict before modifying it
    try:
        BackupDict()
        print("BackupDict() OK")
    except Exception as e:
        print("!! Exception in BackupDict(): ",e)

    # now we save the actual dict so it can be used from Translator
    try:
        SaveDict()
        print("SaveDict() OK")
    except Exception as e:
        print("!! Exception in SaveDict(): ",e)
        
    # clean up the PublicHTML directory from the previous files
    try:
        target = Path(ConfigDict['PublicHTMLDirectory']) / 'test2.svg'
        target1 = Path(ConfigDict['PublicHTMLDirectory']) / 'test2.png'
        subprocess.run(['rm', '-f', '--', str(target)], check=True)
        subprocess.run(['rm', '-f', '--', str(target1)], check=True)
    except Exception as e:
        print("Unable to remove image files in PublicHTML directory: ",e)
    
    # finally, we should be ready to invoke the translator
    # we should run the correct translator
    # GerberTranslator only if a Gerber file has been provided
    try:
        if(ConfigDict['GERBER']=="True"):
            Translator.translate_Gerber(ConfigDict)
            # show automatically the preview...
            try:
                FrontEndQueue.put_nowait("GERBER Preview is ready!")
            except Exception as e:
                print("Error while sending Preview is ready message to frontend: ",e)

    except Exception as e:
        print("!! Exception in running GerberTranslator from TranslateFile: ",e)
        print("Returning with Failure")
        return(-1)

    try:
        if(ConfigDict['SVG']=="True"):
            # I need to copy the svgfile 'SVGFileName' in 
            # the 'PublicHTMLDirectory' as 'test2.svg'
            print("Copying the SVG in the PublicHTML directory for rendering")
            src = Path(ConfigDict['RootDirectory']) / ConfigDict['SVGFileName'] # source SVG
            dst_dir = Path(ConfigDict['PublicHTMLDirectory'])   # destination dir
            dst_dir.mkdir(parents=True, exist_ok=True) # ensure it exists
            dst = dst_dir / 'test2.svg' # rename on copy
            
            subprocess.run(['cp', '-f', '--', src, dst], check=True)  # -f forces overwrite
            # alternative, if you want to import it...
            # shutil.copy2(src, dst)             
            print("running SVG_translator")
            SVGTranslator.translate(ConfigDict)
            # we want to try and have the preview directly
            # we need to send a proper command to websocket and capture it from the JS
            # in the frontend
            try:
                FrontEndQueue.put_nowait("SVG Preview is ready!")
            except Exception as e:
                print("Error while sending Preview is ready message to frontend: ",e)
            
    except Exception as e:
        print("!! Exception in running SVGTranslator from TranslateFile: ",e)
        print("Returning with Failure")
        return(-1)

    # now we need to run the final Gcode generator
    try:
        GcodeGenerator.Generate_Gcode(ConfigDict)
    except Exception as e:
        print("!! Exception in running G_CodeGenerator from TranslateFile: ",e)
        print("Returning with Failure")
        return(-1)        
    # now we can reissue the DIR command to refresh
    print("Succesfully generated Gcode")
    DIR_command()
    print("returning from translateFile")
    
def setTranslatorParameters(data=""):
    global Jdata
    print(">>> setTranslatorParameters invoked")
    # data contains the raw form data with some excess escapes
    try:
        step1 = data.encode("utf-8").decode("unicode_escape").replace("TRA_","")
        Jdata = json.loads(step1) # transforms in a Json form
        fields = Jdata["fields"] # and now in a dict extracting the data as a dict
    except Exception as e:
        print("Failed json.loads(): "+e)
        return()
    # the current is given in mA but the ConfigDict uses it in A, so we need to
    # rescale it
    #print("Fields: ")
    #print(fields)
    if('NozzleCurrent') in fields:
        try:
            current=float(fields['NozzleCurrent'])/1000.0
            fields['NozzleCurrent']=str(current)
        except Exception as e:
            print("Error while changing the NozzleCurrent field: ",e)
            
    # We now, as of Sept 25th 2025, set the 'GCodeFileName' to be generated by the converter
    # to the value of the Gerver or SVG filename if one of those has been selected
    # as determined by the 'SVG' or 'GERBER' ConfigDict key
    if ('SVG') in fields and fields['SVG']=="True" :
        try:
            GCodeFileName=fields['SVGFileName'].split(".")[0]+'.GCODE'
            fields['GCodeFileName']=GCodeFileName
        except:
            print("Error while trying to update 'GCodeFileName': ", e)
    if ('GERBER') in fields and fields['GERBER']=="True" :
        try:
            GCodeFileName=fields['GerberFileName'].split(".")[0]+'.GCODE'
            fields['GCodeFileName']=GCodeFileName
        except:
            print("Error while trying to update 'GCodeFileName': ", e)
        
    # now we have the dict with the values sent from the frontend
    # we want to change the corresponding fields in the ConfigDict as needed
    #print("Updating Dict: ")
    ## Error is here... ConfigDict seems to be empty!!!!
    #print(ConfigDict)
    ConfigDict.update(fields)
    print("Successfully update ConfigDict")


def SetGenerator(data="No Data"):
    #print("Set Generator Function invoked with param: "+data)
    global GEN_HV, GEN_ON
    param=data.split(": ")
    if (param[0]=='RUN'):
        print("Turn On Generator:"+param[1])
        if param[1].lower()=='true':
            GEN_ON=ON
        else:
            GEN_ON=OFF
        HV_gen(GEN_ON,GEN_HV)
    if (param[0]=='HV'):
        print("Turn On HV voltage:"+param[1])
        if param[1].lower()=='true':
            GEN_HV=HIGH
        else:
            GEN_HV=LOW
        HV_gen(GEN_ON,GEN_HV)        
    if (param[0]=='CURRENT'):
        sss="M117 Curr: "+param[1]
        print("Set Current to: "+param[1])
        PrinterQueue.put_nowait(sss)
        CURRENT_set(int(param[1]))
        
#     match param[0]: # not supported under python 3.9.2 that I have on RPI (why?)
#         case "RUN":
#             print("Turn On Generator:"+param[1])
#         case "HV":
#             print("Turn ON HV voltage:"+param[1])
#         case "CURRENT":
#             print("Set Current to: "+param[1])

# when a get request is received from the pump with "CallFromPump" body, the pump
# IP is updated

def CallFromPump(data=""):
    global PUMP_IP
    param=data.split(": ")[0].strip()
    print("CallFromPump received")
    print("Received From Pump: ",param)
    color=0b0000011111100000
    testo="Pump IP: "+param
    PUMP_IP=param # here we set the value used in the system
    print(testo)
    try:
        writeText(testo, color, (30, 20), 0)
    except Exception as e:
        print("Exception in WriteText:",e)


def SetPump(data="No Data"): # this is necessary as a "glueware" as the format of the responses from the HTML document
    # is different from the one used by the pump. The available pump commands are
    # Pump control is done via http get methods (no auth is implemented) and specifically
    '''
    • http://192.168.178.213/?pump=on 
    • http://192.168.178.213/?pump=off 
    • http://192.168.178.213/?pump=forward 
    • http://192.168.178.213/?pump=reverse 
    the speed is set via a GET method (the value 48.8 can vary between 00.0 and 99.9)
    • http://192.168.178.213/?PWM=48.4&Command_1=SET_SPEED 

    '''
    #print("Set Pump Function invoked with param: "+data)
    cmd='unknown'
    param=data.split(": ")
    #match param[0]: # not supported under python 3.9.2 that I have on RPI (why?)
    #    case "RUN":
    if (param[0]=='RUN'):
        print("Turn On Pump: "+param[1])
        if(param[1]=='true'):
            cmd='/?pump=on'
        else:
            cmd='/?pump=off'
    #    case "DIR":
    if (param[0]=='DIR'):
        print("Turn Forward Direction: "+param[1])
        if(param[1]=='true'):
            cmd='/?pump=forward'
        else:
            cmd='/?pump=reverse'            
    #    case "SPEED":
    if (param[0]=='SPEED'):
        print("Set Speed to: "+param[1])
        cmd='/?PWM='+str(param[1])+'.0&Command_1=SET_SPEED'
    if (not cmd=='unknown'): # now we can send the commands
        print('command is: '+cmd)
        connection=http.client.HTTPConnection(PUMP_IP,PUMP_PORT,timeout=10)
        connection.request('GET', cmd)
        response=connection.getresponse()
        data = response.read().decode("utf-8")
        print("Status: {} and reason: {}".format(response.status, response.reason))
        connection.close()


def ControlPrinter(data="No Data"):
    #print("ControlPump Function invoked with param: "+data)
    global PrinterMoveRelative
    param=data.split(": ")
    #print(param)
    if (not PrinterMoveRelative): # we are threfore operating in relative mode.... dangerous.
        PrinterQueue.put_nowait("G91")
        PrinterMoveRelative=True 
    #match param[0]:
#    case "RIGHT":
    if(param[0]=="RIGHT"):
        #print("Printer Move RIGHT with distance: "+param[1])
        PrinterQueue.put_nowait("G00 X "+str(param[1]))
#    case "LEFT":
    if(param[0]=="LEFT"):
        #print("Printer Move LEFT with distance: "+param[1])
        PrinterQueue.put_nowait("G00 X -"+str(param[1]))
#    case "BACK":
    if(param[0]=="BACK"):
        #print("Printer Move BACK with distance: "+param[1])
        PrinterQueue.put_nowait("G00 Y -"+str(param[1]))
#    case "FORWARD":
    if(param[0]=="FORWARD"):
        #print("Printer Move FORWARD with distance: "+param[1])
        PrinterQueue.put_nowait("G00 Y "+str(param[1]))
#    case "UP":
    if(param[0]=="UP"):
        #print("Printer Move UP with distance: "+param[1])
        PrinterQueue.put_nowait("G00 Z "+str(param[1]))
#    case "DOWN":
    if(param[0]=="DOWN"):
        #print("Printer Move DOWN with distance: "+param[1])
        PrinterQueue.put_nowait("G00 Z -"+str(param[1]))
#    case "HOMEZ":
    if(param[0]=="HOMEZ"):
        #print("Printer Z-axis HOME command received")
        PrinterQueue.put_nowait("G28 Z")
#    case "HOMEXY":
    if(param[0]=="HOMEXY"):
        #print("Printer XY-axis HOME command received")
        PrinterQueue.put_nowait("G28 XY") # retract 1 mm before moving
#    case "SET_ZERO" :
    if(param[0]=="SET_ZERO"):
        #print("Printer Set Origin command received")
        PrinterQueue.put_nowait("G92 X0 Y0 Z0") 
        
            

def ELECTRICALS(data="No Data"):
    global outMessage
    try:
        a=str(data[0])
        b=str(data[1])
        c=str(data[2])
    except:
        a="32.73"
        b="202"
        c="129"
    msg_loc={ "HV_Voltage":b, "DR_Voltage":c, "Current":a }
    json_data=json.dumps(msg_loc)
    #print("Attempting to send: "+json_data)
    FrontEndQueue.put_nowait("ELECTRICALS: "+json_data)    

def Select_local_file(data="No Data"):
    global FileNameToPrint
    print(">> Select_local_file COMMAND invoked!")
    data=data.strip()
    #print("Select_local_file param is: "+data)
    #print("Available files are:", J)
    if data in J.values(): # the filename is present
        FileNameToPrint=data
    
    # as of 19th Sept 2025 we need to upload the file from the
    # server upload dir /home/pi/uploads that is also the UPLOAD_DIR
    # to the Octoprint upload dir using the function UploadFileToPrinter
    # then we can select it with SelectFileInPrinter.
    
    # confeptually, we could simply copy the file with os commands as well...
    # this seems to work properly as of 19th Sept 2025
    try:
        UploadFileToPrinter(FileNameToPrint)
    except Exception as e:
        print("Error in Select_local_file while UploadingFileToPrinter: ",e)
#     try:
#         FileNameToPrint=J[data]  
#     except:
#         print("File Not Found")
    SelectFileInPrinter(FileNameToPrint)
    print("Ready to Print: "+FileNameToPrint)

    
def Receive_file(data):
    global File_object, FileName
    FilePresent=False
    if str(type(data))=="<class 'str'>": # I know.... horrendus!
        print("File name is: "+data) # this is the file name
        FileName=data
        try:
            File_object = open(UPLOAD_FOLDER+"/"+data, 'w') # system dependent!      
        except Error as e:
            print("Error: "+str(e))
    else: # if it is not string, then it is the content.... TODO make this more robust...
#    if str(type(data))=="<class 'bytes'>": # this is the content!
        try:
            #print(data.decode("utf-8"))
            File_object.writelines(data.decode("utf-8"))
            FilePresent=True
            #print("File decoding OK")
        except Error as e:  # does not seem to be able to capture the error with non text files...
            print("Error in uploading file: ",e)
        finally:
            #print("ok to file closure?")
            File_object.close()
    # we perform here the upload to Octoprint in parallel 
    if FilePresent:
        DIR_command("No Data")
        print("Attempting File Upload to Printer...")
        UploadFileToPrinter(FileName)

def parse_data(data):
    #print(">> ",data)
    found=False
    if str(type(data))=="<class 'str'>": # I know.... horrendus!
        for index in range(0,len(keywords)): #removes the source identifier and processes the string
            if data.startswith(keywords[index]):
                found=True
                data=data.split(keywords[index])[1].replace("\n","\\n") # very tricky
                # as the data field of the called function can not be multiline, I need to "escape"
                # these dangerous chars by adding their encoding symbol "\n"
                q=functions[index]+"(\""+data.strip().replace("\"","\\\"")+"\")"
                print("debug. Received: "+q)
                exec(q)
        if data.startswith("request_messages"):
            found=True
#        if data.startswith("{\"type\":\"wifi_config\""):
#            TODO
        if not found:
            print("Unknown str data received:")
            print(">>"+str(data))
    if str(type(data))=="<class 'bytes'>": # I know.... horrendus! this should be the content
        Receive_file(data) # function will handle the file itself.
    
async def write_WS(queue):
    global websocket_list
    while True:
        if len(websocket_list) >0:
            websocket=list(websocket_list)[0]
            # wait for an item from the queue
            data = await queue.get()
            # when data is in the queue.. send it.
            try:
                await websocket.send(data)
            except:
                print("Something went wrong in attemting to send data")
                
            # Notify the queue that the message has been processed.
            queue.task_done()
        else:
            await asyncio.sleep(0.1) # important, to avoid becoming blocking if no connection is available

    
async def handle_WS(websocket, uri=0):
    global websocket_list, target_set, message_received, end_in_sight, outMessage
    websocket_list.add(websocket)
    if target_set.__len__()==0:
        target_set.add(websocket) # only the first one is added here.
    print(f"Connection accepted nr: ",len(websocket_list))
    #print("list of current connections: ")
    for each in websocket_list:
        print(each.id)
    i = 1
    # send DIR command result to update client side list
    DIR_command()
    
    # we invoke then "internally" the DIR command so that an updated list of the available files for printing is sent
    DIR_command("No Data")   
    
    while True:
        try:
            if not end_in_sight:
                data = await websocket.recv() # the client keeps pushing in messages every second...
                #print("something came in of length: ",len(data))
#                print(data)
                #print(type(data))
                parse_data(data)
                message_received=message_received+1
            else:
                websocket_list.remove(websocket)
                print("Closing connection to Client: ",websocket.id," ",len(websocket_list)," left")
                await websocket.close()
                break
        except Exception as ex:
            print(f"Connection lost to: ", websocket.id)
            print(ex.__class__.__name__)
            websocket_list.remove(websocket)
            return
        # TODO revisit this part as it sometimes ends up missing messages
        # what happens if message_received>websocket_list
        # it seems that the while will run forever...
        while message_received<len(websocket_list) and message_received>0:
            await asyncio.sleep(0.001) # ??? why?
            #await pass
        if message_received==len(websocket_list): #only one instance will send the ACK
            if outMessage=="":
                # await websocket.send("Message: "+str(i))
                msg="Message: "+str(i)
                FrontEndQueue.put_nowait(msg) # loads the message in the output queue
            else:
                #await websocket.send("DIR: "+outMessage)
                msg="DIR: "+outMessage
                FrontEndQueue.put_nowait(msg) # loads the message in the output queue
                outMessage=""
            i=i+1
            message_received=0
            await asyncio.sleep(0.001)
    end_in_sight=False
    message_received=0
    websocket_list=set()
    return        

def wpa_status():
    try:
        out = subprocess.check_output(["/sbin/wpa_cli", "-i", "wlan0", "status"], text=True)
        st=dict(line.split("=",1) for line in out.splitlines() if "=" in line)
        # if system is in client mode, flushes potential old addresses
        # that may be remnants of old AP mode
        #subprocess.run(["sudo" , "ip", "addr", "flush", "dev", "wlan0"],check=False)
        return(st)
    except:
        return("")
    #return st.get("wpa_state") == "COMPLETED" and "ssid" in st

# Wait until Wi-Fi client connection is established or timeout expires.
# Returns the SSID and IP if connected, or None if not.
def wait_until_connected(timeout=30, interval=1):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            st = wpa_status()
            if st.get("wpa_state") == "COMPLETED" and "ssid" in st:
                return {"ssid": st["ssid"], "ip": st.get("ip_address")}
            print("Running while inside wait_until_connected")
        except Exception as e:
            print("Exception in wait_until_connected while cycle: ")
            print(e)
            pass
        sleep(interval)
    print("returning None from wait_until_connected")
    return None


# version 12th August 2025 to handle AP mode case
# it could actually get stuck somehow if a known network is found
# but it can not connect... Should fall back to Hotspot mode eventually.
# at this time (10 Sept 2025) it does not.
def waitForIpAddress(timeout=None, poll=2.0):
    start = time.time()
    while True:
        ip = get_ip_address()
        print("ip:", ip)
        if ip != "127.0.0.1":
            return ip
        print("Waiting for network (AP or client)…")
        try:
            color=0b0000011111100000
            writeText("Waiting for network...", color, (230, 50), 0)
        except Exception:
            pass
        sleep(poll)
        if timeout and (time.time() - start) > timeout:
            raise TimeoutError("Timed out waiting for an IP address")

# returns a list of ALL the files indicated, in separate lines in the remote README.md
# with the format 'AvailableXXXXX filename.extension'
# the matched string is 'Available' while the separator from the filename is a space
# in versions before 20250908 ony the 'AvailableFile' and 'AvailablePage' were returned
def GetAvailableFile():
    # retrieves from the README.md in the remDir remote git repo
    # the name of the current update file available 
    response=[]
    resp = requests.get(remIndexFile)
    #resp.raise_for_status()
    if resp.status_code==200: # all ok
        Q=resp.text.splitlines() # contains the line(s) in the file
        #the target line is formatted as "AvailableFile test_20250901.py"
        for each in Q:
            if each.startswith("Available"):
                 response.append(each.split(" ")[1].strip())
    print("Debug: GetAvailableFile returns: ",response)
    return(response) # in case of error returns silently empty array

def DownloadAvailableFile(FileName=''):
    # DownloadAvailableFile(FileName='') downloads the file into the local dir
    # or the dir indicated in dowloadFolder (local dir if empty)
    global localFileName
    if not FileName:
        print("No File name provided")
        return(-1)
    else:
        print("Executing download of: ",FileName)
        localFileName = os.path.join(downloadFolder, FileName)
        remTargetFile=remDir+FileName
        resp = requests.get(remTargetFile)
        if resp.status_code!=200: # error... returning -1
            print("Error in download")
            return(-1)
        with open(localFileName, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

def NeedUpdate(fileNameRoot='', remoteFileName=''):
    # checks if the file name retrieved from server is more recent
    # than the one currently available in the local folder
    try:
        remoteFileNameRoot=remoteFileName.split("_202")[0]+"_"
        #print("Debug: remoteFileNameRoot is: ",remoteFileNameRoot)
    except Exception as e:
        print("Exception in NeedUpdate while handling remoteFileName: ",e)
        return(False)

    # selects from the local files in the dowloadFolder if given
    # and lists only those with name starting with the fileNameRoot
    localFiles=os.listdir(downloadFolder)
    test_files = [f for f in localFiles if f.startswith(remoteFileNameRoot)]
    
    # removes fileNameRoot from names for robustness
    test_files=[f.replace(remoteFileNameRoot,"") for f in test_files]
    remoteFileName=remoteFileName.replace(remoteFileNameRoot,"")
    
    test_files.sort() # as the version is given in YYYYMMDD, ordering
    # will leave the newest at the end of the list
    
    # debug
    try:
        print("latest LOCAL file version:",test_files[-1])
    except: # test_files is empty
        print("there is no LOCAL file version starting with: ",remoteFileNameRoot)
        test_files=["0"] # so that subsequent code will execute correctly
    print("latest REMOTE file version: ",remoteFileName)
    
    # we now compare it with the remoteFileName
    currentFile=re.split(r"[_.]",test_files[-1])
    remoteFile=re.split(r"[_.]",remoteFileName)
    #keeps only the numerical elements
    currentFile=[f for f in currentFile if f.isnumeric()]
    remoteFile=[f for f in remoteFile if f.isnumeric()]
    # workaround if any of the file names have no numerical version
    if (currentFile==[]):
        currentFile.append("0")
    if (remoteFile==[]):
        remoteFile.append("0")
    #return([currentFile,remoteFile])
    
    # now the first number is the main version number, the second (if any)
    # is the sub_version
    # updates is based on main version and, if identical, on sub_version
    if currentFile[0]>remoteFile[0]: # comparing main version
        print("Current Version is more recent")
        print("No Update required") # no need to check subversion
        return(False)

    if currentFile[0]<remoteFile[0]: # comparing main version
        print("Major Version Update required") # no need to check subversion
        return(True)
    if currentFile[0]==remoteFile[0]: # if current version match
        print("Major version number coincide")
        # we need to check, if available, the subversion(s)
        # case 1: no subversion is present in either name ==> no update
        # case 2: subversion in remote file but not in local ==> Update
        # case 3: subversion in both, returns comparison between subversions
        # case 4: subversion in local but not in remote (??) ==> no update
        if len(currentFile)==1:
            # add a default subversion to currentFile if not present
            currentFile.append("0")
        if len(currentFile)==len(remoteFile) and currentFile[1]<remoteFile[1]:
            # a higher subversion number is present in the remote file 
            # hence, update required
            print("New sub version: ",remoteFile[1])
            print("Old sub version: ",currentFile[1])
            print("Subversion Update required")            
            return(True)
        else:
            print("Current subversion is more recent or coincident with old one")
            print("No update required")
            return(False)   

def UpdateSymlink(localFileName=""):
    # relinks the local symlink "controller.py" to the latest downloaded
    # version. it also fixes the ownership of the just downloaded file
    if localFileName=="":
        return(-1)
    # updates the simlink to the (supposedly) fully qualified pathname
    # contained in localFileName
    
    tmp_link = symlink_path + ".tmp" # becomes controller.py.tmp
    # create a new symlink pointing to the new file
    try:
        os.symlink(localFileName, tmp_link)
    except Exception as e:
        print("Error while creating temp symlink: ",e)
        return(-1)
    
    # atomically replace the old symlink with the new one
    try:
        os.replace(tmp_link, symlink_path)
    except Exception as e:
        print("Error while creating final symlink: ",e)
        return(-1)
    
    # changes ownership of the downloaded file back to pi:pi
    try:
        subprocess.run(["chown", "pi:pi", localFileName], check=True)
    except Exception as e:
        print("Error while changing ownership of final symlink: ",e)

def CheckAndUpdate():
    # executes in sequence the steps for the update
    color=0b0000011111111111
    print("Checking for update files")
    response=GetAvailableFile() # it is a list with the names of the packages to download
    Updates=[]
    for each in response:
        print("Available remote files: ",each)
        if(NeedUpdate(fileNameRoot,each)): # check if update needed
            DownloadAvailableFile(each) # and download corresponding files
            Updates.append(True)
        else:
            Updates.append(False)
    # update 21 sept. Trying to make the symlink update more robust
    CodePos=-1 # will contain the index of the Websocket code in the server respose (or -1 if not present)
    CodeToRelink=False # becomes true if Websocket code needs to be updated
    IndexPos=-1
    IndexToRelink=False
    ZipPos=-1
    ZipToRefresh=False
    
    try:
        CodePos=[x.startswith("Websocket") for x in response].index(True)
        CodeToRelink=Updates[CodePos]
    except:
        pass
    
    try:
        IndexPos=[x.startswith("index") for x in response].index(True)
        IndexToRelink=Updates[IndexPos]
    except:
        pass
    
    try:
        ZipPos=[x.find(".zip")>-1 for x in response].index(True)
        ZipToRefresh=Updates[ZipPos]
    except:
        pass

    #handling of specific cases
    # it is based on the WEAK assumption that the first name in the updatelist
    # is the main code and the second if the web page
    # TODO: improve robustness by checking the XXXX part in the 'AvailableXXXX' in README.md
#    if Updates[0]:
    if(CodeToRelink): # the Websocket needs to be updated,
        # CodePos contains its position in response
        # checks if main python code has been updated (assuming that it is in first place!)
        print(">Updating Python code to: "+response[CodePos])        
        UpdateSymlink(response[CodePos].strip()) # how does this know which file does it need to point to?
        # fixed Sept 21 passing explicitly the link name as from response
#    if Updates[1]: # check if main web page has been updated
    if(IndexToRelink): # the index needs to be updated and copied in /var/www/html/index.html
        print(">Updating web page file: ",response[IndexPos])
         # here I need to 'sudo cp {PAGE} /var/www/html/index.html'
        subprocess.run(["cp", response[IndexPos], dst], check=True)
#    if Updates[2]: # should be a zip file
    if(ZipToRefresh):
        #extension=response[ZipPos].split(".")[-1]
        #if(extension=="zip"):
        print(">Decompressing file: ",response[ZipPos])
        #todo Decompress
        zip_path = Path("/home/pi/"+response[ZipPos]) # target zipfile
        target_dir = Path("/home/pi/")
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)  # will overwrite existing files         
#         else:
#             print("Not sure what to do with: ",response[2])
#             print("Extension is: ",extension)
    # If the main code was modified, message and reboot
    if CodeToRelink or ZipPos>-1:
        try:
            setCursor(False) #disables cursor
            try:
                img = Image.open('/home/pi/local_packages/owl.png')
                displayImage(img)
            except:
                clearScreen()
            writeText("Update Ok",color,(180,20),0) # welcome message
            writeText("Restarting...",color,(230,20),0)
        except Exception as e:
            print("Exception while trying to write to screen in checkAndUpdate: ",e)
            print(e)
            pass
        # restart service or reboot upon failure
            try:
                restart_self_systemd()
                #subprocess.run(["systemctl", "reboot"], check=True)
            except Exception as e:
                print(f"Restart and Reboot failed: {e}")


# END AUTOUPDATER
def checkDependencies(data=""): # does not work... not sure why.
    try:
        print("CheckDependencies invoked")
        ensure_requirements()
    except Exception as e:
        print("Exception in CheckDependencies: ",e)


def shutdown_system(data=""):
    color=0b0000011111111111
    try:
        setCursor(False) #disables cursor
        try:
            img = Image.open('/home/pi/local_packages/owl.png')
            displayImage(img)
        except:
            clearScreen()
        writeText("System halting",color,(180,20),0) # welcome message
        writeText("Turn off when screen",color,(230,20),0)
        writeText("becomes white",color,(280,20),0)
    except:
        pass
    try:
        print("Here goes the SHUTDOWN")
        subprocess.run(["/sbin/shutdown", "-h", "now"], check=True)
    except Exception as e:
        print(f"Shutdown failed: {e}")

async def main(): # this will contain the main controller logic
    PrinterConnected=True
    # runs forever in this main loop (actually, thre isn't much to do for now)
    # it will need to monitor the hardware param and update the front-end
    # sets the display image to the cat with a welcome message
    color=0b0000011111111111
    #color=0b0000011111100000
    print("Main is running: invoking get_ip_address")
    try:
        version=os.path.realpath(__file__)
        version=version.split('Websocket_Backend_4_')[-1]
        version=version.split('.')[0]
        writeText("Ver: "+version, color, (30, 20), 0)
        sleep(3)
    except:
        pass
    ip=get_ip_address()
    ip_string="my IP is: "+str(ip)
    print("get_ip_address returned ",ip_string)
    TextWelcome="Welcome to your new Etcher!"
    # recovers the ssid of Wifi and Ip
    print("Calling wait_until_connected")
    ntw=wait_until_connected()
    online=False
    try:
        TextSsid='Network: '+ntw['ssid']
        TextIp='With IP: '+str(ip) #note raspthat ntw['ip'] may return the old AP address
        online=True
    except Exception as e:
        TextWelcome='HOTSPOT MODE!'
        TextSsid='Connect to: RpiHotspotN'
        TextIp='Then open: '+str(ip)
        print("Exception with wait_until_connected function: ",e)
    if online:
        # added sept 1st, checks for software updates only if online
        # removed Sept 21 due to presence of alternate mechanism
#         try:
#             fixPackages() # verifies if package updates are neededand and, if so, gets and updates
#         except Exception as e:
#             print("Exception while running fixPackages: ",e)

        # added sept 1st, checks for software updates only if online
        try:
            print("running software update check")
            CheckAndUpdate() # verifies if updates are available and if so gets and updates
        except Exception as e:
            print("Exception while running CheckAndUpdate: ",e)
    print("wait_until_connected returned:")
    print(TextSsid)
    print(TextIp)
    
    # visualizes the new IP on the wifi network
    try:
        setCursor(False) #disables cursor
        try:
            img = Image.open('/home/pi/local_packages/owl.png')
            displayImage(img)
        except:
            clearScreen()
        writeText(TextWelcome,text_color=color,pos=(180,5),dim=32) # welcome message
        writeText(TextSsid,text_color=color,pos=(230,20),dim=32)
        writeText(TextIp,text_color=color,pos=(280,20),dim=32)
    except Exception as e:
        print("Exception while trying to write to screen in main: ",e)
        print(e)
        pass
    # creating configuration directories for Gerertranslator
    try:
        Translator.setup_dirs(ConfigDict)
    except Exception as e:
        print("Unable to create dirs for Translator: ",e)
        
        

    while True:
        await asyncio.sleep(4.123)
        FrontEndQueue.put_nowait("Main is awake!") # this is ignored by the server, could be used as keepalive
        # this creates fake values for the front end. On june 12 it is replaced by the true values
        #hv=int(un(190,212))
        #lv=int(un(120,hv))
        #ic=int(un(5,95)*100)/100.0
        hv=int(ADC_read(2))
        lv=int(ADC_read(1))
        ic=int(ADC_read(0)*100)/100.0
        ELECTRICALS([ic,hv,lv]) ; # this message is handled by the server
    
    if (SystemShutDown):
        # when the process is terminated, we need to close the PrinterHTMLConnection
        PrinterHTMLConnection.close() 
        pass




# TODO waits for network
# clearScreen()
# writeText("Starting: WaitForIpAddress",text_color=0b1111111111111111,pos=(50,20))
waitForIpAddress()
# initializes the GPIOs and sets initial status for generator and activates the voltage safety switch (can be used in the future)
try:
    GPIO_init()
    HV_gen(OFF,GEN_HV)
    CURRENT_set(0.0)
    HT_switch(ON)
except Exception as e:
    print("Failed GPIO initialization: ",e)
#writeText("Done: HW initializzation",text_color=0b1111111111111111,pos=(90,20))


try:
    auth=GetTokenFromOctoprint()
except Exception as e:
    print("Failed to get Octoprint Token: ",e)


'''
###This part has been modified to be able to run as started from a service

#creates a queue for outgoign messages (front-end interaction)
FrontEndQueue = asyncio.Queue()
#creates a queue to interact with (output towards) the printer
PrinterQueue = asyncio.Queue()
# Octoprint session auth, can be used to listen to incoming stuff (as in get_data(auth)) OR to send data
# this is intentionally blocking as of June 12th. it will "hang" attempting connection to Octoprint
# until is succeds. In the meantime, nothing else will happen but the rest of the backend will patiently wait for Octoprint.

server = websockets.serve(handle_WS, "", 8080)
asyncio.get_event_loop().run_until_complete(server) # this is set to implicitly runs as a task
print("Back-end Server (Front End Listener) is running")
asyncio.get_event_loop().create_task(main())
print("Main is running")
asyncio.get_event_loop().create_task(write_WS(FrontEndQueue))
print("Front end writer is running")
asyncio.get_event_loop().create_task(WriteToPrinter(PrinterQueue))
print("Printer writer is running")
asyncio.get_event_loop().create_task(get_data_Printer(auth))
#print("Printer websocket listener is running")
asyncio.get_event_loop().run_forever()
'''
# modifed version

async def start_server():
    try:
        #server = await websockets.serve(handle_WS, "0.0.0.0", 8080)
        server = await websockets.serve(handle_WS, "0.0.0.0", 8080,
                                        reuse_address=True,   # allow rebind quickly
                                        reuse_port=True       # (Linux only) multiple binds on same port
                                        )
        print("Back-end Server (Front End Listener) is running")
        return server
    except Exception as e:
        print("Error while starting server: ",e)
        return

async def run_all():
    global FrontEndQueue, PrinterQueue
    FrontEndQueue = asyncio.Queue()
    PrinterQueue = asyncio.Queue()

    WS_SERVER = await start_server()
    t1 = asyncio.create_task(main())
    print("Main is running")
    t2 = asyncio.create_task(write_WS(FrontEndQueue))
    print("Front end writer is running")
    t3 = asyncio.create_task(WriteToPrinter(PrinterQueue))
    print("Printer writer is running")
    t4 = asyncio.create_task(get_data_Printer(auth))
    # Keep running forever
    while True:
        await asyncio.sleep(3600)

print("name is: "+__name__)

if __name__ == '__main__':
    print("Starting...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_all())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


''' Front End messages for reference '''
'''
these are used both by the front-end and by the G-code controls

GEN_SET_RUN: true
GEN_SET_RUN: false
GEN_SET_HV: true
GEN_SET_HV: false
GEN_SET_CURRENT: 37

PUMP_SET_RUN: false
PUMP_SET_RUN: true
PUMP_SET_DIR: false
PUMP_SET_DIR: true
PUMP_SET_SPEED: 50

these are used only by the front end

INITIATE_PRINT
SELECT: V2 		#### parameters format to be verified!

upload commands to be verified
'''
