import time
import logging

import subprocess
from win32gui import (
    FindWindow,
    GetWindowRect,
    SetForegroundWindow,
    IsWindowVisible,
    EnumWindows,
    GetWindowText,
)
import pyautogui


class AppAssistant:
    def __init__(self, config: dict):
        self.config = config["app"]
        self.logger = logging.getLogger("default")

    def loadAllApnaComplexApps(self, allBookingArgs: dict) -> list:
        self.logger.info("Initializing BlueStacks Multi Instance Manager.")
        allWindowHandles = dict()

        # Open Multi Instance Manager
        subprocess.Popen(self.config["multiInstanceManager"]["launchPath"])
        time.sleep(self.config["sleepDuration"]["smallPause"])
        windowHandle = FindWindow(
            None, self.config["multiInstanceManager"]["windowName"]
        )
        allWindowHandles["manager"] = windowHandle

        SetForegroundWindow(windowHandle)
        windowRectangle = GetWindowRect(windowHandle)
        # Click Select all instances
        pyautogui.moveTo(
            windowRectangle[0]
            + self.config["mousePosition"]["selectInstancesButton"]["x"],
            windowRectangle[1]
            + self.config["mousePosition"]["selectInstancesButton"]["y"],
        )
        pyautogui.click()

        # Click Start all instances
        pyautogui.moveTo(
            windowRectangle[0]
            + self.config["mousePosition"]["startInstancesButton"]["x"],
            windowRectangle[1]
            + self.config["mousePosition"]["startInstancesButton"]["y"],
        )
        pyautogui.click()
        time.sleep(self.config["sleepDuration"]["appLoad"])

        self.logger.info("Loading ApnaComplex app instances.")

        allWindowHandles["apps"] = list()
        for idx, bookingArgs in enumerate(allBookingArgs):
            windowName = self.config["appWindowNames"][idx]
            windowHandle = FindWindow(None, windowName)
            SetForegroundWindow(windowHandle)
            windowRectangle = GetWindowRect(windowHandle)
            # Click ApnaComplex app icon
            pyautogui.moveTo(
                windowRectangle[0]
                + self.config["mousePosition"]["apnaComplexIcon"]["x"],
                windowRectangle[1]
                + self.config["mousePosition"]["apnaComplexIcon"]["y"],
            )
            pyautogui.click()
            allWindowHandles["apps"].append(windowHandle)

        time.sleep(self.config["sleepDuration"]["appLoad"])
        return allWindowHandles

    def navigateAllApps(self, appWindowHandles: list, allBookingArgs: list) -> list:
        successList = list()
        for idx, appWindowHandle in enumerate(appWindowHandles):
            isSuccess = self.navigateToBooking(
                windowHandle=appWindowHandle, bookingArgs=allBookingArgs[idx]
            )
            if isSuccess:
                successList.append(appWindowHandle)
        return successList

    def navigateToBooking(self, windowHandle: int, bookingArgs: dict) -> bool:
        if not IsWindowVisible(windowHandle):
            self.logger.error(
                f"Window handle {windowHandle} not found - unable to navigate"
            )
            return False

        SetForegroundWindow(windowHandle)
        windowRectangle = GetWindowRect(windowHandle)

        self.logger.info(f"Starting navigation to booking page for {windowHandle}.")

        # Open facilities page
        pyautogui.moveTo(
            windowRectangle[0] + self.config["mousePosition"]["facilitiesButton"]["x"],
            windowRectangle[1] + self.config["mousePosition"]["facilitiesButton"]["y"],
        )
        pyautogui.click()
        time.sleep(self.config["sleepDuration"]["pageLoad"])

        # Click on page header before scrolling
        pyautogui.moveTo(
            windowRectangle[0] + self.config["mousePosition"]["facilitiesHeader"]["x"],
            windowRectangle[1] + self.config["mousePosition"]["facilitiesHeader"]["y"],
        )
        pyautogui.click()

        # Scroll to the bottom of the facilities page
        counter = 0
        while counter < self.config["scrollCount"]:
            counter += 1
            pyautogui.scroll(-self.config["scrollLength"])
            time.sleep(self.config["sleepDuration"]["smallPause"])

        # Click the tennis court facility icon
        courtNum = bookingArgs["courtNum"]
        pyautogui.moveTo(
            windowRectangle[0]
            + self.config["mousePosition"][f"tennisCourt{courtNum}Button"]["x"],
            windowRectangle[1]
            + self.config["mousePosition"][f"tennisCourt{courtNum}Button"]["y"],
        )
        pyautogui.click()
        time.sleep(self.config["sleepDuration"]["pageLoad"])

        # Click slot booking button
        pyautogui.moveTo(
            windowRectangle[0] + self.config["mousePosition"]["slotBookingButton"]["x"],
            windowRectangle[1] + self.config["mousePosition"]["slotBookingButton"]["y"],
        )
        pyautogui.click()
        time.sleep(self.config["sleepDuration"]["pageLoad"])

        # Click tomorrow toggle
        pyautogui.moveTo(
            windowRectangle[0] + self.config["mousePosition"]["tomorrowToggle"]["x"],
            windowRectangle[1] + self.config["mousePosition"]["tomorrowToggle"]["y"],
        )
        pyautogui.click()
        time.sleep(self.config["sleepDuration"]["smallPause"])
        time.sleep(self.config["sleepDuration"]["smallPause"])

        # Drag  slots to bring the correct slot to starting position
        dragCounter = 0
        totalDrags = bookingArgs["slotHour"] - self.config["initialSlotHour"]
        while dragCounter < totalDrags:
            dragCounter += 1
            pyautogui.moveTo(
                windowRectangle[0] + self.config["mousePosition"]["timeSlotDrag"]["x"],
                windowRectangle[1] + self.config["mousePosition"]["timeSlotDrag"]["y"],
            )
            pyautogui.click()
            pyautogui.drag(
                -self.config["slotDragLength"],
                0,
                self.config["sleepDuration"]["smallPause"],
                button="left",
            )

        # Click the slot at the starting position
        pyautogui.moveTo(
            windowRectangle[0] + self.config["mousePosition"]["timeSlotButton"]["x"],
            windowRectangle[1] + self.config["mousePosition"]["timeSlotButton"]["y"],
        )
        pyautogui.click()

        # Click on book now button
        pyautogui.moveTo(
            windowRectangle[0] + self.config["mousePosition"]["bookNowButton"]["x"],
            windowRectangle[1] + self.config["mousePosition"]["bookNowButton"]["y"],
        )
        pyautogui.click()
        time.sleep(self.config["sleepDuration"]["smallPause"])
        return True

    def confirmAllBookings(self, appWindowHandles: list) -> list:
        successList = list()
        for appWindowHandle in appWindowHandles:
            isSuccess = self.confirmBooking(windowHandle=appWindowHandle)
            if isSuccess:
                successList.append(appWindowHandle)        
        time.sleep(self.config["sleepDuration"]["pageLoad"])
        return successList

    def confirmBooking(self, windowHandle: int) -> bool:
        if not IsWindowVisible(windowHandle):
            self.logger.error(
                f"Window handle {windowHandle} not found - unable to confirm booking"
            )
            return False

        SetForegroundWindow(windowHandle)
        windowRectangle = GetWindowRect(windowHandle)
        pyautogui.moveTo(
            windowRectangle[0] + self.config["mousePosition"]["confirmButton"]["x"],
            windowRectangle[1] + self.config["mousePosition"]["confirmButton"]["y"],
        )
        pyautogui.click()
        return True

    def minimizeAllWindows(self):
        self.logger.info("Minimizing all windows")
        pyautogui.keyDown("winleft")
        pyautogui.press("d")
        pyautogui.keyUp("winleft")
        screenSize = pyautogui.size()
        pyautogui.moveTo(int(screenSize[0] / 2), int(screenSize[1] / 2))
        pyautogui.click()
        return

    def closeAllApnaComplexApps(self, windowHandle: int) -> bool:
        if not IsWindowVisible(windowHandle):
            self.logger.error(
                f"Manager window handle {windowHandle} not found - unable to close apps."
            )
            return False
        
        self.logger.info("Shutting down all app instances")
        
        SetForegroundWindow(windowHandle)
        windowRectangle = GetWindowRect(windowHandle)
        # Click Select all instances
        pyautogui.moveTo(
            windowRectangle[0]
            + self.config["mousePosition"]["selectInstancesButton"]["x"],
            windowRectangle[1]
            + self.config["mousePosition"]["selectInstancesButton"]["y"],
        )
        pyautogui.click()

        # Click Stop all instances
        pyautogui.moveTo(
            windowRectangle[0]
            + self.config["mousePosition"]["startInstancesButton"]["x"],
            windowRectangle[1]
            + self.config["mousePosition"]["startInstancesButton"]["y"],
        )
        pyautogui.click()
        
        # Click Confirm stop all instances
        pyautogui.moveTo(
            windowRectangle[0]
            + self.config["mousePosition"]["confirmCloseButton"]["x"],
            windowRectangle[1]
            + self.config["mousePosition"]["confirmCloseButton"]["y"],
        )
        pyautogui.click()
        
        # Close manager window
        pyautogui.moveTo(
            windowRectangle[0]
            + self.config["mousePosition"]["managerCloseButton"]["x"],
            windowRectangle[1]
            + self.config["mousePosition"]["managerCloseButton"]["y"],
        )
        pyautogui.click()
        
        return
