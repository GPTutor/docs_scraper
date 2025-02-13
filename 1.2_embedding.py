# %%
print("Q")

# %%
# Synchronous Example
from atoma_sdk import AtomaSDK
import os
from dotenv import load_dotenv
import uuid
import queue
import threading
from threading import Thread
from concurrent.futures import ThreadPoolExecutor

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


def process_document(doc_queue, result_list, stop_event):
    while not stop_event.is_set():
        try:
            doc = doc_queue.get_nowait()
            if doc.get("content"):
                print(doc["url"])
                truncated_text = truncate_text(doc["content"], max_tokens=500)
                embedding = get_embedding(truncated_text)

                embedded_doc = {
                    **doc,
                    "embedding": embedding.data[0].embedding,
                }
                result_list.append(embedded_doc)
            doc_queue.task_done()
        except queue.Empty:
            # No more items to process, exit the thread
            break
        except Exception as e:
            print(f"Error processing document: {e}")
            doc_queue.task_done()


for file_path in scraped_files:
    print(f"Processing {file_path}")

    # Read the scraped data
    with open(file_path, "r", encoding="utf-8") as f:
        scraped_data = json.load(f)

    # Initialize queue and result list
    doc_queue = queue.Queue()
    result_list = []
    stop_event = threading.Event()

    # Fill the queue with documents
    for doc in scraped_data:
        doc_queue.put(doc)

    # Create and start worker threads
    num_threads = 50  # Adjust based on your needs
    threads = []
    for _ in range(num_threads):
        thread = Thread(
            target=process_document, args=(doc_queue, result_list, stop_event)
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)

    # Wait for all documents to be processed
    doc_queue.join()
    stop_event.set()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Generate output filename
    site = file_path.split("_")[1]
    output_file = f"{date_str}_{site}_embed.1.2.json"

    # Save embedded data
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result_list, f, ensure_ascii=False, indent=4)

    print(f"Saved embeddings to {output_file}")

# %%
