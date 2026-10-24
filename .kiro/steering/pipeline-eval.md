---
inclusion: manual
---
# Pipeline evaluation (run with /pipeline-eval)
Run `make eval`. Summarize: per-document classification accuracy, per-field extraction accuracy, grounding rate, and false-pass count (months marked "meets" from extracted data that ground truth says are not "meets"). If false passes > 0, find the cause and propose a fix. Append the headline numbers to docs/KIRO_LOG.md under "Evaluation".
