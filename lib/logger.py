import logging
import sys
import os
import datetime
import platform
from logging.handlers import TimedRotatingFileHandler

path = (
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    + "/logs/POS_"
    + datetime.datetime.now().strftime("%Y-%m-%d_%H_%M")
)
FORMATTER = logging.Formatter(
    "%(asctime)s %(filename)s %(funcName)s %(lineno)s %(levelname)s  :: %(message)s"
)
LOG_FILE = "{}/pos_execution".format(path) + ".log"


def mkdir_p(path):
    """
    Method: to create log dir
    :param path: path of log dir
    :return: None
    """

    if not os.path.exists(path):
        os.makedirs(path)


def get_console_handler():
    """
    Method to get console handler
    :return: console handler
    """
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_file_handler():

    """
    Method: to get file handler
    :return: file handler
    """
    mkdir_p(path)
    file_handler = TimedRotatingFileHandler(LOG_FILE, when="H", interval=48)
    file_handler.setFormatter(FORMATTER)
    return file_handler


def get_logger(logger_name):
    """
    Method :  to get logger
    :param logger_name: Logger name
    :return: logger

    Usage:
    logger= logger.get_logger(__name__)

    """

    logger = logging.getLogger(logger_name)
    if not getattr(logger, "handler_set", None):
        logger.setLevel(logging.DEBUG)  # better to have too much log than not enough
        logger.addHandler(get_console_handler())
        logger.addHandler(get_file_handler())
        logger.propagate = False
        logger.handler_set = True
    return logger


def get_logname():
    """

    :return: log name

    Method: to get the log name  file name

    usage:
    logger.get_logname()
    """
    return LOG_FILE


def get_logpath():
    """

    :return: log path

    Method: to get the logpath
    usage:
    logger.get_logpath()
    """
    return path
