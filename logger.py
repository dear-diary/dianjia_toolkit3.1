import logging
import os
import datetime


# 设置时区
def beijing(sec, what):
    beijing_time = datetime.datetime.now() + datetime.timedelta(hours=8)
    return beijing_time.timetuple()


logging.Formatter.converter = beijing


class Logger:

    file_handler = None
    stream_handler = None

    '''
    handler初始化，保证handler全局唯一
    '''
    @classmethod
    def handler_init(cls):
        # 创建logger对象
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        # 配置处理程序的格式和级别
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        if cls.file_handler is None:
            file_handler = logging.FileHandler(os.path.abspath(os.getcwd()) + '/logs/log_info.log', encoding='UTF-8')
            file_handler.setFormatter(formatter)
            cls.file_handler = file_handler
        if cls.stream_handler is None:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            cls.stream_handler = stream_handler

    '''
    获取logger
    '''
    @classmethod
    def get_logger(cls, file, stream):
        # 创建logger对象
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        if file:
            logger.addHandler(cls.file_handler)
        if stream:
            logger.addHandler(cls.stream_handler)
        return logger


Logger.handler_init()
