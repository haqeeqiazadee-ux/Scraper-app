# TASK: Recursive QA Execution and Input Validation Simulator

We have implemented an extensive set of adapters, schemas, and scraping logic capable of tackling the vast majority of the 27,000+ rows found in the `apify_catalog_implementation_mapping.csv`. To bridge the gap from "capable" to "production-verified," we need a robust, recursive testing strategy.

You are acting as an autonomous QA simulation agent. Your goal is to systematically iterate through every unique use-case mapped in the catalog, deduce the required input permutations, simulate execution, and validate the output schema.

## Step 1: Initialize the Test Environment Context
You must establish a dynamic test runner environment. Instead of testing one hardcoded URL, you will create a test factory.
- Write a Python script (`scripts/recursive_test_runner.py`) that reads `/app/docs/apify_catalog_implementation_mapping.csv`.
- Group the rows by `Required Code/Logic Used` and `Categories` to minimize redundant tests (e.g., all basic E-commerce extractors behave similarly).
- For each unique group, programmatically generate a list of 3-5 diverse, realistic target URLs (e.g., a Shopify product, an Amazon ASIN, a generic WooCommerce link).

## Step 2: Input Parameter Inference
Many scrapers require specific inputs (e.g., pagination limits, stealth requirements, geo-proxies). For each test group:
- Deduce all possible configuration input values that a user might provide based on the group's "Missing/Required Components" and category.
- Example: If the group is "Travel", the test parameters MUST explicitly trigger the `TravelStealthProfile` and require `residential` proxies.
- Example: If the group is "Job Board", parameters must include `extraction_type="job_board"`.

## Step 3: Recursive Execution Loop
Execute the test factory in a recursive loop:
1. Initialize the local Control Plane (FastAPI) test instance using `TestClient`.
2. For each defined input permutation within a test group, submit a POST request to `/api/v1/tasks/execute` (or `/api/v1/smart-scrape`).
3. Intercept the JSON response.
4. **Validation:** Dynamically validate the `extracted_data` payload against the corresponding Pydantic schemas (e.g., `JobListing`, `RealEstateListing`). If the schema is "auto", ensure fundamental fields (like `name`, `price`, `url`) exist.
5. If a test fails (schema mismatch, 403 block, crash), log the exact failure reason into a new artifact file: `docs/qa_simulation_failures.csv`.
6. Proceed to the next input permutation automatically until all grouped use-cases are covered.

## Constraint and Guidelines
- **Zero-Trust Validation:** Do not assume a 200 OK means success. You must parse the `confidence` score and validate the payload structure.
- **Rate-Limit Awareness:** Ensure the test runner respects local API rate limits or mocks out the `RateLimiter` dependency to prevent the recursive loop from blocking itself.
- **Traceability:** At the end of the run, output a summary report detailing the pass/fail rate for every catalog group tested.

By completing this strategy, you will definitively prove whether the native architecture and the newly implemented adapters are truly robust enough to replace the targeted external platform services.
