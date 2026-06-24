# FastAPI User Flows

Record feature flows that affect user behavior, API behavior, AI processing, or Spring compatibility.

## Template

```text
## Flow: <feature name>
Date:
Status: draft | implemented | changed

User action:
Spring API:
FastAPI API:
Input source:
Service flow:
External APIs:
Response:
Failure cases:
Spring compatibility:
Open decisions:
```

## Flow: Experience Extraction Step1
Date: 2026-06-02
Status: draft

User action:
User provides a resume or cover letter source.

Spring API:
`POST /api/experiences/extract/step1`.

FastAPI API:
`POST /api/v1/extract-experiences/step1`.

Input source:
PDF file, URL, or text depending on caller.

Service flow:
FastAPI extracts high-level experience summaries and returns selectable candidates.

External APIs:
May use LLM and document parsing services depending on input source.

Response:
Experience summaries with name, group, and type.

Failure cases:
Missing input source, malformed PDF, external API failure, timeout, invalid model output.

Spring compatibility:
Response must remain compatible with Spring `AiStep1Response`.

Open decisions:
Confirm any new experience classification types before adding them.

## Flow: Experience Extraction Step2
Date: 2026-06-20
Status: changed

User action:
User selects step1 experience candidates for detailed extraction.

Spring API:
`POST /api/experiences/extract/step2`.

FastAPI API:
`POST /api/v1/extract-experiences/step2` or
`POST /api/v1/extract-experiences/step2-v2`.

Input source:
Original file, URL, or text plus `selected_experiences`. V2 also requires
Spring `PresetRegistry` schemas and accepts existing experiences.

Service flow:
FastAPI extracts detailed fields for each selected experience and applies merge candidate detection when existing experiences are provided.
V2 builds each `basic_info` output model from the runtime preset, rejects undeclared fields,
and checks each result against existing experiences plus earlier accepted results in selection order.

External APIs:
May use LLM, embeddings, URL parsing, and document parsing services.

Response:
Detailed experiences including `basic_info`, keywords, content, and merge metadata.
Batch-local merge candidates use IDs in the form `batch:{selected_index}` for Spring to resolve.

Failure cases:
Missing source, invalid request JSON, missing or mismatched preset schema, undeclared `basic_info`
field, external API failure, or timeout.

Spring compatibility:
Response must remain compatible with Spring `AiStep2Response`.

Open decisions:
Confirm merge threshold and rule changes before modifying merge behavior.

## Flow: Notice Analysis
Date: 2026-06-02
Status: draft

User action:
User submits a job notice URL or PDF.

Spring API:
`POST /api/notices/analyze/url` or `POST /api/notices/analyze/pdf`.

FastAPI API:
`POST /api/v1/analyze/url` or `POST /api/v1/analyze/pdf`.

Input source:
Job notice URL or PDF.

Service flow:
FastAPI parses the notice and returns structured company, section, process, document, and citation data.

External APIs:
May use Firecrawl, Upstage Document AI, Gemini, and OpenAI depending on input source.

Response:
Structured job posting data.

Failure cases:
Invalid URL, unsupported PDF, external API failure, timeout, invalid model output.

Spring compatibility:
Response must remain compatible with Spring `AiJobPostingResponse`.

Open decisions:
Confirm confidence handling before changing low-confidence analysis behavior.
