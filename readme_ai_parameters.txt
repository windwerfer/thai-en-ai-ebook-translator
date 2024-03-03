
# https://medium.com/@daniel.puenteviejo/the-science-of-control-how-temperature-top-p-and-top-k-shape-large-language-models-853cb0480dae


# temperature

Higher temperature=higher chances for less likely tokens to be selected.
 As temperature values approach 0 the probability to select the words with higher probabilities valuez increase further, making their selection much more likely. 
 Conversely, when the temperature gets much higher, the probabilities between the words that can be selected are softened, making more unexpected words more likely to be selected
 0=strickt, 1=creative/random

 # top_k = diversity
 def: Top_k (Top-k Sampling): It restricts the selection of tokens to the “k” most likely options, based on their probabilities. This prevents the model from considering tokens with very low probabilities, making the output more focused and coherent.
 top-k is a technique used to limit the number of possible next tokens during text generation
def: 
op_k=top_k,   # default: 1 


def: Top_p (Nucleus Sampling): It selects the most likely tokens from a probability distribution, considering the cumulative probability until it reaches a predefined threshold “p”. This limits the number of choices and helps avoid overly diverse or nonsensical outputs.
op_p=top_p,  # Set top_p, default: 1.0 

 for translations try: temperature=0.3, top_k=20


 ??? The temperature and top_p for underrepresented language generation must be set very low. Lower than in ChatGPT. The perplexity of languages with small amounts of training corpus (think Vietnamese, Portuguese) is very high, like a model with 1/100th the knowledge as English plus the confusion of having English in there also.

 ??? The AI wasn’t pretrained on language simply to be a translator. It’s more “Throw all human knowledge we’ve got in there”…and see the quality that can come out.























**** huggingface ****

Precise:    factual responses and straightforward assistant answers	
creative:   chatting, storywriting, and interesting assistant answers	
Sphinx:     varied storywriting (on 30B/65B) and unconventional chatting
            Precise	        Creative	    Sphinx
temperature	0.7	            0.72	        1.99
top_k	    40	            0	            30
top_p	    0.1	            0.73	        0.18
repetition 
 penalty	1.176 (1/0.85)	1.1	            1.15
