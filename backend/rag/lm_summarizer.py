import re
from groq import Groq
import os
# Get your free API key from: https://console.groq.com
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # ← PUT YOUR API KEY HERE
MODEL_NAME = "llama-3.3-70b-versatile"  # FREE 70B model!


class LMSummarizer:
    def __init__(self, api_key: str = GROQ_API_KEY):
        self.client = Groq(api_key=api_key)
        self.model = MODEL_NAME

    def summarize(self, question: str, context: str, style_instructions: str, max_tokens: int = 2048) -> str:
        # Extract number if "N points" is mentioned
        n_points = re.search(r'(\d+)\s+(?:advantages?|disadvantages?|points?|reasons?|benefits?|characteristics?)', question.lower())
        
        if n_points:
            num = n_points.group(1)
            strict_instruction = f"\n\nCRITICAL: Provide EXACTLY {num} DIFFERENT and DISTINCT points. Use numbered format: 1) 2) 3)... Stop immediately after point {num}."
        else:
            strict_instruction = ""
        
        prompt = f"""You are an exam-helper AI. Answer the question using ONLY the context given.

Question:
{question}

Context:
{context}

Style instructions:
{style_instructions}

Rules:
- Start directly with the answer. Do NOT write any introduction.
- Each numbered point MUST be a completely DIFFERENT concept
- Keep each point concise (2-3 sentences maximum)
- Do NOT repeat similar ideas with different wording
- Finish your last sentence fully before stopping{strict_instruction}

Now write the answer:
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3,
                top_p=0.9,
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Groq API Error: {e}")
            raise