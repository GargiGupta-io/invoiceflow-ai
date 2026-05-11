# Expected Outputs

These JSON files are evaluation targets for the sample cases.

They are not meant to represent exact model wording. Instead, they capture the
minimum structured facts and decision outcomes that the pipeline should produce.

Each expected output may include:

- `expected_extraction`: key fields that should be captured correctly
- `expected_decision`: the workflow result the system should reach
- `must_cite`: source sections the retrieval layer should surface as evidence
- `must_flag_anomalies`: anomaly codes that should appear in the final result
