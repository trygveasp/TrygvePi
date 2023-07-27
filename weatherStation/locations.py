
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
