import os
import sys
import pathlib
import json
import logging
import logging.config

sys.path.append(os.path.join(pathlib.Path(__file__).parent, "src"))

from booking_assistant import BookingAssistant

def getCmdLineArg(args: list, arg: str) -> bool:
    dateArgs = []
    intArgs = ["slotHour"]
    strArgs = []
    argValue = None if arg in (dateArgs + intArgs) else False
    argVar = f"-{arg}"
    if (len(args) > 1) and (argVar in args):
        argIdx = args.index(argVar) + 1
        argValue = args[argIdx] == "True"
        if not argValue:
            if arg in dateArgs:
                try:
                    argValue = datetime.strptime(args[argIdx], "%Y-%m-%d")
                except ValueError:
                    argValue = None
                    print(
                        f"Invalid date argument for {arg}. Expected format is YYYY-MM-DD."
                    )
            elif arg in intArgs:
                try:
                    argValue = int(args[argIdx])
                except ValueError:
                    argValue = None
                    print(f"Invalid integer argument for {arg}.")
            elif arg in strArgs:
                try:
                    argValue = str(args[argIdx])
                except ValueError:
                    argValue = None
                    print(f"Invalid string argument for {arg}.")
    return argValue


def main():
    onlyConfirm = getCmdLineArg(sys.argv[1:], "onlyConfirm")
    slotHour = getCmdLineArg(sys.argv[1:], "slotHour")
    
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

    if slotHour is not None:
        config["slotHour"] = slotHour
    
    bookingAssistant = BookingAssistant(config=config)
    
    if onlyConfirm:
        bookingAssistant.onlyConfirm()
    else:
        bookingAssistant.makeBookings()
    
    return


if __name__ == "__main__":
    main()
