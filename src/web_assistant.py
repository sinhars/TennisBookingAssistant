import time
import datetime
import logging
from typing import Dict, List, Optional


from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import SessionNotCreatedException


class WebAssistant:
    def __init__(self, config: dict) -> None:
        self.config = config["web"]
        self.logger = logging.getLogger("default")

    def getApnaComplexDriver(self) -> WebDriver:
        options = Options()
        options.binary_location = self.config["chromeBinaryPath"]
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        try:
            driver = webdriver.Chrome(
                options=options, executable_path=self.config["chromeDriverExe"]
            )
        except SessionNotCreatedException:
            failureMsg = "Chrome driver is outdated. Please download the latest version from https://chromedriver.chromium.org/downloads"
            self.logger.error(failureMsg)
            quit()

        # Navigate to facilities page url
        driver.get(self.config["apnaComplexURL"])
        # Enter email
        emailBox = driver.find_element(by=By.ID, value="email")
        emailBox.send_keys(self.config["apnaComplexCreds"]["email"])
        # Enter password
        pwdBox = driver.find_element(by=By.ID, value="password")
        pwdBox.send_keys(self.config["apnaComplexCreds"]["password"])
        # Submit login form
        pwdBox.submit()
        # Wait for page to load
        WebDriverWait(driver, self.config["webDriverDelay"]).until(
            EC.presence_of_element_located((By.ID, "facilities"))
        )
        return driver

    def isValidCourt(
        self, allCells: list[WebElement], courtNum: Optional[int]
    ) -> tuple:
        facilityName = allCells[0].text
        isTennisCourt = facilityName.startswith("Tennis Court")
        if not isTennisCourt:
            return False, 0
        currentCourtNum = int(facilityName.split(" ")[-1])
        isValid = (courtNum is None) or (courtNum == currentCourtNum)
        return isValid, currentCourtNum

    def getCourtLinks(
        self, driver: WebDriver, delay: int, courtNum: Optional[int]
    ) -> dict:
        courtLinks: Dict[str, Dict[str, Optional[str]]] = dict(
            viewing=dict(Court1=None, Court2=None),
            booking=dict(Court1=None, Court2=None),
        )
        linkTitles = dict(
            viewing="View bookings for this facility",
            booking="Make a booking for this facility",
        )

        facilitiesTable = driver.find_element(By.ID, "facilities")
        allFacilityRows = facilitiesTable.find_elements(By.XPATH, ".//tbody//tr")
        allFacilityRows.reverse()
        for row in allFacilityRows:
            allCells = row.find_elements(By.XPATH, ".//td")
            isValid, currentCourtNum = self.isValidCourt(allCells, courtNum)
            if isValid:
                allLinks = allCells[-1]
                allLinks = allLinks.find_elements(By.XPATH, ".//a")
                for currentLink in allLinks:
                    imageTitle = currentLink.find_elements(By.XPATH, ".//img")[
                        0
                    ].get_attribute("title")
                    linkURL = currentLink.get_attribute("href")
                    if imageTitle == linkTitles["viewing"]:
                        courtLinks["viewing"][f"Court{currentCourtNum}"] = linkURL
                    elif imageTitle == linkTitles["booking"]:
                        courtLinks["booking"][f"Court{currentCourtNum}"] = linkURL

        return courtLinks

    def getActiveBookings(
        self, driver: WebDriver, delay: int, viewingURL: str, apartmentName: str
    ) -> int:
        def getBookingCount(bookingCalendar, checkExpired):
            bookingCount = 0
            eventsContainer = bookingCalendar.find_elements(
                By.CLASS_NAME, "fc-event-container"
            )
            allEvents = eventsContainer[-1].find_elements(By.CLASS_NAME, "fc-event")
            for bookingEvent in allEvents:
                bookingApartment = bookingEvent.find_element(
                    By.CLASS_NAME, "fc-event-title"
                ).text
                bookingSlot = bookingEvent.find_element(
                    By.CLASS_NAME, "fc-event-time"
                ).text
                if checkExpired and int(bookingSlot[0]) < datetime.datetime.now().hour:
                    continue
                if apartmentName in bookingApartment:
                    bookingCount += 1
            return bookingCount

        bookingCount = 0
        try:
            driver.get(viewingURL)
            bookingCalendar = WebDriverWait(driver, delay).until(
                EC.element_to_be_clickable((By.ID, "calendar"))
            )
            buttonClasses = ["fc-button-agendaDay", "fc-button-next"]
            for buttonClass in buttonClasses:
                checkExpired = buttonClass == "fc-button-agendaDay"
                dayViewButton = bookingCalendar.find_element(By.CLASS_NAME, buttonClass)
                dayViewButton.click()
                time.sleep(1)
                bookingCount += getBookingCount(
                    bookingCalendar=bookingCalendar, checkExpired=checkExpired
                )

        except Exception as ex:
            self.logger.error("Unknown error occured during active booking checks.")
            self.logger.error(ex)

        return bookingCount

    def getExistingBookings(self, apartmentName: str) -> tuple:
        # Initialize the webdriver and navigate to facilities page
        driver = self.getApnaComplexDriver()
        # Get the court booking and viewing links from the facilities table
        courtLinks = self.getCourtLinks(
            driver=driver, delay=self.config["webDriverDelay"], courtNum=None
        )
        viewingLinks = courtLinks["viewing"]
        existingBookings: Dict[str, Optional[int]] = dict(Court1=None, Court2=None)
        try:
            for court in viewingLinks:
                existingBookings[court] = self.getActiveBookings(
                    driver=driver,
                    delay=self.config["webDriverDelay"],
                    viewingURL=viewingLinks[court],
                    apartmentName=apartmentName,
                )
        except Exception as ex:
            self.logger.error(f"Booking failed while checking exising bookings.")
            self.logger.error(ex)

        driver.close()
        driver.quit()
        return existingBookings, courtLinks

    def getBookingTimeSlot(self, slotHour: int, nextHourCutoff: int) -> tuple:
        if slotHour is None:
            slotHour = int(datetime.datetime.now().strftime("%H"))
            currentMin = int(datetime.datetime.now().strftime("%M"))
            if currentMin > nextHourCutoff:
                slotHour += 1

        bookingDatetime = datetime.datetime.now() + datetime.timedelta(days=1)
        bookingDatetime = bookingDatetime.replace(
            hour=slotHour, minute=0, second=0, microsecond=1
        )
        return slotHour, bookingDatetime

    def selectCourtNum(self, existingBookings: dict, numSlots: int) -> Optional[list]:
        maxBookableSlots = 4
        alreadyUsedSlots = existingBookings["Court1"] + existingBookings["Court2"]
        avaiableSlots = maxBookableSlots - alreadyUsedSlots
        if avaiableSlots <= 0:
            return None

        numSlots = min(numSlots, avaiableSlots)
        courtNumList:List[Optional[int]] = [None] * numSlots

        newBookings = existingBookings.copy()
        courtPreference = ["Court1", "Court2"]
        for i in range(numSlots):
            if newBookings[courtPreference[0]] < 2:
                courtNumList[i] = int(courtPreference[0][-1])
                newBookings[courtPreference[0]] += 1
            elif newBookings[courtPreference[1]] < 2:
                courtNumList[i] = int(courtPreference[1][-1])
                newBookings[courtPreference[1]] += 1

        return courtNumList
