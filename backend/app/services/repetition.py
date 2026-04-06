def repetition_score(text):

    w=text.lower().split()
    if not w:return 0
    return (1-len(set(w))/len(w))*100