# E-Commerce Catalog Formatter for AI

This open-source Python library provides tools to convert e-commerce websites into structured product catalogs. The primary goal is to generate data that AI agents can readily consume and act upon.

## Motivation

Interfacing AI agents with e-commerce websites presents several challenges:
*   **Diverse Structures**: E-commerce sites vary significantly in layout, navigation, and how product information is presented.
*   **Dynamic Content**: Content is often loaded dynamically, making simple scraping difficult.
*   **Human-Centric Design**: Sites are optimized for human users, not programmatic access, leading to friction for automated agents.
*   **Brittle Automation**: Traditional web automation scripts for individual sites are often fragile and break with minor website updates.

This project aims to provide a more robust and generalized solution for accessing e-commerce product data.

## Approach

The library employs a multi-agent system to:
1.  **Analyze Website Structure**: Understand the target site's layout, identify product sections, and determine navigation patterns (including pagination).
2.  **Strategically Crawl**: Systematically navigate the website to discover product pages.
3.  **Extract Product Information**: Parse relevant data (name, price, categories, URLs, etc.) from product pages.
4.  **Format for AI**: Structure the extracted data into a consistent, machine-readable format (e.g., JSON based on a Pydantic schema), suitable for AI agent consumption.

By abstracting the complexities of individual e-commerce sites, this library allows developers to focus on building AI agent logic rather than site-specific scraping.

## Key Features

*   **Automated Crawling**: Implements strategies (BFS, DFS, Best-First) for navigating e-commerce sites.
*   **Structured Data Extraction**: Extracts product details and formats them according to a defined schema.
*   **Configurable Filtering**: Allows filtering of crawled URLs by pattern, domain, and content type.
*   **Agent-Based Architecture**: Utilizes a system of specialized agents for analysis, filtering, and extraction.
*   **Designed for AI Integration**: Produces output tailored for use in AI agent workflows.

## High-Level Workflow

1.  **Initial Analysis**: An agent analyzes the entry-point URL to devise a crawling plan, identifying key product sections and URL patterns.
2.  **Filter Configuration**: Based on the analysis, filters are set up to guide the crawler.
3.  **Crawling & Extraction**: The appropriate crawling strategy is executed, visiting pages and extracting content.
4.  **Data Formatting**: Extracted content is transformed into a structured product catalog.
