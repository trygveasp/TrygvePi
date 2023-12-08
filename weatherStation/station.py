import lnetatmo
from datetime import datetime
import pytz
from log import logger

def get_netatmo_station_data(data, home_id):

    logger.debug("data=%s", data)
    for station_data in data:
        logger.debug("%s == %s?", station_data["home_id"], home_id)
        if station_data["home_id"] == home_id:
            logger.debug("Found station id %s", home_id)
            return station_data
    logger.warning("No station ID found %s", home_id)
    raise Exception("Station not found")


def get_netatmo_module_data(data, data_type):
    values = {}
    logger.debug("data_type=%s", data_type)
    for module in data["modules"]:
        logger.debug("Found module %s", module)
        logger.debug("Available data types: %s", module["data_type"])
        if data_type in module["data_type"]:
            logger.debug("Look for %s in %s", data_type, module)
            if "dashboard_data" in module:
                logger.debug("dashboard_data=%s", module["dashboard_data"])
                values = module["dashboard_data"]
            else:
                values = module

    for key in values:
        logger.debug("Found %s %s", key, values[key])
    return values


def get_netatmo_indoor_data(data):
    values = data["dashboard_data"]
    for key in values:
        logger.debug("Found %s %s", key, values[key])
    return values


def get_measurement(location, test_fail_netatmo=False):

    name = location.name2
    try:
        authorization = lnetatmo.ClientAuth()

        # 2 : Get devices list
        weather_data = lnetatmo.WeatherStationData(authorization)
        logger.debug("%s", weather_data.stationByName(name))
        logger.debug("%s", weather_data.rawData)

        weather_data = get_netatmo_station_data(weather_data.rawData, location.home_id)

        # Inddor
        logger.debug("Inddor data:")
        indoor_values = get_netatmo_indoor_data(weather_data)
        logger.debug("indoor_values=%s", indoor_values)

        # Outdoor
        logger.debug("Outddor data:")
        outdoor_values = get_netatmo_module_data(weather_data, "Temperature")
        logger.debug("outdoor_values=", outdoor_values)

        # Rain
        logger.debug("Rain data")
        rain_values = get_netatmo_module_data(weather_data, "Rain")
        logger.debug("rain_values=%s", rain_values)

        if test_fail_netatmo:
            raise Exception("test_fail_netatmo")

        return indoor_values, outdoor_values, rain_values
    except Exception as exc:
        raise Exception("Could not access and get all Netatmo station data: " + str(exc))


def temp_color(value):
    color = "red"
    if value != "NA" and value < 0:
        color = "blue"
    return color


def temp_text(value):
    if value != "NA":
        txt = "%s" % value
    else:
        txt = "NA"
    return txt


def plot_station_indoor_info(panel, location, indoor_values):

    # Inddor
    panel.delete("all")
    label = str(location.name) + " (inne)"
    len_label = len(label)
    x_pos = int((len_label * 8) * 0.5)
    if hasattr(panel, "indoor_station"):
        panel.delete(indoor_station)
    indoor_station = panel.create_text(x_pos, 12, text=label, font=('verdana', 10))

    updated = "Oppdatert: NA"
    if "time_utc" in indoor_values:
        updated = "Oppdatert: " + datetime.fromtimestamp(indoor_values["time_utc"],
                                                        pytz.timezone('Europe/Amsterdam')).strftime("%H:%M")
    if hasattr(panel, 'netatmo_updated'):
        panel.delete(netatmo_updated)
    netatmo_updated = panel.create_text(300, 10, text=updated, font=('verdana', 10))

    # Temp
    if hasattr(panel, 'indoor_temp'):
        panel.delete(indoor_temp)
    temp = "NA"
    if "Temperature" in indoor_values:
        temp = indoor_values["Temperature"]
    indoor_temp = panel.create_text(60, 40, text=temp_text(temp), fill=temp_color(temp),
                                                font=('verdana', 20))

    # Pressure
    if hasattr(panel, 'indoor_pressure'):
        panel.delete(indoor_pressure)
    pres = "NA"
    if "Pressure" in indoor_values:
        pres = "{0:.0f}".format(round(float(indoor_values["Pressure"]), 0))+' mb'
    indoor_pressure = panel.create_text(45, 90, text=pres, fill="black", font=('verdana', 12))

    # CO2
    if hasattr(panel, 'indoor_co2'):
        panel.delete(indoor_co2)
    co2 = "NA"
    if "CO2" in indoor_values:
        co2 = str(indoor_values["CO2"])
    indoor_co2 = panel.create_text(65, 120, text='co2: '+co2+'ppm', fill="black",
                                            font=('verdana', 12))
    return panel


def plot_station_outdoor_info(panel, location, outdoor_values, rain_values):

    #######################
    # Outdoor
    #######################
    panel.delete("all")
    label = str(location.name) + " (ute)"
    len_label = len(label)
    x_pos = int((len_label * 8) * 0.5)

    if hasattr(panel, "outdoor_station"):
        panel.delete(outdoor_station)
    outdoor_station = panel.create_text(x_pos, 12, text=label, font=('verdana', 10))

    updated = "Oppdatert: NA"
    if "time_utc" in outdoor_values:
        updated = "Oppdatert: " + datetime.fromtimestamp(outdoor_values["time_utc"],
                                                        pytz.timezone('Europe/Amsterdam')).strftime("%H:%M")
    if hasattr(panel, 'netatmo_outdoor_updated'):
        panel.delete(netatmo_outdoor_updated)
    netatmo_outdoor_updated = panel.create_text(300, 12, text=updated, font=('verdana', 10))

    if hasattr(panel, 'outdoor_temp'):
        panel.delete(outdoor_temp)
    temp = "NA"
    if "Temperature" in outdoor_values:
        temp = outdoor_values["Temperature"]
    outdoor_temp = panel.create_text(235, 75, text=temp_text(temp),
                                     fill=temp_color(temp),
                                     font=('verdana', 60))

    # Humidity
    if hasattr(panel, 'outdoor_humidity'):
        panel.delete(outdoor_humidity)
    hum = "NA"
    if "Humidity" in outdoor_values:
        hum = str(outdoor_values["Humidity"])
    outdoor_humidity = panel.create_text(40, 90, text=hum + '%',
                                                            fill="black", font=('verdana', 15))
    # Rain
    if hasattr(panel, 'rain1h'):
        panel.delete(rain1h)
    rain1h = ""
    if "sum_rain_1" in rain_values:
        logger.debug("sum_rain_1 value: %s", rain_values["sum_rain_1"])
        rain1h = "{0:.1f}".format(round(float(rain_values["sum_rain_1"]), 1))+'mm/h'
        logger.debug("sum_rain_1 converted: %s", rain1h)
    else:
        logger.debug("sum_rain_1 not found")
    rain1h = panel.create_text(60, 120, text=rain1h, font=('verdana', 15))
    return panel
