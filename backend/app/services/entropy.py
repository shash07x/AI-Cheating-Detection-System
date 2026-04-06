from transformers import GPT2Tokenizer,GPT2LMHeadModel

tok=GPT2Tokenizer.from_pretrained("gpt2")
model=GPT2LMHeadModel.from_pretrained("gpt2")

def entropy_score(text):

    inp=tok(text,return_tensors="pt")
    loss=model(**inp,labels=inp["input_ids"]).loss
    return min(100,loss.item()*20)