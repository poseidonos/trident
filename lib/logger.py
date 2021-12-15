#/*
# *   BSD LICENSE
# *   Copyright (c) 2021 Samsung Electronics Corporation
# *   All rights reserved.
# *
# *   Redistribution and use in source and binary forms, with or without
# *   modification, are permitted provided that the following conditions
# *   are met:
# *
# *     * Redistributions of source code must retain the above copyright
# *       notice, this list of conditions and the following disclaimer.
# *     * Redistributions in binary form must reproduce the above copyright
# *       notice, this list of conditions and the following disclaimer in
# *       the documentation and/or other materials provided with the
# *       distribution.
# *     * Neither the name of Samsung Electronics Corporation nor the names of
# *       its contributors may be used to endorse or promote products derived
# *       from this software without specific prior written permission.
# *
# *   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# *   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# *   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# *   A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# *   OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# *   SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# *   LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# *   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# *   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# *   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# *   OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# */
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
