import time
import logging

import pywinauto
from win32gui import GetWindowRect, SetForegroundWindow


class AppAssistant:

    def __init__(self, config: dict):
        self.config = config["app"]
        self.logger = logging.getLogger("default")

    def getAppInfoByName(self, appTitle: str, bringToFront: bool = True):
        try:
            app = pywinauto.application.Application(backend="uia")
            appConnection = app.connect(title=appTitle)
            appWindow = appConnection.window(title=appTitle)
            if bringToFront:
                SetForegroundWindow(appWindow.handle)
        except pywinauto.findwindows.ElementNotFoundError:
            return None

        appInfo = dict(appWindow=appWindow, windowRect=GetWindowRect(appWindow.handle))
        return appInfo

    def closeExistingApp(self, appTitle: str):
        appInfo = self.getAppInfoByName(appTitle=appTitle, bringToFront=False)
        if appInfo is None:
            return
        appWindow = appInfo["appWindow"]
        appWindow.close()
        return

    def loadAllApnaComplexApps(self, allBookingArgs: dict) -> None:
        self.logger.info("Initializing BlueStacks Multi Instance Manager.")
        # Close existing Multi Instance Manager and open new window
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
        time.sleep(self.config["sleepDuration"]["smallPause"])
        
        # Click Start to launch all app instances
        managerWindow[self.config["inputElementNames"]["startAllButton"]].click_input()
        time.sleep(self.config["sleepDuration"]["appLoad"])

        # For each app instance, click the ApnaComplex icon to load
        self.logger.info("Loading ApnaComplex app in all instances.")
        allApps = list()
        for idx, bookingArgs in enumerate(allBookingArgs):
            appInfo = self.getAppInfoByName(
                appTitle=self.config["appWindowNames"][idx]
            )
            appInfo["appWindow"].click_input(
                coords=self.getCoordinates(element="apnaComplexIcon")
            )
            allApps.append(appInfo)

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
        SetForegroundWindow(appWindow.handle)
        # Open facilities page
        appWindow.click_input(coords=self.getCoordinates(element="facilitiesButton"))
        time.sleep(self.config["sleepDuration"]["pageLoad"])

        # Click on page header before scrolling
        appWindow.click_input(coords=self.getCoordinates(element="facilitiesHeader"))

        # Scroll to the bottom of the facilities page
        counter = 0
        while counter < self.config["facilitiesScrollCount"]:
            counter += 1
            pywinauto.mouse.scroll(
                coords=self.getCoordinates(
                    element="facilitiesHeader", windowRect=windowRect
                ),
                wheel_dist=-1,
            )
            time.sleep(self.config["sleepDuration"]["smallPause"])

        # Click the tennis court facility icon
        courtNum = bookingArgs["courtNum"]
        appWindow.click_input(
            coords=self.getCoordinates(element=f"tennisCourt{courtNum}Button")
        )
        time.sleep(self.config["sleepDuration"]["pageLoad"])

        # Click slot booking button
        appWindow.click_input(coords=(self.getCoordinates(element="slotBookingButton")))
        time.sleep(self.config["sleepDuration"]["pageLoad"])
        # Click tomorrow toggle
        appWindow.click_input(coords=(self.getCoordinates(element="tomorrowToggle")))
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
        appWindow.click_input(coords=self.getCoordinates(element="timeSlotButton"))
        # Click on book now button
        appWindow.click_input(coords=self.getCoordinates(element="bookNowButton"))
               
        return True

    def confirmAllBookings(self, allApps: list) -> list:
        pywinauto.timings.Timings.fast()
        pywinauto.timings.Timings.after_click_wait = 0.001
        pywinauto.timings.Timings.after_setcursorpos_wait = 0.001
        self.logger.info("Confirming all bookings.")
        successList = list()
        for appInfo in allApps:
            if appInfo is None:
                continue
            isSuccess = self.confirmBooking(windowRect=appInfo["windowRect"])
            if isSuccess:
                successList.append(isSuccess)
        time.sleep(self.config["sleepDuration"]["pageLoad"])
        return successList

    def confirmBooking(self, windowRect: tuple) -> bool:
        try:
            confirmCoords = self.getCoordinates(
                element="confirmButton", windowRect=windowRect
            )
            pywinauto.mouse.click(button="left", coords=confirmCoords)
        except Exception as ex:
            return False
        return True

    def closeAllApnaComplexApps(self) -> None:
        self.logger.info("Closing all app instances and manager window.")
        managerInfo = self.getAppInfoByName(
            appTitle=self.config["multiInstanceManager"]["windowName"]
        )
        managerWindow = managerInfo["appWindow"]
        if managerWindow is None:
            return
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

    def getCoordinates(self, element: str, windowRect: tuple = None):
        windowX, windowY = 0, 0
        if windowRect is not None:
            windowX, windowY = windowRect[0], windowRect[1]
        return (
            windowX + self.config["mousePosition"][element]["x"],
            windowY + self.config["mousePosition"][element]["y"],
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
        startCoords = self.getCoordinates(element=dragStart, windowRect=windowRect)
        stopCoords = self.getCoordinates(element=dragStop, windowRect=windowRect)
        while dragCounter < totalDrags:
            dragCounter += 1
            pywinauto.mouse.press(button="left", coords=startCoords)
            pywinauto.mouse.release(button="left", coords=stopCoords)
            if sleepDuration > 0:
                time.sleep(sleepDuration)
        return
