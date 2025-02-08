# %%
print("Q")

# %%
# Synchronous Example
from atoma_sdk import AtomaSDK
import os
import uuid

from dotenv import load_dotenv

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


# %%
def process_to_paragraphs(text):
    # Split by newlines
    lines = text.split("\n")

    # Initialize variables
    current_title = None
    current_content = []
    paragraphs = []

    for i, line in enumerate(lines):
        # Skip empty lines
        if not line.strip():
            continue

        # Count words
        word_count = len(line.split())

        # If line has less than 10 words, treat as title
        if word_count < 10:
            # If we have content from previous title, save it
            if current_title and current_content:
                paragraphs.append(
                    {"title": current_title, "content": " ".join(current_content)}
                )

            # Start new section
            current_title = line
            current_content = []

        else:
            # Add to current content
            current_content.append(line)

    # Handle last section
    if current_title and current_content:
        # Check if last line should be merged
        if len(current_content) > 1:
            last_line = current_content[-1]
            if len(last_line.split()) < 10:
                # Merge last line with previous
                current_content[-2] = current_content[-2] + " " + last_line
                current_content.pop()

        paragraphs.append(
            {"title": current_title, "content": " ".join(current_content)}
        )

    return paragraphs


# # Process the text into paragraphs
# text = scraped_data[0]["content"]
# structured_paragraphs = process_paragraphs(text)


# # Print content length for each paragraph
# for i, p in enumerate(structured_paragraphs):
#     print(f"\nParagraph {i+1}:")
#     print(f"Title length: {len(p['title'])}")
#     print(f"Content length: {len(p['content'])}")
#     print(f"Content tokens: {len(tokenizer(p['content'])['input_ids'])}")

# %%
import glob
import json
from datetime import datetime
import os
import queue
import threading
from threading import Thread


# Get today's date in YYYYMMDD format
date_str = datetime.now().strftime("%Y%m%d")

# Find all scraped data files for today
embed_1_2_files = glob.glob(f"{date_str}_*_embed.1.2.json")


def process_document(doc_queue, result_list, stop_event):
    while not stop_event.is_set():
        try:
            doc = doc_queue.get_nowait()
            if doc.get("content"):
                print(doc["url"])
                # Process text into paragraphs
                paragraphs = process_to_paragraphs(doc["content"])

                # Process each paragraph
                doc_paragraph_embeddings = []
                for para in paragraphs:
                    # Format text as "# {title}\n{content}"
                    formatted_text = f"# {para['title']}\n{para['content']}"

                    # Get embedding for the formatted text
                    truncated_text = truncate_text(formatted_text, max_tokens=500)
                    embedding = get_embedding(truncated_text)

                    doc_paragraph_embeddings.append(embedding.data[0].embedding)

                # Store original doc data along with paragraph embeddings
                embedded_doc = {**doc, "paragraph_embeddings": doc_paragraph_embeddings}
                result_list.append(embedded_doc)
            doc_queue.task_done()
        except queue.Empty:
            # No more items to process, exit the thread
            break
        except Exception as e:
            print(f"Error processing document: {e}")
            doc_queue.task_done()


for file_path in embed_1_2_files:
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
    num_threads = 10  # Adjust based on your needs
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
    output_file = f"{date_str}_{site}_embed.1.3.json"

    # Save embedded data
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result_list, f, ensure_ascii=False, indent=4)

    print(f"Saved embeddings to {output_file}")

# %%


# %%
