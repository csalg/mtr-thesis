import config


def debug(message):
    if not config.DEBUG:
        return
    print(message)