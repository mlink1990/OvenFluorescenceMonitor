import os
import sys

if sys.platform == "win32":
    ursaGroupFolder = "G:"
    humphryNASFolder = "N:"
    humphryNASTemporaryData = "T:"
elif sys.platform == "linux2":
    ursaGroupFolder = os.path.join(os.sep,"media","ursa","AQOGroupFolder")
    humphryNASFolder = os.path.join(os.sep,"media","humphry-nas","Humphry")
    humphryNASTemporaryData = os.path.join(os.sep,"media","humphry-nas","TemporaryData")
else:
    raise NotImplementedError()