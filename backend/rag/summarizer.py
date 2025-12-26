from transformers import T5ForConditionalGeneration, T5Tokenizer

class Summarizer:
    def __init__(self):
        self.tokenizer = T5Tokenizer.from_pretrained("t5-small")
        self.model = T5ForConditionalGeneration.from_pretrained("t5-small")

    def summarize(self, question, context, style_instructions, max_len=180):

        prompt = (
            "Answer the question using the content. "
            "Style: " + style_instructions + ". "
            "Question: " + question + ". "
            "Content: " + context
        )

        inputs = self.tokenizer.encode(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )

        output = self.model.generate(
            inputs,
            max_length=max_len,
            min_length=40,
            num_beams=4,
            early_stopping=True
        )

        return self.tokenizer.decode(output[0], skip_special_tokens=True)
