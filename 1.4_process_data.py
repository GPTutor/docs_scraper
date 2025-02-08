# %%
print("Q")

# %%
from sheet_utils import get_sheet_df

protocol_docs_df = get_sheet_df("main")

# %%


# %%
import glob
import json
from datetime import datetime

# Get today's date in YYYYMMDD format
date_str = datetime.now().strftime("%Y%m%d")

# List all embedding files with the specified pattern
embed_files = glob.glob(f"{date_str}_*_embed.1.3.json")
print("\nEmbedding files:")
for f in embed_files:
    doc_url = f.replace(f"{date_str}_", "").replace("_embed.1.3.json", "")
    name = protocol_docs_df[
        protocol_docs_df["Documentation Link"].apply(lambda x: doc_url in x)
    ]["Protocol Name"].to_list()[0]
    with open(f, "r") as f:
        data = json.load(f)
        for doc in data:
            doc["source"] = name
            # Generate output filename
        output_file = f.replace("_embed.1.3.json", ".1.4.json")

        # Save processed data
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"Saved processed data to {output_file}")

# %%
