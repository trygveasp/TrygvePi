try:
    import Tkinter as tkinter  # noqa
except ModuleNotFoundError:
    import tkinter

import threading
from log import logger
from datetime import datetime
from time import strftime
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib import gridspec
matplotlib.use('TkAgg')

from forecast import get_location_forecast, plot_location_forecast
from nowcast import get_nowcast, plot_nowcast
from station import get_measurement, plot_station_indoor_info, plot_station_outdoor_info


class Screen(tkinter.Frame):
    def __init__(self, master, locations,
                 test_fail_netatmo=False,
                 test_fail_forecast=False,
                 test_fail_nowcast=False,
                 show_netatmo=True,
                 show_nowcast=True,
                 show_forecast=True,
                 updtime=300000,
                 timeout_netatmo=5,
                 timeout_nowcast=4,
                 timeout_forecast=5,
                 update=True):

        tkinter.Frame.__init__(self, master)

        # Initialize
        self.master = master
        self.loc_index = 0
        self.locations = locations
        self.location = self.locations[self.loc_index]
        self.days = 5
        self.test_fail_netatmo = test_fail_netatmo
        self.test_fail_forecast = test_fail_forecast
        self.test_fail_nowcast = test_fail_nowcast
        self.show_netamo = show_netatmo
        self.show_nowcast = show_nowcast
        self.show_forecast = show_forecast
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
        logger.debug("screenwidth=%s", screenwidth)
        logger.debug("screenheight=%s", screenheight)

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

        self.netatmo = tkinter.Canvas(self.master, bg="white", width=380, height=150)

        self.netatmo_outdoor = tkinter.Canvas(self.master, bg="white", width=380, height=130)

        self.time1 = ''
        self.clock = tkinter.Label(self.master, font=('times', 60, 'bold'), bg='white')

        my_dpi = 80
        sthisfig = Figure(figsize=(int(float(400)/float(my_dpi)), int(float(150)/float(my_dpi))), dpi=my_dpi)
        sthisfig.patch.set_facecolor('white')
        self.sthisplot = sthisfig.add_subplot(111)
        sthisplotcanvas = FigureCanvasTkAgg(sthisfig, master=self.master)
        sthisplotcanvas.draw()
        self.sthisplot.set_visible(False)

        if hasattr(self, "bottomfig"):
            self.bottomfig.clear()
        self.bottomfig = Figure(figsize=(int(float(800)/float(my_dpi)), int(float(200)/float(my_dpi))), dpi=my_dpi)
        self.bottomfig.patch.set_facecolor('white')
        gs = gridspec.GridSpec(1, 2, width_ratios=[1, 3])
        self.nowcast = self.bottomfig.add_subplot(gs[0])

        self.forecast = self.bottomfig.add_subplot(gs[1])
        self.ax_prec = self.forecast.twinx()
        self.ax_wind = self.forecast.twinx()

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
        if update:
            self.update()  # start the update loop

    def quit(self, event):
        tkinter.Frame.quit(self)

    def change_location(self, event):
        self.loc_index = self.loc_index + 1
        if self.loc_index >= len(self.locations):
            self.loc_index = 0
        self.location = self.locations[self.loc_index]

        logger.debug("Change location: %s", self.location.print_location())

        self.update()

    def toggle_geom(self, event):
        geom = self.master.winfo_geometry()
        logger.debug("geom=%s self._geom=%s", geom, self._geom)
        self.master.geometry(self._geom)
        self._geom = geom

    def find_x_center(self, canvas, item):
        logger.debug("find_x_center: %s", self.master.winfo_screenwidth() - self.pad)
        return (self.master.winfo_screenwidth() - self.pad) / 8


    def update(self):

        logger.info(datetime.now())
        t1 = threading.Thread(target=self.tick())
        t1.start()
        t2 = threading.Thread(target=self.update_data())
        t2.start()

    def update_data(self):

        self.days = 5
        now = datetime.utcnow()
        now = now.replace(second=0, minute=0, microsecond=0)
        # self.set_time_dimension(now, self.days*24)

        ###################################################################
        # Netatmo
        ###################################################################
        if self.show_netamo:
            indoor_values = None
            outdoor_values = None
            rain_values = None
            test_fail_netatmo = False
            if self.test_fail_netatmo:
                test_fail_netatmo = True
            try:
                indoor_values, outdoor_values, rain_values = get_measurement(self.location,
                                                                            test_fail_netatmo=test_fail_netatmo)
            except:
                pass

            if indoor_values is not None and outdoor_values is not None and rain_values is not None:
                self.netatmo = plot_station_indoor_info(self.netatmo, self.location, indoor_values)
                self.netatmo_outdoor = plot_station_outdoor_info(self.netatmo_outdoor, self.location, outdoor_values, rain_values)
                '''
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
                '''
            else:
                print("Can not update netatmo")

        ###########################################################
        # Nowcast
        ###########################################################
        if self.show_nowcast:
            minutes = None
            values = None
            test_fail_nowcast = False
            if self.test_fail_nowcast:
                test_fail_nowcast = True
            try:
                minutes, values = get_nowcast(self.location,
                                            timeout_nowcast=self.timeout_nowcast,
                                            test_fail_nowcast=test_fail_nowcast)
            except Exception as exc:
                logger.warning("Got exception %s", str(exc))

            self.nowcast.clear()

            if minutes is not None and values is not None:
                self.nowcast = plot_nowcast(self.nowcast, minutes, values)
                '''
                ticks = [0, 15, 30, 45, 60, 75, 90]
                self.nowcast.axes.get_xaxis().set_ticks(ticks)
                if len(values) > 0:
                    lines = self.nowcast.plot(minutes, values)
                    lines[0].set_ydata(values)
                    self.nowcast.set_ylim(bottom=0., top=max(values)+0.2)

                    if max(values) > 0:
                        self.nowcast.fill_between(minutes, 0, values)
                '''
            else:
                print("Could not update nowcast")

        ###############################################################################
        # Location forecast
        ###############################################################################
        if self.show_forecast:
            acc_vars1h = None
            other_vars = None
            test_fail_forecast = False
            if self.test_fail_forecast:
                test_fail_forecast = True
            try:
                acc_vars1h, other_vars, acc_vars2h, acc_vars3h, acc_vars6h = \
                    get_location_forecast(self.location, self.vars,
                                        timeout_forecast=self.timeout_forecast,
                                        test_fail_forecast=test_fail_forecast)
            except Exception as exc:
                logger.warning("Got exception %s", str(exc))

            if acc_vars1h is not None and other_vars is not None:
                self.forecast = plot_location_forecast(
                    self.forecast, self.ax_prec, self.ax_wind, acc_vars1h, other_vars,
                    test_increase=self.test_increase, days=self.days)

                '''
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
                '''
                logger.debug("Updated forecast")

            else:
                logger.warning("Can not update location forecast")

        self.bottomplots.draw_idle()
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
