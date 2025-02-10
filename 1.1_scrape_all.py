from sheet_utils import get_sheet_df

protocol_docs_df = get_sheet_df("main")

urls = protocol_docs_df["Documentation Link"].to_list()
urls = [url for url in urls if url.startswith("https://")]


base_urls = list(map(lambda url: "/".join(url.rstrip("/").split("/")[:3]), urls))

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import trafilatura
from readability import Document
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
import json
import concurrent.futures

# 添加線程鎖來確保輸出不會混亂
print_lock = threading.Lock()


def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)


def scrape_website(base_url):
    # 儲存已處理的 URL
    visited_urls = set()
    visited_urls_lock = threading.Lock()  # 添加鎖來保護 visited_urls

    # 結果儲存
    scraped_data = []
    scraped_data_lock = threading.Lock()  # 添加鎖來保護 scraped_data

    def scrape_page(url, should_follow_links=True):
        # Remove fragment identifier and trailing slash from URL
        url = url.split("#")[0].rstrip("/")

        with visited_urls_lock:
            if url in visited_urls:
                return
            visited_urls.add(url)

        safe_print("Scraping", url)

        try:
            # Send request with proper headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("Content-Type", "").lower()

            if "application/pdf" in content_type:
                # Handle PDF
                import base64

                pdf_base64 = base64.b64encode(response.content).decode("utf-8")

                with scraped_data_lock:
                    scraped_data.append(
                        {
                            "url": url,
                            "type": "pdf",
                            "pdf": pdf_base64,
                            "content": "",
                            "title": None,  # No title for PDFs
                            "links": [],
                        }
                    )

            else:
                # Handle HTML
                try:
                    soup = BeautifulSoup(response.text, "html.parser")
                    text_raw = soup.get_text(separator=" ", strip=True)
                    title = soup.title.string if soup.title else ""
                except Exception as e:
                    print(f"Failed to parse HTML with BeautifulSoup for {url}: {e}")
                    text_raw = ""
                    title = ""
                    soup = None

                try:
                    text_trafilatura = trafilatura.extract(response.text)
                except Exception as e:
                    print(f"Failed to extract text with trafilatura for {url}: {e}")
                    text_trafilatura = ""

                try:
                    doc = Document(response.text)
                    text_readability = BeautifulSoup(
                        doc.summary(), "html.parser"
                    ).get_text(separator=" ", strip=True)
                except Exception as e:
                    print(f"Failed to extract text with readability for {url}: {e}")
                    text_readability = ""

                links = []
                if soup is not None:
                    for a_tag in soup.find_all("a", href=True):
                        link = urljoin(url, a_tag["href"])
                        links.append(link)

                with scraped_data_lock:
                    scraped_data.append(
                        {
                            "url": url,
                            "type": "html",
                            "pdf": None,
                            "content": text_trafilatura,
                            "title": title,
                            "links": links,
                        }
                    )

                if should_follow_links:
                    for link in links:
                        if is_same_domain(link, base_url):
                            scrape_page(link, should_follow_links=True)
                        else:
                            scrape_page(link, should_follow_links=False)

        except requests.RequestException as e:
            safe_print(f"Failed to scrape {url}: {e}")

    def is_same_domain(link, base_url):
        # 檢查連結是否與基底網址同網域
        base_netloc = urlparse(base_url).netloc
        link_netloc = urlparse(link).netloc
        return base_netloc == link_netloc

    # 開始抓取
    scrape_page(base_url, should_follow_links=True)
    return scraped_data


# 修改主程式部分
if __name__ == "__main__":
    # 設定最大線程數
    max_workers = 15  # 可以根據需求調整

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 建立任務列表
        future_to_url = {executor.submit(scrape_website, url): url for url in base_urls}

        # 處理完成的任務
        for future in concurrent.futures.as_completed(future_to_url):
            base_url = future_to_url[future]
            try:
                result = future.result()

                # 輸出結果
                filename = base_url.replace("https://", "").replace("/", "_")
                date_str = datetime.now().strftime("%Y%m%d")
                output_filename = f"{date_str}_{filename}_scraped_data.json"

                with open(output_filename, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=4)

                safe_print(f"Scraping complete. Data saved to {output_filename}.")

            except Exception as e:
                safe_print(f"Error processing {base_url}: {e}")
