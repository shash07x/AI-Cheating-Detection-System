import numpy as np

def burst_fluency_score(text):

    words=text.split()
    wps=len(words)/5

    lengths=[len(s.split()) for s in text.split(".") if s]
    var=np.var(lengths) if lengths else 0

    return min(100,wps*10+(20-var))