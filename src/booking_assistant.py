import time
from datetime import datetime, timedelta

import logging
from web_assistant import WebAssistant
from app_assistant import AppAssistant


class BookingAssistant:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.logger = logging.getLogger("default")

    def getAllBookingArgs(self) -> dict:
        self.logger.info(f"Checking existing bookings.")
        webAssistant = WebAssistant(config=self.config)
        # Get existing booking counts for each court
        slotHour, bookingDatetime = webAssistant.getBookingTimeSlot(
            slotHour=self.config["slotHour"],
            nextHourCutoff=self.config["nextHourCutoff"],
        )
        existingBookings, courtLinks = webAssistant.getExistingBookings(
            apartmentName=self.config["apartmentName"]
        )
        # Get list of available courts
        courtNumList = webAssistant.selectCourtNum(
            existingBookings=existingBookings,
            numSlots=self.config["numSlots"],
        )
        if courtNumList is None:
            self.logger.error("Too many active bookings found. Can't book any more.")
            return None, None

        # Create booking arguments for each court booking
        allBookingArgs = [
            dict(courtNum=courtNum, slotHour=slotHour) for courtNum in courtNumList
        ]
        return allBookingArgs, slotHour, bookingDatetime

    def sleepTillOpeningTime(self, bookingDatetime: datetime):
        self.logger.info("Sleeping till booking time arrives.")
        timeRemaining = bookingDatetime - datetime.now()
        sleepTime = self.config["sleepDuration"]["long"]
        while timeRemaining >= timedelta(hours=24):
            time.sleep(sleepTime)
            timeRemaining = bookingDatetime - datetime.now()
            if timeRemaining < timedelta(
                hours=24, minutes=0, seconds=(self.config["sleepDuration"]["long"] * 2)
            ):
                sleepTime = self.config["sleepDuration"]["short"]

        return

    def makeBookings(self) -> None:
        appAssistant = AppAssistant(config=self.config)
        # Get booking arguments based on existing bookings
        allBookingArgs, slotHour, bookingDatetime = self.getAllBookingArgs()
        if allBookingArgs is None:
            return

        # Book courts using the app assistant
        self.logger.info(
            f"Booking {len(allBookingArgs)} slots for {slotHour}:00 hours."
        )

        allApps = appAssistant.loadAllApnaComplexApps(allBookingArgs=allBookingArgs)
        allApps = appAssistant.navigateAllApps(
            allBookingArgs=allBookingArgs, allApps=allApps
        )
        if not allApps:
            return

        self.sleepTillOpeningTime(bookingDatetime=bookingDatetime)
        successList = appAssistant.confirmAllBookings(allApps=allApps)
        appAssistant.closeAllApnaComplexApps()

        return

    def onlyConfirm(self) -> None:
        appAssistant = AppAssistant(config=self.config)
        webAssistant = WebAssistant(config=self.config)
        # Get existing booking counts for each court
        slotHour, bookingDatetime = webAssistant.getBookingTimeSlot(
            slotHour=self.config["slotHour"],
            nextHourCutoff=self.config["nextHourCutoff"],
        )
        # Fallback for confirming on manually opened windows
        allApps = [
            appAssistant.getAppInfoByName(
                appTitle=f"ApnaComplex{i+1}", bringToFront=True
            )
            for i in range(self.config["maxSlots"])
        ]
        self.sleepTillOpeningTime(bookingDatetime=bookingDatetime)
        successList = appAssistant.confirmAllBookings(allApps=allApps)
        appAssistant.closeAllApnaComplexApps()
        
        return
