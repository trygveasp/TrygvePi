import requests
import xml.etree.ElementTree
import dateutil.parser
from datetime import datetime
from log import logger

def get_nowcast(location, test_fail_nowcast=False, timeout_nowcast=4):

    # Coordinates
    latitiude = location.lat
    longitude = location.lon

    request_string = "https://api.met.no/weatherapi/nowcast/2.0/classic?lat={lat}&lon={lon}".format(lat=latitiude,
                                                                                             lon=longitude)
    logger.debug("request_string: %s", request_string)
    try:
        # Website data
        headers = {"User-Agent": "TrygvePi https://github.com/trygveasp/TrygvePi trygve@aspelien.no"}
        try:
            response = requests.get(request_string, timeout=timeout_nowcast, headers=headers)
        except TimeoutError:
            raise TimeoutError(request_string + " timed out with timeout " + str(timeout_nowcast))

        minutes = []
        values = []

        # Gets the website data
        logger.debug("content=%s", response.content)
        doc_root = xml.etree.ElementTree.fromstring(response.content)
        logger.debug("doc_root=%s", doc_root)
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
            for __, tup in enumerate(weather_data):
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
    except Exception as exc:
        raise Exception("Could not get nowcast: " + str(exc))


def plot_nowcast(panel, minutes, values):
    panel.clear()
    ticks = [0, 15, 30, 45, 60, 75, 90]
    panel.axes.get_xaxis().set_ticks(ticks)
    if len(values) > 0:
        lines = panel.plot(minutes, values)
        lines[0].set_ydata(values)
        panel.set_ylim(bottom=0., top=max(values)+0.2)

        if max(values) > 0:
            panel.fill_between(minutes, 0, values)
    return panel