#!/usr/bin/python2.7
# encoding=utf-8

import os
try:
    import Tkinter as tkinter
except ModuleNotFoundError:
    import tkinter

from screen import Screen
from locations import Location
from log import logger

if __name__ == "__main__":

    ids = ["5ea2e122a91a6479dd163b47", "629bb3dab578163e8439299f", "5ea2ded4a91a64e6511638e0", "63fcbc6f10e8eeb6a00fe448"]
    names = ["Meiselen 19", "Hokksund", "Solbakken", "Skareseter"]
    names2 = ["Aspelien Konnerud (Indoor)", "Hokksund Stasjonsby (Indoor)", "Solbakken (Indoor)", "Skareseterveien (Indoor)"]
    latitudes = [59.7350, 59.766965, 59.7516, 60.287246]
    longitudes = [10.1242, 9.909917, 10.3204, 9.296931]
    msls = [231, 12, 170, 909]

    keys = ["CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN"]
    for key in keys:
        if key in os.environ:
            os.environ.pop(key)

    stations = []
    for iloc in range(0, len(names)):
        stations.append(Location(ids[iloc], names[iloc], longitudes[iloc], latitudes[iloc], msls[iloc], names2[iloc]))

    root = tkinter.Tk()
    screen = Screen(root, stations,
                    test_fail_netatmo=False,
                    test_fail_forecast=False,
                    test_fail_nowcast=False,
                    show_netatmo=True,
                    show_nowcast=True,
                    show_forecast=True,
                    updtime=300000,
                    # updtime=5000,
                    timeout_netatmo=5,
                    timeout_nowcast=4,
                    timeout_forecast=5,
                    update=True
                    )
    root.mainloop()
