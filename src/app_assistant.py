import time
import logging

import pywinauto
from win32gui import GetWindowRect, SetForegroundWindow


class AppAssistant:
    def __init__(self, config: dict):
        self.config = config["app"]
        self.logger = logging.getLogger("default")

    def getAppWindowByName(self, appTitle: str, bringToFront: bool = True):
        try:
            app = pywinauto.application.Application(backend="uia")
            appConnection = app.connect(title=appTitle)
            appWindow = appConnection.window(title=appTitle)
            if bringToFront:
                SetForegroundWindow(appWindow.handle)
        except pywinauto.findwindows.ElementNotFoundError:
            return None
        return appWindow

    def closeExistingApp(self, appTitle: str):
        appWindow = self.getAppWindowByName(appTitle=appTitle, bringToFront=False)
        if appWindow is not None:
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

        # Click Start to launch all app instances
        managerWindow[self.config["inputElementNames"]["startAllButton"]].click_input()
        time.sleep(self.config["sleepDuration"]["appLoad"])

        # For each app instance, click the ApnaComplex icon to load
        for idx, bookingArgs in enumerate(allBookingArgs):
            appWindow = self.getAppWindowByName(
                appTitle=self.config["appWindowNames"][idx]
            )
            appWindow.click_input(coords=self.getCoordinates(element="apnaComplexIcon"))

        time.sleep(self.config["sleepDuration"]["appLoad"])
        return

    def navigateAllApps(self, allBookingArgs: list) -> list:
        successList = list()
        for idx, bookingArgs in enumerate(allBookingArgs):
            isSuccess = self.navigateToBooking(bookingIdx=idx, bookingArgs=bookingArgs)
            successList.append(isSuccess)
        return successList

    def navigateToBooking(self, bookingIdx: int, bookingArgs: dict) -> bool:
        appWindow = self.getAppWindowByName(
            appTitle=self.config["appWindowNames"][bookingIdx]
        )
        if appWindow is None:
            self.logger.error(
                f"Valid app window not found for Booking # {bookingIdx + 1}"
            )
            return False

        self.logger.info(
            f"Starting navigation to booking page for Booking # {bookingIdx + 1}."
        )

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
                    element="facilitiesHeader", windowHandle=appWindow.handle
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
            windowHandle=appWindow.handle,
        )

        # Click the slot at the starting position
        appWindow.click_input(coords=self.getCoordinates(element="timeSlotButton"))
        # Click on book now button
        appWindow.click_input(coords=self.getCoordinates(element="bookNowButton"))

        time.sleep(self.config["sleepDuration"]["smallPause"])
        return True

    def confirmAllBookings(self, allBookingArgs: list) -> list:
        successList = list()
        for idx, allBookingArg in enumerate(allBookingArgs):
            isSuccess = self.confirmBooking(bookingIdx=idx)
            if isSuccess:
                successList.append(isSuccess)
        time.sleep(self.config["sleepDuration"]["pageLoad"])
        return successList

    def confirmBooking(self, bookingIdx: int) -> bool:
        appWindow = self.getAppWindowByName(
            appTitle=self.config["appWindowNames"][bookingIdx]
        )
        if appWindow is None:
            self.logger.error(
                f"Valid app window not found for Booking # {bookingIdx + 1}"
            )
            return False
        appWindow.click_input(coords=(self.getCoordinates(element="confirmButton")))
        return True

    def closeAllApnaComplexApps(self) -> None:
        self.logger.info("Closing all app instances and manager window.")
        managerWindow = self.getAppWindowByName(
            appTitle=self.config["multiInstanceManager"]["windowName"]
        )
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

    def getCoordinates(self, element: str, windowHandle: int = None):
        windowX, windowY = 0, 0
        if windowHandle is not None:
            windowRect = GetWindowRect(windowHandle)
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
        windowHandle: int,
        sleepDuration: int = 0,
    ):
        dragCounter = 0
        startCoords = self.getCoordinates(element=dragStart, windowHandle=windowHandle)
        stopCoords = self.getCoordinates(element=dragStop, windowHandle=windowHandle)
        while dragCounter < totalDrags:
            dragCounter += 1
            pywinauto.mouse.press(button="left", coords=startCoords)
            pywinauto.mouse.release(button="left", coords=stopCoords)
            if sleepDuration > 0:
                time.sleep(sleepDuration)
        return
