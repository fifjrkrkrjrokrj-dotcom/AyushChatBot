from Radhe import mongo

RADHE = mongo["RADHEDb"]["RADHE"] if mongo is not None else None

from .chats import *
from .users import *
from .admins import *
