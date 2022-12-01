import time
from datetime import datetime, timedelta

import logging
from typing import Tuple
from web_assistant import WebAssistant
from app_assistant import AppAssistant


class BookingAssistant:
    def __init__(self, config: dict, testRun: bool) -> None:
        self.config = config
        self.logger = logging.getLogger("default")
        self.testRun = testRun

    def getAllBookingArgs(self) -> Tuple[list, int, datetime]:
        self.logger.info(f"Checking existing bookings.")

        webAssistant = WebAssistant(config=self.config)
        # Get existing booking counts for each court
        slotHour, bookingDatetime = webAssistant.getBookingTimeSlot(
            slotHour=self.config["slotHour"],
            nextHourCutoff=self.config["nextHourCutoff"],
        )

        # Use dummy data for test run
        if self.testRun:
            return self.getDummyBookingArgs()
        elif self.config["numSlots"] > self.config["maxSlots"]:
            return self.getMaxBookingArgs(
                slotHour=slotHour, bookingDatetime=bookingDatetime
            )

        existingBookings, _ = webAssistant.getExistingBookings(
            apartmentName=self.config["apartmentName"]
        )
        # Get list of available courts
        courtNumList = webAssistant.selectCourtNum(
            existingBookings=existingBookings,
            numSlots=self.config["numSlots"],
        )
        if courtNumList is None:
            self.logger.error("Too many active bookings found. Can't book any more.")
            return list(), slotHour, bookingDatetime

        # Create booking arguments for each court booking
        allBookingArgs = [
            dict(courtNum=courtNum, slotHour=slotHour) for courtNum in courtNumList
        ]
        return allBookingArgs, slotHour, bookingDatetime

    def sleepTillOpeningTime(self, bookingDatetime: datetime):
        self.logger.info("Sleeping till booking time arrives.")
        timeRemaining = bookingDatetime - datetime.now()
        sleepTime = self.config["sleepDuration"]["long"]
        while timeRemaining >= timedelta(hours=24, minutes=00, seconds=1):
            time.sleep(sleepTime)
            timeRemaining = bookingDatetime - datetime.now()
            if timeRemaining < timedelta(
                hours=24, minutes=0, seconds=(self.config["sleepDuration"]["long"] * 2)
            ):
                sleepTime = self.config["sleepDuration"]["short"]

        return

    def makeBookings(self) -> None:
        appAssistant = AppAssistant(config=self.config)

        # Minimize all open windows
        appAssistant.minimizeAllWindows()

        # Get booking arguments based on existing bookings
        allBookingArgs, slotHour, bookingDatetime = self.getAllBookingArgs()
        if allBookingArgs is None:
            return

        # Book courts using the app assistant
        self.logger.info(
            f"Booking {len(allBookingArgs)} slots for {slotHour}:00 hours."
        )

        # allBookingArgs, _, bookingDatetime = self.getDummyBookingArgs()
        allApps = appAssistant.loadAllApnaComplexApps(allBookingArgs=allBookingArgs)
        if not allApps:
            return

        allApps = appAssistant.navigateAllApps(
            allBookingArgs=allBookingArgs, allApps=allApps
        )
        if not allApps:
            return

        self.sleepTillOpeningTime(bookingDatetime=bookingDatetime)
        successList = appAssistant.confirmAllBookings(
            allApps=allApps, testRun=self.testRun
        )

        if not self.testRun:
            appAssistant.closeAllApnaComplexApps()

        return

    def onlyConfirm(self) -> None:
        appAssistant = AppAssistant(config=self.config)
        webAssistant = WebAssistant(config=self.config)
        # Get existing booking counts for each court
        _, bookingDatetime = webAssistant.getBookingTimeSlot(
            slotHour=self.config["slotHour"],
            nextHourCutoff=self.config["nextHourCutoff"],
        )
        # Fallback for confirming on manually opened windows
        allApps = [
            appAssistant.getAppInfoByName(
                appTitle=f"ApnaComplex{i+1}", bringToFront=True
            )
            for i in range(self.config["numSlots"])
        ]
        
        print(allApps)
        
        self.sleepTillOpeningTime(bookingDatetime=bookingDatetime)
        successList = appAssistant.confirmAllBookings(allApps=allApps)
        appAssistant.closeAllApnaComplexApps()

        return

    def getMaxBookingArgs(
        self, slotHour: int, bookingDatetime: datetime
    ) -> Tuple[list, int, datetime]:
        bookingArgs = list()
        for i in range(self.config["numSlots"] // 2):
            bookingArgs.append(dict(courtNum=1, slotHour=slotHour))
            bookingArgs.append(dict(courtNum=2, slotHour=slotHour))
        return bookingArgs, slotHour, bookingDatetime

    def getDummyBookingArgs(self) -> Tuple[list, int, datetime]:
        slotHour = 10
        bookingArgs = [
            dict(courtNum=1, slotHour=slotHour),
            dict(courtNum=1, slotHour=slotHour),
        ]
        bookingDatetime = datetime.now() + timedelta(minutes=1)
        return bookingArgs, slotHour, bookingDatetime
