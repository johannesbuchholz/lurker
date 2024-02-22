import logging

# create logger
LOG = logging.getLogger("Lurker")
LOG.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('[%(levelname)8s] %(name)s: %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
LOG.addHandler(ch)
