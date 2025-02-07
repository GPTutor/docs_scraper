# %%
print("Q")

# %%
# Synchronous Example
from atoma_sdk import AtomaSDK
import os
from dotenv import load_dotenv
import uuid

# Load environment variables from .env file
load_dotenv()


def get_embedding(text):
    with AtomaSDK(
        bearer_auth=os.getenv("ATOMA_API_KEY", ""),
    ) as atoma_sdk:

        user_id = f"user-{uuid.uuid4()}"

        res = atoma_sdk.embeddings.create(
            input_=text,
            model="intfloat/multilingual-e5-large-instruct",
            encoding_format="float",
            user=user_id,
        )

        return res


# Example usage
# text = "The quick brown fox jumped over the lazy dog"
# embedding = get_embedding(text)
# print(embedding)

# %%
from transformers import AutoTokenizer, AutoModel

tokenizer = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-large-instruct")


def truncate_text(text, max_tokens=512):
    # Tokenize the text
    tokens = tokenizer(text, truncation=False)["input_ids"]

    # If text is already shorter than max_tokens, return as is
    if len(tokens) <= max_tokens:
        return text

    # Truncate to max_tokens and decode back to text
    truncated_tokens = tokens[:max_tokens]
    truncated_text = tokenizer.decode(truncated_tokens)

    return truncated_text


# Example usage
# text = "The quick brown fox jumped over the lazy dog"
# truncated = truncate_text(text)
# print(f"Original length: {len(tokenizer(text)['input_ids'])}")
# print(f"Truncated length: {len(tokenizer(truncated)['input_ids'])}")

# %%
import glob
import json
from datetime import datetime
import os

# Get today's date in YYYYMMDD format
date_str = datetime.now().strftime("%Y%m%d")

# Find all scraped data files for today
scraped_files = glob.glob(f"{date_str}_*_scraped_data.json")
from tqdm import tqdm

for file_path in scraped_files:
    print(f"Processing {file_path}")

    # Read the scraped data
    with open(file_path, "r", encoding="utf-8") as f:
        scraped_data = json.load(f)

    # Process each document
    embedded_data = []
    for doc in tqdm(scraped_data):
        if doc.get("content"):
            # Get embedding for the content

            truncated_text = truncate_text(doc["content"], max_tokens=500)
            embedding = get_embedding(truncated_text)

            # Store original data along with embedding
            embedded_doc = {
                **doc,
                "embedding": embedding.data[0].embedding,
            }
            embedded_data.append(embedded_doc)

    # Generate output filename
    # Extract site name from input filename
    # Input format: YYYYMMDD_site_scraped_data.json
    site = file_path.split("_")[1]
    output_file = f"{date_str}_{site}_embed.1.2.json"

    # Save embedded data
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(embedded_data, f, ensure_ascii=False, indent=4)

    print(f"Saved embeddings to {output_file}")

# %%
