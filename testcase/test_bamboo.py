import pytest, json, sys, time, random, os
sys.path.insert(0, '../')
import logger
logger = logger.get_logger(__name__)

@pytest.mark.bamboo
def test_bamboo():
    logger.info("sample TCS for bamboo")
