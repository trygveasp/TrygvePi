#!/usr/bin/python2.7
# encoding=utf-8

from Tkinter import *
import lnetatmo
from time import strftime
import requests
import xml.etree.ElementTree
import dateutil.parser
from datetime import timedelta, datetime
import matplotlib
import pytz
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib import gridspec
from matplotlib.collections import LineCollection
import numpy as np
matplotlib.use('TkAgg')


class Location(object):
    def __init__(self, home_id, name, lon, lat, msl, name2):
        self.home_id = home_id
        self.name = name
        self.lon = lon
        self.lat = lat
        self.msl = msl
        self.name2 = name2

    def print_location(self):
        print("home_id: ", self.home_id)
        print("Name: ", self.name)
        print("Longitude: ", self.lon)
        print("Latitude: ", self.lat)
        print("MSL: ", self.msl)
        print("Netatmo name: ", self.name2)


def get_measurement(location, debug=False, test_fail_netatmo=False):

    name = location.name2
    indoor_values = {}
    outdoor_values = {}
    rain_values = {}
    try:
        authorization = lnetatmo.ClientAuth()

        # 2 : Get devices list
        weather_data = lnetatmo.WeatherStationData(authorization)
        if debug:
            print(weather_data.stationByName(name))
            print(weather_data.rawData)

        # Inddor
        if debug:
            print("Inddor data:")
        for key in weather_data.stationByName(name)["dashboard_data"]:
            indoor_values.update({key: weather_data.stationByName(name)["dashboard_data"][key]})
            if debug:
                print(key, weather_data.stationByName(name)["dashboard_data"][key])

        # Outdoor
        if debug:
            print("Outddor data:")
        for key in weather_data.stationByName(name)["modules"][0]["dashboard_data"]:
            outdoor_values.update({key: weather_data.stationByName(name)["modules"][0]["dashboard_data"][key]})
            if debug:
                print(key, weather_data.stationByName(name)["modules"][0]["dashboard_data"][key])

        # Rain
        if debug:
            print("Rain data")
        if len(weather_data.stationByName(name)["modules"]) > 1:
            for key in weather_data.stationByName(name)["modules"][1]["dashboard_data"]:
                rain_values.update({key: weather_data.stationByName(name)["modules"][1]["dashboard_data"][key]})
                if debug:
                    print(key, weather_data.stationByName(name)["modules"][1]["dashboard_data"][key])

        if debug:
            print(indoor_values)
            print(outdoor_values)
            print(rain_values)

        if test_fail_netatmo:
            raise Exception("test_fail_netatmo")

        return indoor_values, outdoor_values, rain_values
    except:
        print("Could not access and get all Netatmo station data")
        raise


def get_location_forecast(location, variables, debug=False, test_fail_forecast=False,
                          timeout_forecast=5):

    latitude = location.lat
    longtude = location.lon
    msl = location.msl

    request_string = "https://api.met.no/weatherapi/locationforecast/2.0/classic/?lat={lat}&lon={lon}&altitude={msl}".format(
        lat=latitude, lon=longtude, msl=msl)
    if debug:
        print(request_string)

    try:
        try:
            headers = {
                 'User-Agent': 'Home weather display',
                'From': 'trygve@aspelien.no'  # This is another valid field
            }
            response = requests.get(request_string, timeout=timeout_forecast, headers=headers)
        except TimeoutError:
            raise TimeoutError(request_string+" timed out with timeout " + str(timeout_forecast))

        # Gets the website data
        doc_root = xml.etree.ElementTree.fromstring(response.content)
        product = doc_root[1]

        # Gets from-time and rain-value in a tuple and appends it to a list.
        acc_vars1h = {}
        acc_vars2h = {}
        acc_vars3h = {}
        acc_vars6h = {}
        other_vars = {}

        for i, time in enumerate(product.findall('time')):
            from_data = time.get('from')
            to_data = time.get('to')
            dt_from = dateutil.parser.parse(from_data, ignoretz=True)
            dt_to = dateutil.parser.parse(to_data, ignoretz=True)
            if debug:
                print(dt_from, dt_to)

            # Accumulated values
            if dt_to > dt_from:
                acc_time = str(dt_to - dt_from).split(':')[0]
                for loc in time.iter('location'):  # time.find() by itself doesn't work.
                    for var in ["precipitation"]:
                        for v in loc.iter(var):
                            atts = {}
                            for a in v.attrib:
                                value = v.get(a)
                                if a == "value" or a == "minvalue" or a == "maxvalue":
                                    value = float(value) / float(acc_time)
                                atts.update({a: value})

                            if debug:
                                print(time, var, atts)
                            # Update accumulated values valid for this time step
                            if int(acc_time) == 1:
                                acc_vars1h.update({dt_to: {var: atts}})
                            elif int(acc_time) == 2:
                                acc_vars2h.update({dt_to: {var: atts}})
                            elif int(acc_time) == 3:
                                acc_vars3h.update({dt_to: {var: atts}})
                            elif int(acc_time) == 6:
                                acc_vars6h.update({dt_to: {var: atts}})
                            else:
                                raise Exception("Acctime not implemented")

            # Not accumulated variables
            elif dt_to == dt_from:
                for loc in time.iter('location'):  # time.find() by itself doesn't work.
                    var_data = {}
                    for var in variables:
                        var_atts = {}
                        for v in loc.iter(var):
                            for a in v.attrib:
                                if debug:
                                    print(v.tag, v.attrib)

                                value = v.get(a)
                                var_atts.update({a: value})

                        var_data.update({var: var_atts})

                    other_vars.update({dt_to: var_data})
            else:
                raise Exception("Should not happen " + str(dt_from) + " -> " + str(dt_to))

        if test_fail_forecast:
            raise Exception("test_fail_forecast")

        return acc_vars1h, other_vars, acc_vars2h, acc_vars3h, acc_vars6h
    except:
        raise Exception("Could not get location forecast")

def get_nowcast(location, debug=False, test_fail_nowcast=False, timeout_nowcast=4):

    # Coordinates
    latitiude = location.lat
    longitude = location.lon

    request_string = "https://api.met.no/weatherapi/nowcast/0.9/?lat={lat}&lon={lon}".format(lat=latitiude,
                                                                                             lon=longitude)
    if debug:
        print(request_string)
    try:
        # Website data
        try:
            response = requests.get(request_string, timeout=timeout_nowcast)
        except TimeoutError:
            raise TimeoutError(request_string + " timed out with timeout " + str(timeout_nowcast))

        minutes = []
        values = []

        # Gets the website data
        doc_root = xml.etree.ElementTree.fromstring(response.content)
        if len(doc_root) > 0:
            product = doc_root[1]
            # Gets from-time and rain-value in a tuple and appends it to a list.
            weather_data = list()
            for i, time in enumerate(product.findall('time')):
                from_data = time.get('from')
                value_data = None
                for precipitation in time.iter('precipitation'):  # time.find() by itself doesn't work.
                    value_data = precipitation.get('value')
                weather_data.append((from_data, value_data))

            # Datetime
            dt = datetime.utcnow()
            # If any rain period of rain with over 0.5 mm of rainfall starts within 2 hours, return True.
            for i, tup in enumerate(weather_data):
                from_data = tup[0]
                value_data = tup[1]
                from_dt = dateutil.parser.parse(from_data, ignoretz=True)
                diff = from_dt - dt
                diff_minutes = (diff.days * 24 * 60) + (diff.seconds / 60)
                if from_dt >= dt:
                    minutes.append(int(diff_minutes))
                    values.append(float(value_data))
        if test_fail_nowcast:
            raise Exception("test_fail_nowcast")
        return minutes, values
    except:
        print("Could not get nowcast")
        raise


class Screen(Frame):
    def __init__(self, master, locations,
                 debug=False,
                 debug_update=False,
                 debug_update2=False,
                 debug_netatmo=False,
                 debug_nowcast=False,
                 debug_forecast=False,
                 test_fail_netatmo=False,
                 test_fail_forecast=False,
                 test_fail_nowcast=False,
                 updtime=300000,
                 timeout_netatmo=5,
                 timeout_nowcast=4,
                 timeout_forecast=5):

        Frame.__init__(self, master)

        # Initialize
        self.master = master
        self.loc_index = 0
        self.locations = locations
        self.location = self.locations[self.loc_index]
        self.days = 5
        self.debug = debug
        self.debug_update = debug_update
        self.debug_update2 = debug_update2
        self.debug_netatmo = debug_netatmo
        self.debug_nowcast = debug_nowcast
        self.debug_forecast = debug_forecast
        self.test_fail_netatmo = test_fail_netatmo
        self.test_fail_forecast = test_fail_forecast
        self.test_fail_nowcast = test_fail_nowcast
        self.updtime = updtime
        self.timeout_netatmo = timeout_netatmo
        self.timeout_nowcast = timeout_nowcast
        self.timeout_forecast = timeout_forecast

        # Raspberry pi has 800x480 pixels
        # Set fullscreen
        self.pad = 1
        self._geom = '200x200+0+0'
        # self.master.geometry("{0}x{1}+0+0".format(
        #    self.master.winfo_screenwidth()-self.pad, self.master.winfo_screenheight()-self.pad))
        self.master.geometry("{0}x{1}+0+0".format(800, 480))
        self.master.bind('<Escape>', self.toggle_geom)
        self.master.bind("<Button-1>", self.change_location)
        self.master.bind("<Button-3>", self.quit)
        self.master.wm_attributes('-type', 'splash')

        master.configure(background='white')

        screenwidth = self.master.winfo_screenwidth()
        screenheight = self.master.winfo_screenheight()
        if debug:
            print(screenwidth)
            print(screenheight)

        self.times = []
        self.dts = []
        self.indoor_station = None
        self.netatmo_updated = None
        self.indoor_temp = None
        self.indoor_pressure = None
        self.indoor_co2 = None
        self.outdoor_station = None
        self.netatmo_outdoor_updated = None
        self.outdoor_temp = None
        self.outdoor_humidity = None
        self.rain1h = None

        self.vars = ["temperature", "windDirection", "windSpeed", "windGust",
                     "areaMaxWindSpeed", "humidity", "pressure", "cloudiness",
                     "fog", "lowClouds", "mediumClouds", "highClouds", "temperatureProbability",
                     "windProbability", "dewpointTemperature"]

        self.netatmo = Canvas(self.master, bg="white", width=380, height=150)

        self.netatmo_outdoor = Canvas(self.master, bg="white", width=380, height=130)

        self.time1 = ''
        self.clock = Label(self.master, font=('times', 60, 'bold'), bg='white')

        my_dpi = 80
        sthisfig = Figure(figsize=(int(float(400)/float(my_dpi)), int(float(150)/float(my_dpi))), dpi=my_dpi)
        sthisfig.patch.set_facecolor('white')
        self.sthisplot = sthisfig.add_subplot(111)
        sthisplotcanvas = FigureCanvasTkAgg(sthisfig, master=self.master)
        sthisplotcanvas.draw()
        self.sthisplot.set_visible(False)

        self.bottomfig = Figure(figsize=(int(float(800)/float(my_dpi)), int(float(200)/float(my_dpi))), dpi=my_dpi)
        self.bottomfig.patch.set_facecolor('white')
        gs = gridspec.GridSpec(1, 2, width_ratios=[1, 3])
        self.nowcast = self.bottomfig.add_subplot(gs[0])

        self.forecast = self.bottomfig.add_subplot(gs[1])

        # a tk.DrawingArea
        self.bottomplots = FigureCanvasTkAgg(self.bottomfig, master=self.master)
        self.bottomplots.draw()

        self.netatmo.grid(row=0, column=0)
        sthisplotcanvas.get_tk_widget().grid(row=0, column=1)
        sthisplotcanvas._tkcanvas.grid(row=0, column=1)
        self.netatmo_outdoor.grid(row=1, column=0)
        self.clock.grid(row=1, column=1)
        self.bottomplots.get_tk_widget().grid(row=2, columnspan=2)
        self.bottomplots._tkcanvas.grid(row=2, columnspan=2)

        self.master.grid_columnconfigure(0, weight=1, uniform="group1")
        self.master.grid_columnconfigure(1, weight=1, uniform="group1")
        self.master.grid_rowconfigure(0, weight=1)

        self.test_increase = 0
        self.update()  # start the update loop

    def quit(self, event):
        Frame.quit(self)

    def change_location(self, event):
        self.loc_index = self.loc_index + 1
        if self.loc_index >= len(self.locations):
            self.loc_index = 0
        self.location = self.locations[self.loc_index]

        if self.debug:
            print("Change location")
            self.location.print_location()

        # Clear canvas elements
        if hasattr(self, "indoor_station"):
            self.netatmo.delete(self.indoor_station)
        if hasattr(self, "netatmo_updated"):
            self.netatmo.delete(self.netatmo_updated)
        if hasattr(self, "indoor_temp"):
            self.netatmo.delete(self.indoor_temp)
        if hasattr(self, "indoor_pressure"):
            self.netatmo.delete(self.indoor_pressure)
        if hasattr(self, "indoor_co2"):
            self.netatmo.delete(self.indoor_co2)
        if hasattr(self, "outdoor_station"):
            self.netatmo_outdoor.delete(self.outdoor_station)
        if hasattr(self, "netatmo_outdoor_updated"):
            self.netatmo_outdoor.delete(self.netatmo_outdoor_updated)
        if hasattr(self, "outdoor_temp"):
            self.netatmo_outdoor.delete(self.outdoor_temp)
        if hasattr(self, "outdoor_humidity"):
            self.netatmo_outdoor.delete(self.outdoor_humidity)
        if hasattr(self, "rain1h"):
            self.netatmo_outdoor.delete(self.rain1h)
        if hasattr(self, "nowcast"):
            self.nowcast.clear()
        if hasattr(self, "forecast"):
            self.forecast.clear()

        self.update()

    def toggle_geom(self, event):
        geom = self.master.winfo_geometry()
        if debug:
            print(geom, self._geom)
        self.master.geometry(self._geom)
        self._geom = geom

    def find_x_center(self, canvas, item):
        if debug:
            print(self.master.winfo_screenwidth() - self.pad)
        return (self.master.winfo_screenwidth() - self.pad) / 8

    def set_time_dimension(self, now, hours):
        self.times = []
        self.dts = []
        for t in range(0, hours):
            self.times.append(t)
            self.dts.append(now+timedelta(hours=t))

    def get_time_indices(self, dts, values_in=None):
        if values_in is not None and len(dts) != len(values_in):
            raise Exception("Mismatch in length: "+str(len(dts))+" != "+str(len(values_in)))

        indices = []
        values = []
        j = 0
        for dt in dts:
            for t in range(0, len(self.dts)):
                if dt == self.dts[t]:
                    indices.append(t)
                    if values_in is not None:
                        values.append(values_in[j] + self.test_increase)
            j = j + 1

        indices = np.asarray(indices)
        values = np.asarray(values)
        if values_in is not None:
            return indices, values
        else:
            return indices

    def update(self):

        # self.testIncrease=self.testIncrease-1
        if self.debug_update:
            print(datetime.now())
        self.tick()
        self.days = 5
        now = datetime.utcnow()
        now = now.replace(second=0, minute=0, microsecond=0)
        self.set_time_dimension(now, self.days*24)

        ###################################################################
        # Netatmo
        ###################################################################
        indoor_values = None
        outdoor_values = None
        rain_values = None
        test_fail_netatmo = False
        if self.debug_update and self.test_fail_netatmo:
            test_fail_netatmo = True
        try:
            indoor_values, outdoor_values, rain_values = get_measurement(self.location,
                                                                         debug=self.debug_netatmo,
                                                                         test_fail_netatmo=test_fail_netatmo)
        except:
            pass

        if indoor_values is not None and outdoor_values is not None and rain_values is not None:
            # if self.debug:
            #    print(indoor_values)
            #    print(outdoor_values)
            #    print(rain_values)

            # Inddor
            label = str(self.location.name) + " (inne)"
            len_label = len(label)
            x_pos = int((len_label * 8) * 0.5)
            if hasattr(self, "indoor_station"):
                self.netatmo.delete(self.indoor_station)
            self.indoor_station = self.netatmo.create_text(x_pos, 12, text=label, font=('verdana', 10))

            updated = "Oppdatert: NA"
            if "time_utc" in indoor_values:
                updated = "Oppdatert: " + datetime.fromtimestamp(indoor_values["time_utc"],
                                                                 pytz.timezone('Europe/Amsterdam')).strftime("%H:%M")
            if hasattr(self, 'netatmo_updated'):
                self.netatmo.delete(self.netatmo_updated)
            self.netatmo_updated = self.netatmo.create_text(300, 10, text=updated, font=('verdana', 10))

            # Temp
            if hasattr(self, 'indoor_temp'):
                self.netatmo.delete(self.indoor_temp)
            temp = "NA"
            if "Temperature" in indoor_values:
                temp = indoor_values["Temperature"]
            self.indoor_temp = self.netatmo.create_text(60, 40, text=self.temp_text(temp), fill=self.temp_color(temp),
                                                        font=('verdana', 20))

            # Pressure
            if hasattr(self, 'indoor_pressure'):
                self.netatmo.delete(self.indoor_pressure)
            pres = "NA"
            if "Pressure" in indoor_values:
                pres = "{0:.0f}".format(round(float(indoor_values["Pressure"]), 0))+' mb'
            self.indoor_pressure = self.netatmo.create_text(45, 90, text=pres, fill="black", font=('verdana', 12))

            # CO2
            if hasattr(self, 'indoor_co2'):
                self.netatmo.delete(self.indoor_co2)
            co2 = "NA"
            if "CO2" in indoor_values:
                co2 = str(indoor_values["CO2"])
            self.indoor_co2 = self.netatmo.create_text(65, 120, text='co2: '+co2+'ppm', fill="black",
                                                       font=('verdana', 12))

            #######################
            # Outdoor
            #######################
            label = str(self.location.name) + " (ute)"
            len_label = len(label)
            x_pos = int((len_label * 8) * 0.5)

            if hasattr(self, "outdoor_station"):
                self.netatmo_outdoor.delete(self.outdoor_station)
            self.outdoor_station = self.netatmo_outdoor.create_text(x_pos, 12, text=label, font=('verdana', 10))

            updated = "Oppdatert: NA"
            if "time_utc" in outdoor_values:
                updated = "Oppdatert: " + datetime.fromtimestamp(outdoor_values["time_utc"],
                                                                 pytz.timezone('Europe/Amsterdam')).strftime("%H:%M")
            if hasattr(self, 'netatmo_outdoor_updated'):
                self.netatmo_outdoor.delete(self.netatmo_outdoor_updated)
            self.netatmo_outdoor_updated = self.netatmo_outdoor.create_text(300, 12, text=updated, font=('verdana', 10))

            if hasattr(self, 'outdoor_temp'):
                self.netatmo_outdoor.delete(self.outdoor_temp)
            temp = "NA"
            if "Temperature" in outdoor_values:
                temp = outdoor_values["Temperature"]
            self.outdoor_temp = self.netatmo_outdoor.create_text(235, 75, text=self.temp_text(temp),
                                                                 fill=self.temp_color(temp),
                                                                 font=('verdana', 60))

            # Humidity
            if hasattr(self, 'outdoor_humidity'):
                self.netatmo_outdoor.delete(self.outdoor_humidity)
            hum = "NA"
            if "Humidity" in outdoor_values:
                hum = str(outdoor_values["Humidity"])
            self.outdoor_humidity = self.netatmo_outdoor.create_text(40, 90, text=hum + '%',
                                                                     fill="black", font=('verdana', 15))
            # Rain
            if hasattr(self, 'rain1h'):
                self.netatmo_outdoor.delete(self.rain1h)
            rain1h = ""
            if "sum_rain_1" in rain_values:
                rain1h = "{0:.1f}".format(round(float(rain_values["sum_rain_1"]), 1))+'mm/h'
            self.rain1h = self.netatmo_outdoor.create_text(60, 120, text=rain1h, font=('verdana', 15))
            if self.debug_update:
                print("Updated netatmo")
        else:
            print("Can not update netatmo")

        ###########################################################
        # Nowcast
        ###########################################################
        minutes = None
        values = None
        test_fail_nowcast = False
        if self.debug_update and self.test_fail_nowcast:
            test_fail_nowcast = True
        try:
            minutes, values = get_nowcast(self.location, debug=self.debug_nowcast,
                                          timeout_nowcast=self.timeout_nowcast,
                                          test_fail_nowcast=test_fail_nowcast)
        except:
            pass

        self.nowcast.clear()
        if minutes is not None and values is not None:
            ticks = [0, 15, 30, 45, 60, 75, 90]
            self.nowcast.axes.get_xaxis().set_ticks(ticks)
            if len(values) > 0:
                lines = self.nowcast.plot(minutes, values)
                lines[0].set_ydata(values)
                self.nowcast.set_ylim(bottom=0., top=max(values)+0.2)

                if max(values) > 0:
                    self.nowcast.fill_between(minutes, 0, values)
            if self.debug_update:
                print("Updated nowcast")
        else:
            print("Could not update nowcast")

        ###############################################################################
        # Location forecast
        ###############################################################################

        acc_vars1h = None
        other_vars = None
        test_fail_forecast = False
        if self.debug_update and self.test_fail_forecast:
            test_fail_forecast = True
        try:
            acc_vars1h, other_vars, acc_vars2h, acc_vars3h, acc_vars6h = \
                get_location_forecast(self.location, self.vars,
                                      debug=self.debug_forecast,
                                      timeout_forecast=self.timeout_forecast,
                                      test_fail_forecast=test_fail_forecast)
        except:
            pass

        if acc_vars1h is not None and other_vars is not None:
            # if self.debug:
            #    print(acc_vars1h)
            precipitation = []
            times = []
            var = "precipitation"
            for time in sorted(acc_vars1h):
                # if self.debug:
                #    print(time, var, acc_vars1h[time])
                times.append(time)
                precipitation.append(acc_vars1h[time][var]["value"])

            prec_indices, precipitation = self.get_time_indices(times, precipitation)
            temperature = []
            windspeed = []
            times = []
            for time in sorted(other_vars):
                var = "temperature"
                times.append(time)
                temperature.append(float(other_vars[time][var]["value"]))
                var = "windSpeed"
                windspeed.append(float(other_vars[time][var]["mps"]))

            temp_indices, temperature = self.get_time_indices(times, temperature)
            wind_indices, windspeed = self.get_time_indices(times, windspeed)

            c = ['r' if t > 0 else 'b' for t in temperature]
            lines = [((x0, y0), (x1, y1)) for x0, y0, x1, y1 in zip(temp_indices[:-1], temperature[:-1],
                                                                    temp_indices[1:],
                                                                    temperature[1:])]
            colored_lines = LineCollection(lines, colors=c, linewidths=(2,))
            self.forecast.clear()
            self.forecast.set_ylim(bottom=np.min(temperature) - 1, top=np.max(temperature) + 1)
            self.forecast.add_collection(colored_lines)
            if not hasattr(self, "axP"):
                self.axP = self.forecast.twinx()
            self.axP.clear()
            self.axP.bar(prec_indices, height=precipitation, width=1)
            self.axP.set_ylim(bottom=0, top=max(np.maximum(precipitation, 2)))
            line_wind = self.forecast.plot(wind_indices, windspeed, color="grey")
            today = now.replace(hour=0, second=0, minute=0, microsecond=0)
            ticks = []
            labels = []
            for d in range(1, self.days+1):
                ticks.append(today+timedelta(days=d))
                labels.append((today+timedelta(days=d)).strftime("%d/%m"))

            tick_positions = self.get_time_indices(ticks)
            self.forecast.axes.set_xticks(ticks=tick_positions, minor=False)
            self.forecast.axes.set_xticklabels(labels, fontdict=None, minor=False)
            line_wind[0].set_ydata(windspeed)
            if self.debug_update:
                print("Updated forecast")

        else:
            print("Can not update location forecast")

        self.bottomplots.draw_idle()
        if self.debug_update:
            if not self.debug_update2:
                self.debug_update = False
        else:
            if self.debug_update2:
                self.debug_update = True

        if self.debug_update2:
            self.debug_update2 = False
        self.after(self.updtime, self.update)  # ask the mainloop to call this method again in ms

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

    @staticmethod
    def temp_color(value):
        color = "red"
        if value != "NA" and value < 0:
            color = "blue"
        return color

    @staticmethod
    def temp_text(value):
        if value != "NA":
            # txt = "%s °C" % (value)
            txt = "%s" % value
        else:
            txt = "NA"
        return txt


if __name__ == "__main__":

    ids = ["5ea2e122a91a6479dd163b47", "5ea0320e5f0d964a8402d322","5ea2ded4a91a64e6511638e0"]
    names = ["Meiselen 19", "Bøen", "Solbakken"]
    names2 = ["Aspelien Konnerud (Indoor)", "Aspelien (Indoor)", "Solbakken (Indoor)"]
    latitudes = [59.7350, 59.9775, 59.7516]
    longitudes = [10.1242, 9.8978, 10.3204]
    msls = [231, 175, 170]

    stations = []
    for iloc in range(0, len(names)):
        stations.append(Location(ids[iloc], names[iloc], longitudes[iloc], latitudes[iloc], msls[iloc], names2[iloc]))

    root = Tk()
    screen = Screen(root, stations,
                    debug=False,
                    debug_update=False,
                    debug_update2=False,
                    debug_netatmo=False,
                    debug_nowcast=False,
                    debug_forecast=False,
                    test_fail_netatmo=False,
                    test_fail_forecast=False,
                    test_fail_nowcast=False,
                    updtime=300000,
                    # updtime=5000,
                    timeout_netatmo=5,
                    timeout_nowcast=4,
                    timeout_forecast=5
                    )
    root.mainloop()
