import os
import sys
import pathlib
import json
import logging
import logging.config

sys.path.append(os.path.join(pathlib.Path(__file__).parent, "src"))

from booking_assistant import BookingAssistant


def main():
    # Load config
    configFilePath = os.path.join(pathlib.Path(__file__).parent, "config.json")
    with open(configFilePath) as configJson:
        config = json.load(configJson)
        
    credsFilePath = os.path.join(pathlib.Path(__file__).parent, config["web"]["credentialsFile"])
    with open(credsFilePath) as credsJson:
        config["web"]["apnaComplexCreds"] = json.load(credsJson)

    # Set logging config
    logConfigPath = os.path.join(pathlib.Path(__file__).parent, "log_config.json")
    with open(logConfigPath) as logConfigJson:
        logConfig = json.load(logConfigJson)
    logging.config.dictConfig(logConfig)

    bookingAssistant = BookingAssistant(config=config)
    bookingAssistant.makeBookings()
    return


if __name__ == "__main__":
    main()
