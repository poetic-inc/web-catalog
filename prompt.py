EXTRACTION_PROMPT = """
You are an expert web data extractor. Your task is to parse the provided markdown content of a webpage and extract specific information into a JSON object that strictly adheres to the given Pydantic schema.

Focus on extracting:
- The URL of the page.
- The main name or title of the page.
- A list of products, categorized as specified.
- For each product, extract its category and a list of individual items.
- For each item, extract its name, price, and its specific URL.

Ensure all fields are populated accurately based on the content. If a piece of information is not present, omit that specific field or provide an empty list/string as appropriate for the schema. Do not invent data.
"""
