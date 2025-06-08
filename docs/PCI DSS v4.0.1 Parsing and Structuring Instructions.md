# PCI DSS v4.0.1 Parsing and Structuring Instructions

## Objective

This document outlines the tasks the team needs to perform to parse, organize, and prepare the PCI DSS v4.0.1 document (`PCI-DSS-v4_0_1.pdf`) for structured use within our PCI Compliance Agent. Your output will feed directly into our retrieval system and interface logic.

## Output Directory

All output files should be saved in the `/docs` directory.

## Deliverables

| Filename | Description |
| :---- | :---- |
| `requirement_index.json` | JSON with structured data for each PCI requirement |
| `parsed_requirements.md` | Markdown with all requirements in readable format |
| `taxonomy.md` *(optional)* | Overview of tags/categories used to organize requirements |
| `parsing_notes.md` *(optional)* | Notes about special cases or logic assumptions |

## Task Checklist

### 1\. Parse All Requirements

Start from **page 36** of the document. Extract each PCI requirement into a structured format.

For each requirement, extract:

- `id`: e.g. `1.1.2`  
- `text`: full requirement statement  
- `tags`: list of category tags if mentioned (e.g., `network`, `authentication`)  
- `summary`: leave empty initially and fill in using LLM (see guidance below)  
- `section`: e.g., `Build and Maintain a Secure Network and Systems`  
- `page`: PDF page number where it appears (optional but helps for trust/transparency)

### 2\. Build `requirement_index.json`

This file must contain an array of all parsed requirements. Example:

\[

  {

    "id": "1.1.2",

    "text": "Review firewall and router rule sets at least every six months.",

    "tags": \["network"\],

    "summary": "Ensure firewall rules are reviewed biannually to keep configurations secure.",

    "section": "Build and Maintain a Secure Network and Systems",

    "page": 45

  }

\]

### 3\. Write `parsed_requirements.md`

Markdown version of all requirements with readable formatting. Include:

\#\# Requirement 1.1.2

\*\*Section\*\*: Build and Maintain a Secure Network and Systems  

\*\*Page\*\*: 45  

\*\*Tags\*\*: network  

\*\*Text\*\*: Review firewall and router rule sets at least every six months.  

\*\*Summary\*\*: Ensure firewall rules are reviewed biannually to keep configurations secure.

### 4\. Define Summary Generation Strategy

Leave the `summary` field blank on first pass. Later, generate summaries using LLM with similar prompt:

*“Summarize the following PCI DSS requirement in plain language (1–2 lines). Focus on what the organization must do and why.”*

Insert the result under `"summary"`. If unclear or incomplete, use `"summary": "[TODO]"`.

### 5\. (Optional) Define a Tag Taxonomy

If you apply tags to help categorize requirements (e.g. `network`, `encryption`, `authentication`), describe them in a file named `taxonomy.md`.

If unsure about tags, either leave them blank or use `["uncategorized"]` as a placeholder.

### 6\. (Optional) Document Special Cases

If there are irregular formats or edge cases, note them in `parsing_notes.md`.

## Reference & Notes

- Start parsing from page **36** onward — this is where the "Detailed PCI DSS Requirements and Testing Procedures" section begins.  
- Use regex or line-based parsing to detect lines like:  
  - `Requirement 1.1.2:`  
  - or `1.1.2 Review firewall...`  
- If a requirement spans multiple lines or paragraphs, include the entire block.  
- You may omit **testing procedures** for now unless they are clearly marked.

## Internal QA Checklist

- [ ] Does every requirement have an `id`, `text`, `section`?  
- [ ] Are tag choices consistent across similar requirements?  
- [ ] Are all summaries ≤ 2 lines and written in plain language?  
- [ ] No fields are null or missing without explanation

## Sample Prompt You Can Use

Please extract all requirement entries from the PCI DSS v4.0.1 PDF starting from page 36 onward. Structure each entry as JSON with keys: id, text, tags, and optionally summary. Save your parsed results to' requirement\_index.json' and a Markdown overview in' parsed\_requirements. md'. Store everything in /docs. Let me know if you hit edge cases.

# Support Tools 

### Python Libraries for PDF Parsing

- [`pdfplumber`](https://github.com/jsvine/pdfplumber): Excellent for fine-grained, line-by-line text extraction. Preserves layout.  
- [`PyMuPDF` (fitz)](https://pymupdf.readthedocs.io): Fast and memory-efficient; good for extracting pages and bounding boxes.  
- [`pdfminer.six`](https://github.com/pdfminer/pdfminer.six): Detailed control over text extraction, but more complex.  
- [`PyPDF2`](https://github.com/py-pdf/pypdf): Useful for splitting, merging, or reading basic text—not as powerful for layout-sensitive parsing.

### LLM Access for Summarization

- [Ollama](https://ollama.com): For running models like Mistral or LLaMA locally.  
- [`openai` Python client](https://github.com/openai/openai-python): For remote GPT-4/3.5 APIs (if policy allows).  
- [`transformers`](https://github.com/huggingface/transformers): Local summarization using open-source models from HuggingFace.

### Regex and Rule-Based Extraction

- Python's built-in `re` module  
- [regex101.com](https://regex101.com/): For testing and debugging regex patterns

### Data Manipulation and Export

- `json`, `jsonlines`: For reading/writing structured output  
- `pandas`: For debugging and QA of structured data  
- `markdown`, `rich`, or `tabulate`: For formatted terminal output (optional)

### Batch Processing / QA

- `tqdm`: For visual progress bars  
- `click` or `argparse`: To turn your scripts into reusable CLI tools  
- `unittest` or `pytest`: For validation and correctness checks

### IDE / Editor Extensions

- VSCode with:  
  - **Python** extension  
  - **Markdown Preview Enhanced**  
  - **Regex Previewer**  
  - **Jupyter Notebooks** (for testing parsing logic interactively)

