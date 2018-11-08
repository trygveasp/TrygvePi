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
import pytz
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

    # Indoor:
    # 'CO2': 587, #
    # 'Temperature': 20.2,
    # 'time_utc': 1541674966,
    # 'pressure_trend': 'up',
    # 'temp_trend': u'stable',
    # 'Humidity': 44,
    # 'Pressure': 1016.7,
    # 'Noise': 37,
    # 'AbsolutePressure': 989,
    # 'date_max_temp': 1541651100,
    # 'min_temp': 20,
    # 'date_min_temp': 1541647172,
    # 'max_temp': 21.5

    # Outdoor [0]
    # 'date_min_temp': 1541631702,
    # 'Temperature': 6.3,
    # 'time_utc': 1541674921,
    # 'temp_trend': 'stable',
    # 'Humidity': 100,
    # 'date_max_temp': 1541673743,
    # 'min_temp': 5.5,
    # 'max_temp': 6.3

    # Rain [1]
    # 'time_utc': 1541674953,
    # 'sum_rain_24': 0.8,
    # 'sum_rain_1': 0,
    # 'Rain': 0

    indoorValues={}
    outdoorValues={}
    rainValues={}
    try:
        authorization = lnetatmo.ClientAuth()

        # 2 : Get devices list
        weatherData = lnetatmo.WeatherStationData(authorization)
        #print weatherData.stationByName(name)
        for key in weatherData.stationByName(name)["dashboard_data"]:
            indoorValues.update({key: weatherData.stationByName(name)["dashboard_data"][key]})

        # Outdoor
        for key in weatherData.stationByName(name)["modules"][0]["dashboard_data"]:
            outdoorValues.update({key:weatherData.stationByName(name)["modules"][0]["dashboard_data"][key]})

        # Rain
        if len(weatherData.stationByName(name)["modules"]) > 0:
            for key in weatherData.stationByName(name)["modules"][1]["dashboard_data"]:
                rainValues.update({key: weatherData.stationByName(name)["modules"][1]["dashboard_data"][key]})

    except:
        print "Could not access and get all Netatmo station data"

    print indoorValues
    print outdoorValues
    print rainValues
    return indoorValues,outdoorValues,rainValues


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


    # Gets from-time and rain-value in a tuple and appends it to a list.
    timeSeries={}
    for i, time in enumerate(product.findall('time')):
        from_data = time.get('from')
        #print from_data
        for loc in time.iter('location'):  # time.find() by itself doesn't work.
            #print loc
            for temperature in loc.iter('temperature'):  # time.find() by itself doesn't work.
                #print temperature
                value_data = temperature.get('value')
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
    if value != "NA" and value < 0 : color="blue"
    return color

def tempText(value):
    if value != "NA":
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

        my_dpi=80
        stHisFig=Figure(figsize=(int(float(400)/float(my_dpi)), int(float(150)/float(my_dpi))), dpi=my_dpi)
        stHisFig.patch.set_facecolor('white')
        self.stHisPlot= stHisFig.add_subplot(111)
        stHisPlotCanvas = FigureCanvasTkAgg(stHisFig, master=self.master)
        stHisPlotCanvas.show()

        bottomFig = Figure(figsize=(int(float(800)/float(my_dpi)), int(float(200)/float(my_dpi))), dpi=my_dpi)
        bottomFig.patch.set_facecolor('white')
        gs = gridspec.GridSpec(1, 2, width_ratios=[1, 3])
        self.nowcast = bottomFig.add_subplot(gs[0])
        #self.nowcast = bottomFig.add_subplot(121)
        self.nowcast.set_ylim(bottom=0.)
        ticks=[0,15,30,45,60,75,90]
        self.nowcast.axes.get_xaxis().set_ticks(ticks)

        self.forecast = bottomFig.add_subplot(gs[1])
        #self.forecast = bottomFig.add_subplot(122)


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

        indoorValues, outdoorValues, rainValues = get_measurement(self.location)
        updated="Updated: "+str(datetime.now().strftime("%H:%M"))

        #Inddor
        updated = "Updated: NA"
        if "time_utc" in indoorValues: updated = "Updated: "+datetime.fromtimestamp(indoorValues["time_utc"], pytz.timezone('Europe/Amsterdam')).strftime("%H:%M")
        if hasattr(self,'netatmoUpdated'): self.netatmo.delete(self.netatmoUpdated)
        self.netatmoUpdated=self.netatmo.create_text(300, 10, text=updated,font=('verdana', 10))

        # Temp
        if hasattr(self, 'indoorTemp'): self.netatmo.delete(self.indoorTemp)
        temp="NA"
        if "Temperature" in indoorValues: temp=indoorValues["Temperature"]
        self.indoorTemp=self.netatmo.create_text(60, 40, text=tempText(temp), fill=tempColor(temp), font=('verdana', 20))

        # Pressure
        if hasattr(self, 'indoorPressure'): self.netatmo.delete(self.indoorPressure)
        pres="NA"
        if "Pressure" in indoorValues: pres="{0:.0f}".format(round(float(indoorValues["Pressure"]),0))+' mb'
        self.indoorPressure = self.netatmo.create_text(45, 90, text=pres,fill="black", font=('verdana', 12))

        # CO2
        if hasattr(self, 'indoorCO2'): self.netatmo.delete(self.indoorCO2)
        co2="NA"
        if "CO2" in indoorValues: co2=str(indoorValues["CO2"])
        self.indoorCO2 = self.netatmo.create_text(65, 120, text='co2: '+co2+'ppm',fill="black", font=('verdana', 12))

        #######################
        # Outdoor
        #######################
        updated="Updated: NA"
        if "time_utc" in outdoorValues: updated="Updated: "+datetime.fromtimestamp(outdoorValues["time_utc"], pytz.timezone('Europe/Amsterdam')).strftime("%H:%M")
        if hasattr(self, 'netatmoOutdoorUpdated'): self.netatmoOutdoor.delete(self.netatmoOutdoorUpdated)
        self.netatmoOutdoorUpdated = self.netatmoOutdoor.create_text(300, 12, text=updated, font=('verdana', 10))

        if hasattr(self,'outdoorTemp'): self.netatmoOutdoor.delete(self.outdoorTemp)
        temp="NA"
        if "Temperature" in outdoorValues: temp=outdoorValues["Temperature"]
        self.outdoorTemp=self.netatmoOutdoor.create_text(250, 75, text=tempText(temp), fill=tempColor(temp), font=('verdana', 50))

        # Humidity
        if hasattr(self, 'outdoorHumidity'): self.netatmoOutdoor.delete(self.outdoorHumidity)
        hum="NA"
        if "Humidity" in outdoorValues: hum=str(outdoorValues["Humidity"])
        self.outdoorHumidity = self.netatmoOutdoor.create_text(34, 90, text=hum + '%',
                                                        fill="black", font=('verdana', 15))
        # Rain
        if hasattr(self, 'Rain1h'): self.netatmoOutdoor.delete(self.Rain1h)
        rain1h="NA"
        if "sum_rain_1" in rainValues: rain1h="{0:.1f}".format(round(float(rainValues["sum_rain_1"]),1))+'mm/h'
        self.Rain1h = self.netatmoOutdoor.create_text(50, 120, text=rain1h,font=('verdana', 15))

        minutes,values=get_rain(self.location)
        self.nowcast.axes.get_yaxis().set_visible(False)
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
