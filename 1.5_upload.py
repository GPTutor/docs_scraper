# %%
from datetime import datetime

date_str = datetime.now().strftime("%Y%m%d")
collection_name = f"{date_str}_scraped"

# %%
from qdrant_client import QdrantClient, models
import os

from dotenv import load_dotenv

load_dotenv()

client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
client.create_collection(
    collection_name=collection_name,
    vectors_config={
        "content": models.VectorParams(size=1024, distance=models.Distance.COSINE),
        "paragraph": models.VectorParams(
            size=1024,
            distance=models.Distance.COSINE,
            multivector_config={"comparator": "max_sim"},
        ),
    },
)

# %%
import glob

embed_files = glob.glob(f"{date_str}_*.1.4.json")

# %%
import json

all_data = []
index = 1
for file in embed_files:
    with open(file, "r") as f:
        print("Uploading", file)
        data = json.load(f)
        all_data.extend(data)


# Remove duplicates based on URL
seen_urls = set()
for item in all_data:
    if item["url"].split("?")[0].split("#")[0] not in seen_urls:
        seen_urls.add(item["url"].split("?")[0].split("#")[0])
        item["duplicated"] = False
    else:
        item["duplicated"] = True

for payload in all_data:
    embedding = payload.pop("embedding")
    paragraph_embeddings = payload.pop("paragraph_embeddings")
    if len(paragraph_embeddings) == 0:
        paragraph_embeddings = [[0] * 1024]
    try:
        result = client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=index,
                    vector={
                        "content": embedding,
                        "paragraph": paragraph_embeddings,
                    },
                    payload=payload,
                )
            ],
        )
    except Exception as e:
        print(f"Error uploading point {index}: {e}")
        continue
    index += 1
print("Done")

# %%
