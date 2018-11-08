#!/usr/bin/python2.7
# encoding=utf-8

from Tkinter import *
import ttk
import lnetatmo
import ntplib
from time import ctime,strftime
import requests
import xml.etree.ElementTree as ET
import dateutil.parser
from datetime import timedelta,datetime,tzinfo

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg,NavigationToolbar2TkAgg
from matplotlib.figure import Figure
from matplotlib import gridspec

class Location(object):
    def __init__(self,name,lon,lat,msl):
        self.name=name
        self.lon=lon
        self.lat=lat
        self.msl=msl

def checkTime():
    c = ntplib.NTPClient()
    response = c.request('europe.pool.ntp.org', version=3)
    print response.offset
    print response.version
    print ctime(response.tx_time)
    print ntplib.leap_to_text(response.leap)
    print response.root_delay
    print ntplib.ref_id_to_text(response.ref_id)

def get_measurement(location):

    # 1 : Authenticate
    values={}
    values.update({"indoorTemp":None})
    values.update({"outdoorTemp": None})
    values.update({"outdoorHumidity": "NA"})
    values.update({"indoorPressure": "NA"})
    values.update({"indoorCO2": "NA"})
    try:
        authorization = lnetatmo.ClientAuth()

        # 2 : Get devices list
        weatherData = lnetatmo.WeatherStationData(authorization)
        print weatherData.stationByName(name)
        indoorTemp=weatherData.stationByName(name)["dashboard_data"]["Temperature"]
        values.update({"indoorTemp": indoorTemp})
        outdoorTemp=weatherData.stationByName(name)["modules"][0]["dashboard_data"]["Temperature"]
        values.update({"outdoorTemp": outdoorTemp})
        outdoorHumididty = weatherData.stationByName(name)["modules"][0]["dashboard_data"]["Humidity"]
        values.update({"outdoorHumidity": outdoorHumididty})
        indoorPressure = weatherData.stationByName(name)["dashboard_data"]["Pressure"]
        values.update({"indoorPressure": indoorPressure})
        indoorCO2 = weatherData.stationByName(name)["dashboard_data"]["CO2"]
        values.update({"indoorCO2": indoorCO2})
    except:
        print "Could not access and get all Netatmo station data"

    print values
    return values

def minTime(times,GT=None):
    ind=-1
    time=-1
    if len(times) > 0:
        if GT != None:
            minTime=GT
        else:
            minTime = times[0]
        ind = 0
        for time in times:
            i = 0
            if time < minTime:
                minTime = time
                ind = i
            i = i + 1

    return time,ind

def sortValues(times1,values1):
    times = []
    values = []
    if len(times1) > 0:

        t, ind = minTime(times1)
        times.append(t)
        values.append(values1[ind])

        for t in range(1,len(times1)):

            t,ind=minTime(times1,times)
            times.append(t)
            values.append(values1[ind])

    times = times1.sort()
    values = values1
    return times,values


def getLocationForecast(location):

    LATITUDE = location.lat
    LONGITUDE = location.lon
    MSL=location.msl

    request_string ="https://api.met.no/weatherapi/locationforecast/1.9/?lat={lat}&lon={lon}&msl={msl}".format(lat=LATITUDE,
                                                                                             lon=LONGITUDE,msl=MSL)

    print request_string
    response = requests.get(request_string)

    # Gets the website data
    root = ET.fromstring(response.content)
    product = root[1]

    #time_data_list = [time.get('from') for time in product.iter('time')]
    #value_data_list = [precipitation.get('value') for precipitation in product.iter('precipitation')]

    # Gets from-time and rain-value in a tuple and appends it to a list.
    timeSeries={}
    weather_data = list()
    for i, time in enumerate(product.findall('time')):
        from_data = time.get('from')
        #print from_data
        for loc in time.iter('location'):  # time.find() by itself doesn't work.
            #print loc
            for temperature in loc.iter('temperature'):  # time.find() by itself doesn't work.
                #print temperature
                value_data = temperature.get('value')
            #weather_data.append((from_data, value_data))
            dt=dateutil.parser.parse(from_data, ignoretz=True)
            timeSeries.update({dt:value_data})


    return timeSeries

def get_rain(location):

    # Coordinates
    LATITUDE = location.lat
    LONGITUDE = location.lon

    request_string = "https://api.met.no/weatherapi/nowcast/0.9/?lat={lat}&lon={lon}".format(lat=LATITUDE,
                                                                                             lon=LONGITUDE)
    print request_string
    # Website data
    response = requests.get(request_string)

    minutes = []
    values = []

    # Gets the website data
    root = ET.fromstring(response.content)
    if len(root) > 0:
        product = root[1]


        # Gets from-time and rain-value in a tuple and appends it to a list.
        weather_data = list()
        for i, time in enumerate(product.findall('time')):
            from_data = time.get('from')
            for precipitation in time.iter('precipitation'):  # time.find() by itself doesn't work.
                value_data = precipitation.get('value')
            weather_data.append((from_data, value_data))

        # Datetime
        dt = datetime.utcnow()
        
        # If any rain period of rain with over 0.5 mm of rainfall starts within 2 hours, return True.
        for i, tup in enumerate(weather_data):
            from_data = tup[0]
            value_data = tup[1]

            from_dt = dateutil.parser.parse(from_data,ignoretz=True)

            diff=from_dt-dt
            diff_minutes = (diff.days * 24 * 60) + (diff.seconds / 60)
            if from_dt >= dt:
                minutes.append(int(diff_minutes))
                values.append(float(value_data))

    return minutes,values

def tempColor(value):
    color= "red"
    if value < 0 : color="blue"
    return color

def tempText(value):
    if value != None:
        txt = " %s °C" % (value)
    else:
        txt = "NA"
    return txt

class Screen(Frame):
    def __init__(self, master,location):
        Frame.__init__(self, master)

        # Initialize
        self.master=master
        self.location=location

        # Raspberry pi has 800x480 pixels
        # Set fullscreen
        self.pad=1
        self._geom='200x200+0+0'
        #self.master.geometry("{0}x{1}+0+0".format(
        #    self.master.winfo_screenwidth()-self.pad, self.master.winfo_screenheight()-self.pad))
        self.master.geometry("{0}x{1}+0+0".format(800,480))
        self.master.bind('<Escape>',self.toggle_geom)
        self.master.bind("<Button-3>",self.quit)
        self.master.wm_attributes('-type', 'splash')
        #self.master.overrideredirect(1) 

        master.configure(background='white')

        screenWidth=self.master.winfo_screenwidth()
        screenHeight=self.master.winfo_screenheight()
        print screenWidth
        print screenHeight

        self.netatmo = Canvas(self.master, bg="white",width=380, height=150)
        self.netatmo.create_text(100,12,text=str(self.location.name)+" Indoor",font=('verdana', 10))

        self.netatmoOutdoor = Canvas(self.master, bg="white",width=380,height=130)
        self.netatmoOutdoor.create_text(100,12,text=str(self.location.name)+" Outdoor", font=('verdana', 10))


        self.time1=''
        self.clock = Label(self.master, font=('times', 60, 'bold'), bg='white')

        my_dpi=96
        stHisFig=Figure(figsize=(400/my_dpi, 150/my_dpi), dpi=my_dpi)
        stHisFig.patch.set_facecolor('white')
        self.stHisPlot= stHisFig.add_subplot(111)
        stHisPlotCanvas = FigureCanvasTkAgg(stHisFig, master=self.master)
        stHisPlotCanvas.show()

        bottomFig = Figure(figsize=(800/my_dpi, 200/my_dpi), dpi=my_dpi)
        bottomFig.patch.set_facecolor('white')
        gs = gridspec.GridSpec(1, 2, width_ratios=[2, 5])
        self.nowcast = bottomFig.add_subplot(gs[0])
        self.nowcast.set_ylim(bottom=0.)

        self.forecast = bottomFig.add_subplot(gs[1])


        # a tk.DrawingArea
        bottomPlots = FigureCanvasTkAgg(bottomFig, master=self.master)
        bottomPlots.show()

        self.netatmo.grid(row=0, column=0)
        stHisPlotCanvas.get_tk_widget().grid(row=0,column=1)
        stHisPlotCanvas._tkcanvas.grid(row=0, column=1)
        self.netatmoOutdoor.grid(row=1,column=0)
        self.clock.grid(row=1, column=1)
        bottomPlots.get_tk_widget().grid(row=2,columnspan=2)
        bottomPlots._tkcanvas.grid(row=2,columnspan=2)

        self.master.grid_columnconfigure(0, weight=1, uniform="group1")
        self.master.grid_columnconfigure(1, weight=1, uniform="group1")
        self.master.grid_rowconfigure(0, weight=1)

        self.update() # start the update loop

    def quit(self,event):
        Frame.quit(self)

    def toggle_geom(self,event):
        geom=self.master.winfo_geometry()
        print(geom,self._geom)
        self.master.geometry(self._geom)
        self._geom=geom

    def findXCenter(self, canvas, item):
        print (self.master.winfo_screenwidth() - self.pad)
        return ((self.master.winfo_screenwidth() - self.pad) / 8)

    def update(self):

        print datetime.now()
        self.tick()

        values=get_measurement(self.location)
        updated="Updated: "+str(datetime.now().strftime("%H:%M"))


        #xCenter = self.findXCenter(self.netatmo, self.indoor)

        #Inddor
        if hasattr(self,'netatmoUpdated'): self.netatmo.delete(self.netatmoUpdated)
        self.netatmoUpdated=self.netatmo.create_text(300, 10, text=updated,font=('verdana', 10))

        # Temp
        if hasattr(self, 'indoorTemp'): self.netatmo.delete(self.indoorTemp)
        self.indoorTemp=self.netatmo.create_text(70, 40, text=tempText(values["indoorTemp"]), fill=tempColor(values["indoorTemp"]), font=('verdana', 20))

        # Humidity
        if hasattr(self, 'outdoorHumidity'): self.netatmo.delete(self.outdoorHumidity)
        self.outdoorHumidity = self.netatmo.create_text(250, 40, text=str(values["outdoorHumidity"])+'%',fill="black", font=('verdana', 20))

        # Pressure
        if hasattr(self, 'indoorPressure'): self.netatmo.delete(self.indoorPressure)
        self.indoorPressure = self.netatmo.create_text(70, 80, text=str(values["indoorPressure"])+'mb',fill="black", font=('verdana', 20))

        # CO2
        if hasattr(self, 'indoorCO2'): self.netatmo.delete(self.indoorCO2)
        self.indoorCO2 = self.netatmo.create_text(100, 120, text='CO2: '+str(values["indoorCO2"])+'ppm',fill="black", font=('verdana', 20))


        # Outdoor
        if hasattr(self, 'netatmoOutdoorUpdated'): self.netatmoOutdoor.delete(self.netatmoOutdoorUpdated)
        self.netatmoOutdoorUpdated = self.netatmoOutdoor.create_text(300, 12, text=updated, font=('verdana', 10))

        if hasattr(self,'outdoorTemp'): self.netatmoOutdoor.delete(self.outdoorTemp)
        self.outdoorTemp=self.netatmoOutdoor.create_text(150, 75, text=tempText(values["outdoorTemp"]), fill=tempColor(values["outdoorTemp"]), font=('verdana', 50))


        minutes,values=get_rain(self.location)
        self.nowcast.plot(minutes,values)
        if max(values) > 0:
            self.nowcast.fill_between(minutes,0,values)

        timeSeries=getLocationForecast(self.location)
        times=[]
        values=[]
        for time in sorted(timeSeries):
            #print time,timeSeries[time]
            times.append(time)
            values.append(timeSeries[time])

        self.forecast.plot(times,values)

        updtime=300000
        #updtime=5000
        self.after(updtime, self.update) # ask the mainloop to call this method again in 1,000 milliseconds

    def tick(self):
        # get the current local time from the PC
        time2 = strftime('%H:%M:%S')
        # if time string has changed, update it
        if time2 != self.time1:
            time1 = time2
            self.clock.config(text=time2)
        # calls itself every 200 milliseconds
        # to update the time display as needed
        # could use >200 ms, but display gets jerky
        self.clock.after(200, self.tick)

# Meiselen 19
name="Aspelien Konnerud"
LATITUDE = 59.7350
LONGITUDE = 10.1242
MSL = 231

# Bøen
#name="Aspelien"
#LATITUDE=59.9775
#LONGITUDE=9.8978
#MSL=175

station=Location(name,LONGITUDE,LATITUDE,MSL)

root=Tk()
screen=Screen(root,station)
root.mainloop(  )
