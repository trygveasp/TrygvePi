import requests
import xml.etree.ElementTree
import dateutil.parser
from datetime import datetime, timedelta
import numpy as np
from log import logger

from datetime import timedelta, datetime
import matplotlib

from matplotlib.collections import LineCollection
import numpy as np
matplotlib.use('TkAgg')


def get_screen_time_dimension(now, days):
    hours = days*24
    times = []
    dts = []
    for t in range(0, hours):
        times.append(t)
        dts.append(now + timedelta(hours=t))
    return times, dts

def get_time_indices(dts, values_in=None, test_increase=0, days=5):
    if values_in is not None and len(dts) != len(values_in):
        raise Exception("Mismatch in length: "+str(len(dts))+" != "+str(len(values_in)))

    now = datetime.utcnow()
    now = now.replace(second=0, minute=0, microsecond=0)
    indices = []
    values = []
    j = 0
    __, screen_dts = get_screen_time_dimension(now, days)
    for dt in dts:
        for t in range(0, len(screen_dts)):
            if dt == screen_dts[t]:
                indices.append(t)
                if values_in is not None:
                    values.append(values_in[j] + test_increase)
        j = j + 1

    indices = np.asarray(indices)
    values = np.asarray(values)
    if values_in is not None:
        return indices, values
    else:
        return indices

def plot_location_forecast(panel, axP, ax_wind, acc_vars1h, other_vars, test_increase=0, days=5):
    now = datetime.utcnow()
    precipitation = []
    precipitation_min = []
    precipitation_max = []
    prec_times = []
    var = "precipitation"
    for time in sorted(acc_vars1h):
        prec_times.append(time)
        precipitation.append(acc_vars1h[time][var]["value"])
        precipitation_min.append(acc_vars1h[time][var]["minvalue"])
        precipitation_max.append(acc_vars1h[time][var]["maxvalue"])

    prec_indices, precipitation = get_time_indices(prec_times, values_in=precipitation, test_increase=test_increase, days=days)
    temperature = []
    windspeed = []
    times = []
    for time in sorted(other_vars):
        var = "temperature"
        times.append(time)
        temperature.append(float(other_vars[time][var]["value"]))
        var = "windSpeed"
        windspeed.append(float(other_vars[time][var]["mps"]))

    temp_indices, temperature = get_time_indices(times, values_in=temperature, test_increase=test_increase, days=days)

    wind_indices, windspeed = get_time_indices(times, values_in=windspeed, test_increase=test_increase, days=days)

    c = ['r' if t > 0 else 'b' for t in temperature]
    lines = [((x0, y0), (x1, y1)) for x0, y0, x1, y1 in zip(temp_indices[:-1], temperature[:-1],
                                                            temp_indices[1:],
                                                            temperature[1:])]
    colored_lines = LineCollection(lines, colors=c, linewidths=(2,))
    panel.clear()
    axP.clear()
    ax_wind.clear()
    panel.set_ylim(bottom=np.min(temperature) - 1, top=np.max(temperature) + 1)
    panel.add_collection(colored_lines)

    pmax = max(np.maximum(precipitation_max, 2))
    axP.bar(prec_indices, height=precipitation_max, width=1, fill=False, hatch="//", edgecolor=(0.2, 0.4, 0.6, 0.6))
    axP.bar(prec_indices, height=precipitation, width=1, color=(0.2, 0.4, 0.6, 0.6))
    axP.set_ylim(bottom=0, top=pmax)
    pticks = [0]
    for i in range(0, 5):
        pticks.append(round((pmax * i / 5), 1))
    pticks.append(pmax)
    axP.axes.set_yticks(ticks=pticks)
    ax_wind.plot(wind_indices, windspeed, color="grey", linestyle="dotted")
    today = now.replace(hour=0, second=0, minute=0, microsecond=0)
    ticks = []
    labels = []
    for d in range(1, days+1):
        ticks.append(today+timedelta(days=d))
        labels.append((today+timedelta(days=d)).strftime("%d/%m"))

    tick_positions = get_time_indices(ticks, test_increase=test_increase, days=days)
    panel.axes.set_xticks(ticks=tick_positions, minor=False)
    panel.axes.set_xticklabels(labels, fontdict=None, minor=False)
    ax_wind.spines['right'].set_position(('outward', 30))
    ax_wind.set_ylim(0, 15)
    return panel

def get_location_forecast(location, variables, test_fail_forecast=False,
                          timeout_forecast=5):

    latitude = location.lat
    longtude = location.lon
    msl = location.msl

    request_string = "https://api.met.no/weatherapi/locationforecast/2.0/classic/?lat={lat}&lon={lon}&altitude={msl}".format(
        lat=latitude, lon=longtude, msl=msl)
    logger.debug("request_string=%s", request_string)

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

        for __, time in enumerate(product.findall('time')):
            from_data = time.get('from')
            to_data = time.get('to')
            dt_from = dateutil.parser.parse(from_data, ignoretz=True)
            dt_to = dateutil.parser.parse(to_data, ignoretz=True)
            logger.debug("dt_from=%s dt_to=%s",dt_from, dt_to)

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
                                    logger.debug("v.tag=%s v.attrib=%s a=%s", v.tag, v.attrib, a)
                                    value = float(value) / float(acc_time)
                                atts.update({a: value})

                            logger.debug("time=%s var=%s atts=%s", time, var, atts)
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
                                logger.debug("v.tag=%s v.attrib=%s", v.tag, v.attrib)
                                value = v.get(a)
                                var_atts.update({a: value})

                        var_data.update({var: var_atts})

                    other_vars.update({dt_to: var_data})
            else:
                raise Exception("Should not happen " + str(dt_from) + " -> " + str(dt_to))

        if test_fail_forecast:
            raise Exception("test_fail_forecast")

        return acc_vars1h, other_vars, acc_vars2h, acc_vars3h, acc_vars6h
    except Exception as exc:
        raise Exception("Could not get location forecast " + str(exc))
