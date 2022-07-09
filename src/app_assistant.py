from cgi import test
from typing import Optional
import time
import logging

import pywinauto
from pywinauto import keyboard, mouse, timings

from win32api import GetSystemMetrics
from win32gui import GetWindowRect, SetForegroundWindow


class AppAssistant:
    def __init__(self, config: dict):
        self.config = config["app"]
        self.logger = logging.getLogger("default")
        self.screenResolution = dict(x=GetSystemMetrics(0), y=GetSystemMetrics(1))  # type: ignore

    def getAppInfoByName(
        self, appTitle: str, bringToFront: bool = True
    ) -> Optional[dict]:
        try:
            app = pywinauto.application.Application(backend="uia")
            appConnection = app.connect(title=appTitle)
            appWindow = appConnection.window(title=appTitle)
            if bringToFront:
                SetForegroundWindow(appWindow.handle)  # type: ignore
        except pywinauto.findwindows.ElementNotFoundError:
            return None

        appInfo = dict(appWindow=appWindow, windowRect=GetWindowRect(appWindow.handle))  # type: ignore
        return appInfo

    def closeExistingApp(self, appTitle: str) -> None:
        appInfo = self.getAppInfoByName(appTitle=appTitle, bringToFront=False)
        if appInfo is None:
            return
        appWindow = appInfo["appWindow"]
        appWindow.close()
        return

    def loadInstanceManager(self, allBookingArgs: list):
        self.closeExistingApp(
            appTitle=self.config["multiInstanceManager"]["windowName"]
        )
        managerApp = pywinauto.application.Application(backend="uia").start(
            self.config["multiInstanceManager"]["launchPath"]
        )
        managerWindow = managerApp.window(
            title=self.config["multiInstanceManager"]["windowName"]
        )
        # Select app instances based on number of bookings
        for i in range(len(allBookingArgs)):
            selectCheckbox = managerWindow[f"CheckBox{i + 2}"]
            if selectCheckbox.get_toggle_state() == 0:
                selectCheckbox.invoke()
        time.sleep(self.config["sleepDuration"]["instanceLoad"])
        return managerWindow

    def loadAllApnaComplexApps(self, allBookingArgs: list) -> Optional[list]:
        self.logger.info("Initializing BlueStacks Multi Instance Manager.")
        # Close existing Multi Instance Manager and open new window
        managerWindow = self.loadInstanceManager(allBookingArgs=allBookingArgs)

        retries = 0
        isSuccess = False
        allApps = None
        while not isSuccess and retries < self.config["maxRetries"]:
            retries += 1
            try:
                # Click Start to launch all app instances
                managerWindow[
                    self.config["inputElementNames"]["startAllButton"]
                ].click_input()
                time.sleep(self.config["sleepDuration"]["appLoad"])
                # For each app instance, click the ApnaComplex icon to load
                self.logger.info("Loading ApnaComplex app in all instances.")
                allApps = list()
                for idx in range(len(allBookingArgs)):
                    appInfo = self.getAppInfoByName(
                        appTitle=self.config["appWindowNames"][idx]
                    )
                    if appInfo is not None:
                        appInfo["appWindow"].click_input(
                            coords=self.getCoordinates(
                                element="apnaComplexIcon",
                                windowRect=appInfo["windowRect"],
                            )
                        )
                        allApps.append(appInfo)
                        isSuccess = True
            except Exception:
                self.logger.error(
                    f"Couldn't load app instances on attempt {retries} / {self.config['maxRetries']}"
                )
                isSuccess = False

        if not isSuccess:
            return None
        time.sleep(self.config["sleepDuration"]["appLoad"])

        return allApps

    def navigateAllApps(self, allBookingArgs: list, allApps: list) -> list:
        successApps = list()
        for idx, bookingArgs in enumerate(allBookingArgs):
            isSuccess = self.navigateToBooking(
                bookingArgs=bookingArgs, appInfo=allApps[idx]
            )
            successApps.append(allApps[idx])
        return successApps

    def navigateToBooking(self, bookingArgs: dict, appInfo: dict) -> bool:
        appWindow = appInfo["appWindow"]
        windowRect = appInfo["windowRect"]
        if appWindow is None:
            self.logger.error(f"Valid app window not found for {bookingArgs}")
            return False
        self.logger.info(f"Starting navigation to booking page for {bookingArgs}.")

        # Bring app to foreground
        SetForegroundWindow(appWindow.handle)  # type: ignore
        # Open facilities page
        appWindow.click_input(
            coords=self.getCoordinates(
                element="facilitiesButton", windowRect=windowRect
            )
        )
        time.sleep(self.config["sleepDuration"]["pageLoad"])

        # Click on page header before scrolling
        appWindow.click_input(
            coords=self.getCoordinates(
                element="facilitiesHeader", windowRect=windowRect
            )
        )

        # Scroll to the bottom of the facilities page
        counter = 0
        while counter < self.config["facilitiesScrollCount"]:
            counter += 1
            mouse.scroll(
                coords=self.getCoordinates(
                    element="facilitiesHeader", windowRect=windowRect, isAbsolute=True
                ),
                wheel_dist=-1,
            )
            time.sleep(self.config["sleepDuration"]["smallPause"])

        # Click the tennis court facility icon
        courtNum = bookingArgs["courtNum"]
        appWindow.click_input(
            coords=self.getCoordinates(
                element=f"tennisCourt{courtNum}Button", windowRect=windowRect
            )
        )
        time.sleep(self.config["sleepDuration"]["pageLoad"])

        # Click slot booking button
        appWindow.click_input(
            coords=(
                self.getCoordinates(element="slotBookingButton", windowRect=windowRect)
            )
        )
        time.sleep(self.config["sleepDuration"]["pageLoad"])
        # Click tomorrow toggle
        appWindow.click_input(
            coords=(
                self.getCoordinates(element="tomorrowToggle", windowRect=windowRect)
            )
        )
        time.sleep(self.config["sleepDuration"]["smallPause"])
        time.sleep(self.config["sleepDuration"]["smallPause"])

        # Drag  slots to bring the correct slot to starting position
        self.dragMouseOnApp(
            dragStart="timeSlotDragStart",
            dragStop="timeSlotDragStop",
            totalDrags=bookingArgs["slotHour"] - self.config["initialSlotHour"],
            windowRect=windowRect,
        )

        # Click the slot at the starting position
        appWindow.click_input(
            coords=self.getCoordinates(element="timeSlotButton", windowRect=windowRect)
        )
        # Click on book now button
        appWindow.click_input(
            coords=self.getCoordinates(element="bookNowButton", windowRect=windowRect)
        )

        return True

    def confirmAllBookings(self, allApps: list, testRun: bool=False) -> list:
        timings.Timings.fast()
        timings.Timings.after_click_wait = 0.001
        timings.Timings.after_setcursorpos_wait = 0.001
        self.logger.info("Confirming all bookings.")
        successList = list()
        for appInfo in allApps:
            if appInfo is None:
                continue
            isSuccess = self.confirmBooking(windowRect=appInfo["windowRect"], testRun=testRun)
            if isSuccess:
                successList.append(isSuccess)
        time.sleep(self.config["sleepDuration"]["pageLoad"])
        return successList

    def confirmBooking(self, windowRect: tuple, testRun: bool = False) -> bool:
        try:
            confirmCoords = self.getCoordinates(
                element="confirmButton", windowRect=windowRect, isAbsolute=True
            )
            if testRun:
                mouse.move(coords=confirmCoords)
            else:
                mouse.click(button="left", coords=confirmCoords)
        except Exception as ex:
            return False
        return True

    def closeAllApnaComplexApps(self) -> None:
        self.logger.info("Closing all app instances and manager window.")
        managerInfo = self.getAppInfoByName(
            appTitle=self.config["multiInstanceManager"]["windowName"]
        )
        if managerInfo is None or managerInfo["appWindow"] is None:
            return
        managerWindow = managerInfo["appWindow"]
        try:
            # Click Stop All to close all app instances
            managerWindow[
                self.config["inputElementNames"]["stopAllButton"]
            ].click_input()

            # Click Close All in the confirmation dialog
            confirmCloseWindow = managerWindow[
                self.config["inputElementNames"]["closeConfirmDialog"]
            ]
            closeButton = confirmCloseWindow.child_window(
                title=self.config["inputElementNames"]["closeAllButton"],
                control_type="Button",
            )
            closeButton.click_input()
        except pywinauto.findbestmatch.MatchError:
            # No instances running - no apps to close
            pass
        self.closeExistingApp(
            appTitle=self.config["multiInstanceManager"]["windowName"]
        )

        return

    def getCoordinates(self, element: str, windowRect: tuple, isAbsolute: bool = False):
        # Adjustment for different window size
        xSizeAdj = (windowRect[2] - windowRect[0]) / self.config[
            "defaultAppWindowSize"
        ]["x"]
        ySizeAdj = (windowRect[3] - windowRect[1]) / self.config[
            "defaultAppWindowSize"
        ]["y"]
        windowX, windowY = 0, 0
        if isAbsolute:
            windowX, windowY = windowRect[0], windowRect[1]

        return (
            windowX + int(self.config["mousePosition"][element]["x"] * xSizeAdj),
            windowY + int(self.config["mousePosition"][element]["y"] * ySizeAdj),
        )

    def dragMouseOnApp(
        self,
        totalDrags: int,
        dragStart: str,
        dragStop: str,
        windowRect: tuple,
        sleepDuration: int = 0,
    ):
        dragCounter = 0
        startCoords = self.getCoordinates(
            element=dragStart, windowRect=windowRect, isAbsolute=True
        )
        stopCoords = self.getCoordinates(
            element=dragStop, windowRect=windowRect, isAbsolute=True
        )
        while dragCounter < totalDrags:
            dragCounter += 1
            mouse.press(button="left", coords=startCoords)
            mouse.release(button="left", coords=stopCoords)
            if sleepDuration > 0:
                time.sleep(sleepDuration)
        return

    def minimizeAllWindows(self):
        self.logger.info("Minimizing all windows")
        keyboard.send_keys("{ESC}")
        keyboard.send_keys("{VK_LWIN down} {d down} {d up} {VK_LWIN up}")
        centerCoords = int(self.screenResolution["x"] / 2), int(
            self.screenResolution["y"] / 2
        )
        mouse.press(button="left", coords=centerCoords)
        return
