from llama_cloud import AsyncLlamaCloud
import asyncio
import os

async def parse_document():
    client = AsyncLlamaCloud(api_key="llx-g2wCGMXWWHb4L5gWUh6YDj3KjhmsyLayQwZQryKFURK4VGzw")

    # Upload and parse a document
    file_obj = await client.files.create(file="./RFA2024-pages.pdf", purpose="parse")

    result = await client.parsing.parse(
        file_id=file_obj.id,
        tier="agentic",
        version="latest",
        expand=["markdown_full", "text_full"],
    )

    # Create output folder if it doesn't exist
    os.makedirs("output", exist_ok=True)

    # Save markdown to file
    with open("output/markdown.md", "w", encoding="utf-8") as f:
        f.write(result.markdown_full)
    print("Markdown saved to output/markdown.md")

    # Save text to file
    with open("output/text.txt", "w", encoding="utf-8") as f:
        f.write(result.text_full)
    print("Text saved to output/text.txt")

# Call the function
asyncio.run(parse_document())
