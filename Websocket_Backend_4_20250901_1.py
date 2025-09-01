import http.client
import asyncio
import websockets
import os
import json
from random import uniform as un
import requests

# for the on-board hardware elements
import pigpio
from gpiozero import MCP3008 # ADC converter on SPI1 lines
from time import sleep
# added may 9th 2025 a set of functions handling the SPI display
try:
    from local_packages import *
except:
    print("Errors in importing local_packages")
# added may 9th 2025 solely to get the system IP
import socket
from PIL import Image

# added 12th August 2025 to handle the waitForIpAddress() function in case of AP mode
# also added to handle the request of available WiFi
import subprocess, re, time
PREFERRED_IFACES = ("wlan0", "uap0", "ap0", "eth0")  # adjust to your setup

# end of 12th August 2025 addition

# version control
#print("Version 9 May 2025 17:00")
print("Version 20 August 2025 03:00")

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


UPLOAD_FOLDER = '/home/pi/uploads/'
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


# Keywords to Functions connection for Front End to Back End interaction 
keywords=["BUTTON_1: ","BUTTON_2: ","FILE_NAME: ","SELECT: ",
          "START_PRINT","GEN_SET_","PUMP_SET_","PRINTER_","RequestWifiList","{\"type\":\"wifi_config\"","CallFromPump"]
functions=["BUTTON_1_pressed","DIR_command","Receive_file","Select_local_file",
           "Initiate_print","SetGenerator","SetPump","ControlPrinter","scan_wifi_ssids","wifi_config","CallFromPump"]

# this is the list of identifiers that the client prepends to messages coming from different
# sources and that we will use to trigger the right function and remove from the messages themselves
# the corresponding (by position) list of function is invoked when the corresponding indicator is found
# this is done by the function parse_data() that is a basic a command interpreter where each
# identifier is actually a command (so we should use proper "commands-like-names" for each identifier

''' octoprint client part for RPI software'''

OCTOPRINTUSER="OctoAdmin"
OCTOPRINTPASS="H725d548r"
OCTOPRINTAPI_KEY="58612A874FD343C6810532DD1C169DA5"
OCTOPRINTHOST="raspberrypi2b.local"
OCTOPRINTPORT=5000 # port can be 80 or 5000
OCTOPRINTuri = "ws://raspberrypi2b.local:5000/sockjs/websocket"
Printerws="" # global handle to the printer websocket


''' octoprint client part for local software'''
'''
OCTOPRINTUSER="local"
OCTOPRINTPASS="local"
OCTOPRINTAPI_KEY="A150FE7F005448E7B28B8797E040338A"
OCTOPRINTHOST="127.0.0.1"
OCTOPRINTPORT=5000 # port can be 80 or 5000
OCTOPRINTuri = "ws://127.0.0.1:5000/sockjs/websocket"
Printerws="" # global handle to the printer websocket
'''

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
    img = Image.open('/home/pi/local_packages/owl.png')
    displayImage(img)
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
        TextSsid='Connected to: '+ntw['ssid']
        TextIp='With IP: '+str(ip)
    except:
        TextSsid='Not Connected to WiFi'
        TextIp='No Ip'
    
    # visualizes the new IP on the wifi network
    displayImage(img)
    color=0b0000011111111111
    writeText("Welcome to your new Etcher!",color,(180,20),0) # welcome message
    writeText(TextSsid,color,(230,20),0)
    writeText(TextIp,color,(280,20),0)

    

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
    return(max(r)+1)
    
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
    # let's start getting an HTTP session from octoprint to get our one-time authentication token
    # by loggin in with our username and password
    # the returned token is then used to establish the websockets session
    # failure is handled somewhat gracefulyl by printing out errors and trying again (ad  infinitum)
    headers = {'Content-type': 'application/json'}
    data = {'passive': 'true','user':OCTOPRINTUSER,'pass':OCTOPRINTPASS,'remember':'true'}
    json_data=json.dumps(data)
    Connected=False
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
        if not Connected:
            print("Retrying in 10 seconds")
            sleep(10)           
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
    list_dir=os.listdir(UPLOAD_FOLDER) # this is a list
    i=0 ;
    # '{ "V0":"file_0.txt", "V1":"file_1.txt", "V2":"new.txt", "V3":"anot.txt", "V4":"myf.txt" }'
    for each in list_dir:
        J["V"+str(i+1)]=each
        i=i+1
    json_data=json.dumps(J)
    FrontEndQueue.put_nowait("DIR: "+json_data)

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
    data=data.strip()
    try:
        FileNameToPrint=J[data]
    except:
        print("File Not Found")
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

# version used before August 12th. Fails in AP mode
# def get_ip_address():
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     try:
#         # This doesn't send data, it just selects the interface
#         s.connect(('8.8.8.8', 80))
#         ip = s.getsockname()[0]
#     except Exception:
#         ip = '127.0.0.1'
#     finally:
#         s.close()
#     return ip

# a function that, using wpa_supplicant, returns True if system is connected to
# a WiFi network, False if in AP mode.
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
        except:
            print("Exception in wait_until_connected while cycle")
            pass
        time.sleep(interval)
    print("returning None from wait_until_connected")
    return None


# version 12th August 2025 to handle AP mode case
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
        time.sleep(poll)
        if timeout and (time.time() - start) > timeout:
            raise TimeoutError("Timed out waiting for an IP address")

    

async def main(): # this will contain the main controller logic
    PrinterConnected=True
    # runs forever in this main loop (actually, thre isn't much to do for now)
    # it will need to monitor the hardware param and update the front-end
    # sets the display image to the cat with a welcome message
    color=0b0000011111111111
    #color=0b0000011111100000
    print("Main is running: invoking get_ip_address")
    ip=get_ip_address()
    ip_string="my IP is: "+str(ip)
    print("get_ip_address returned ",ip_string)
    TextWelcome="Welcome to your new Etcher!"
    # recovers the ssid of Wifi and Ip
    print("Calling wait_until_connected")
    ntw=wait_until_connected()
    try:
        TextSsid='Connected to: '+ntw['ssid']
        TextIp='With IP: '+str(ip) #note raspthat ntw['ip'] may return the old AP address
    except Exception as e:
        TextWelcome='HOTSPOT MODE!'
        TextSsid='Connect to: RpiHotspotN'
        TextIp='Then open: '+str(ip)
        print("Exception with wait_until_connected function: ",e)
    print("wait_until_connected returned:")
    print(TextSsid)
    print(TextIp)
    
    # visualizes the new IP on the wifi network
    try:
        setCursor(False) #disables cursor
        img = Image.open('/home/pi/local_packages/owl.png')
        displayImage(img)
        writeText(TextWelcome,color,(180,20),0) # welcome message
        writeText(TextSsid,color,(230,20),0)
        writeText(TextIp,color,(280,20),0)
    except Exception as e:
        print("Exception while trying to write to screen")
        print(e)
        pass

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

# routines for auto-updating from git repo
# can be sustained this way only if few systems are attached
# START AUTOUPDATER
remDir="https://mstefancich.github.io/example_2/"
remIndexFile=remDir+"README.md"
fileNameRoot='Websocket_Backend_4_' # the files of interest must start with this root
downloadFolder="./download" # set it to something like "/home/pi/downloads" or "/home/pi/src"
downloadFolder="."
localFileName="" # will contain the fully qualified path of it and is the target of the  updated symlink

symlink_path = "controller.py"

def GetAvailableFile():
    # retrieves from the README.md in the remDir remote git repo
    # the name of the current update file available 
    ANS=""
    resp = requests.get(remIndexFile)
    #resp.raise_for_status()
    if resp.status_code==200: # all ok
        Q=resp.text.splitlines() # contains the line(s) in the file
        #the target line is formatted as "AvailableFile test_20250901.py"
        for each in Q:
            if each.startswith("AvailableFile"):
                 ANS=each.split(" ")[1].strip()
    return(ANS) # in case of error returns silently empty string

def DownloadAvailableFile(FileName=''):
    # DownloadAvailableFile(FileName='') downloads the file into the local dir
    # or the dir indicated in dowloadFolder (local dir if empty)
    global localFileName
    if not FileName:
        print("No File name provided")
        return(-1)
    else:
        print("Executing download")
        localFileName = os.path.join(downloadFolder, FileName)
        remTargetFile=remDir+FileName
        resp = requests.get(remTargetFile)
        if resp.status_code!=200: # error... returning -1
            print("Error in download")
            return(-1)
        with open(localFileName, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

def NeedUpdate(remoteFileName=''):
    # checks if the file name retrieved from server is more recent
    # than the one currently available in the local folder
    
    # selects from the local files in the dowloadFolder if given
    # and lists only those with name starting with the fileNameRoot
    localFiles=os.listdir(downloadFolder)
    test_files = [f for f in localFiles if f.startswith(fileNameRoot)]
    
    # removes fileNameRoot from names for robustness
    test_files=[f.replace(fileNameRoot,"") for f in test_files]
    remoteFileName=remoteFileName.replace(fileNameRoot,"")
    
    test_files.sort() # as the version is given in YYYYMMDD, ordering
    # will leave the newest at the end of the list
    
    # debug
    print("latest LOCAL file version:",test_files[-1])
    print("latest REMOTE file version: ",remoteFileName)
    
    # we now compare it with the remoteFileName
    currentFile=re.split(r"[_.]",test_files[-1])
    remoteFile=re.split(r"[_.]",remoteFileName)
    #keeps only the numerical elements
    currentFile=[f for f in currentFile if f.isnumeric()]
    remoteFile=[f for f in remoteFile if f.isnumeric()]
    #return([currentFile,remoteFile])
    
    # now the first number is the main version number, the second (if any)
    # is the sub_version
    # updates is based on main version and, if identical, on sub_version
    if currentFile[0]>remoteFile[0]: # comparing main version
        print("Current Version is more recent")
        print("No Update required") # no need to check subversion
        return(True)

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

def UpdateSymlink():
    # relinks the local symlink "controller.py" to the latest downloaded
    # version.
    if localFileName=="":
        return(-1)
    # updates the simlink to the (supposedly) fully qualified pathname
    # contained in localFileName
    tmp_link = symlink_path + ".tmp"
    # create a new symlink pointing to the new file
    os.symlink(localFileName, tmp_link)
    
    # atomically replace the old symlink with the new one
    os.replace(tmp_link, symlink_path)

def CheckAndUpdate():
    # executes in sequence the steps for the update
    print("Checking for update files")
    ANS=GetAvailableFile()
    print("Available remote files: ",ANS)
    X=NeedUpdate(ANS)

    if X:
    # visualizes au Updating message
        try:
            setCursor(False) #disables cursor
            img = Image.open('/home/pi/local_packages/owl.png')
            displayImage(img)
            writeText("Updating System",color,(180,20),0) # welcome message
            writeText("Software",color,(230,20),0)
            writeText("Please wait..",color,(280,20),0)
        except Exception as e:
            print("Exception while trying to write to screen")
            print(e)
            pass
        # download software and change symlink
        DownloadAvailableFile(ANS)
        UpdateSymlink()
        # message and reboot
        try:
            setCursor(False) #disables cursor
            img = Image.open('/home/pi/local_packages/owl.png')
            displayImage(img)
            writeText("Update Ok",color,(180,20),0) # welcome message
            writeText("Rebooting...",color,(230,20),0)
        except Exception as e:
            print("Exception while trying to write to screen")
            print(e)
            pass
        # reboot
            try:
                subprocess.run(["systemctl", "reboot"], check=True)
            except Exception as e:
                print(f"Reboot failed: {e}")


# END AUTOUPDATER



# TODO waits for network
waitForIpAddress()
# initializes the GPIOs and sets initial status for generator and activates the voltage safety switch (can be used in the future)
GPIO_init()
HV_gen(OFF,GEN_HV)
CURRENT_set(0.0)
HT_switch(ON)

auth=GetTokenFromOctoprint() 
# Added 1st September 2025 - AutoUpdater
CheckAndUpdate() # verifies if updates are available and if so gets and updates


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
    server = await websockets.serve(handle_WS, "0.0.0.0", 8080)
    print("Back-end Server (Front End Listener) is running")
    return server

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
