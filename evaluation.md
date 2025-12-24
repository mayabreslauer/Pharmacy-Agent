# Evaluation Plan – Pharmacy Agent

This document describes the evaluation methodology for validating the functionality, reliability, and correctness of the Pharmacy Agent system.
The goal is to ensure that the Agent, its tools, and the multi-step workflows operate as expected across a variety of scenarios.

## 1. Objectives of the Evaluation

The evaluation focuses on four main pillars:
* Functional Accuracy: Verify that the Agent uses the correct tools, retrieves valid data from the database, and produces accurate final responses.
* Multi-Step Flow Reliability: Ensure that the Agent successfully completes multi-step workflows involving sequential tool calls and reasoning steps.
* Streaming Stability (SSE): Confirm that the backend streams tokens to the frontend in real time and that UI updates smoothly.
* Language Adaptation: Confirm that the Agent responds correctly in both Hebrew and English and can adapt mid-conversation if the user switches languages.
* User Experience: Ensure the frontend receives incremental streaming (SSE) without freezing and the Agent provides responses smoothly.

## 2. Methodology – How to Evaluate

Evaluation is performed via automated tests and manual checks:

* Unit Tests & Flow Tests: Execute tests for each tool call and each flow step (like the provided Python test scripts).
* Multi-Step Workflows: Validate that the Agent executes all steps sequentially without errors, preserving context and history between messages.
* Streaming / SSE Checks: Confirm that the frontend receives incremental tokens in real-time and the UI remains responsive.
* Logging Verification: Check that all tool calls are logged correctly, including tool name, user_id (if applicable), and result.
* Edge Case Scenarios: Test responses for missing data, unknown medications, invalid input formats, or language switches.

## 3. Success Criteria / Metrics

* Correctness: The correct tool is called (tool calls), responses contain expected values (should_contain) and do not contain forbidden phrases (should_not_contain)
* Robustness: No hallucinations when information is missing, graceful handling of invalid input
* Language Adaptation: Responses match the user's language, mid-flow language switches are handled seamlessly
* Multi-Step Handling:, All steps in multi-step flows are executed successfully, context is maintained across messages
* Streaming / SSE Handling: No crashes during streaming, frontend receives incremental updates smoothly

## 4. Evaluation Checklist for Reviewers

### Backend
* Server starts without errors
* All tools return valid outputs
* SSE streaming works end-to-end
* Logs show correct tool calls

### Frontend
* UI receives live stream without freezing
* Tool call displays correctly
* Multi-step conversations appear fluid
* No console errors

### Agent Behavior
* Does not hallucinate medication names
* Handles missing or invalid data gracefully
* Follows instructions strictly
* Maintains context across messages
* Provides language-appropriate responses

## Test Case Examples
### Positive Test Cases

These tests validate expected and correct behavior.

Scenario	→ Expected Result
* Valid medication lookup →	Correct tool call + correct DB result
* Multi-step workflow (Flow 1–3) →	All steps executed with no errors
* System handles Hebrew/English	→ Language-adapted responses
* User updates their question mid-flow	→ Agent adapts without breaking SSE
* UI stays responsive during long answers →	Frontend displays incremental stream

### Negative Test Cases & Edge Cases

Tests to validate robustness and failure handling.

Scenario →	Expected Behavior
* User requests medication not in DB →	Agent apologizes and offers alternatives
* Tool returns empty or null result →	Agent handles gracefully without hallucinations
* Invalid dosage format →	Agent asks for clarification
* User switches languages mid-conversation →	Agent maintains continuity
* SSE disconnect →	Frontend recovers gracefully

## 5. Summary

The evaluation plan ensures that the Pharmacy Agent is:
* Reliable – performs workflows without breaking
* Accurate – uses the correct tools and correct data
* Robust – handles edge cases gracefully
* User-Friendly – streams smoothly with minimal latency
* Aligned with Requirements – meets all project specifications

This evaluation framework can also be reused if the system is extended with more tools or a larger database.

## 2. Multi-Step Workflow Evaluation

Each workflow includes its own success criteria, expected steps, and validation checks.

### Flow 1: Medication Lookup → Availability Check → Reservation

Success Criteria
* Agent identifies user intent correctly.
* Agent calls get_medication_info correctly and reserve_medication.
* Agent summarizes results in Hebrew or English based on user input.
* All steps stream via SSE without interruption.

Validation
* No backend exceptions.
* Correct data is fetched from the DB.
* Response quality is consistent and actionable.

### Flow 2: Asking About Active Prescriptions → Providing User_ID → Asking About The Medication

Success Criteria
* Agent requests required details tool get_user_prescriptions.
* Agent calls the get_medication_info tool correctly.
* Final summary response includes explicit guidance.

Validation
* The full sequence of tool calls appears in the logs.
* The Agent does not hallucinate unavailable medication names.

### Flow 3: Shearching Medication by Active Ingredient → Allergy Check → Providing User_ID 

Success Criteria
* Agent extracts the ingredient name.
* Calls the correct tools.
* Call the tool of allergy check only after providing user_id.

Validation
* The full sequence of tool calls appears in the logs.
* Correct data is fetched from the DB.
* Response quality is consistent and actionable.

## 3. Positive Test Cases

These tests validate expected and correct behavior.

Scenario	→ Expected Result
* Valid medication lookup →	Correct tool call + correct DB result
* Multi-step workflow (Flow 1–3) →	All steps executed with no errors
* System handles Hebrew/English	→ Language-adapted responses
* User updates their question mid-flow	→ Agent adapts without breaking SSE
* UI stays responsive during long answers →	Frontend displays incremental stream

## 4. Negative Test Cases & Edge Cases

Tests to validate robustness and failure handling.

Scenario →	Expected Behavior
* User requests medication not in DB →	Agent apologizes and offers alternatives
* Tool returns empty or null result →	Agent handles gracefully without hallucinations
* Invalid dosage format →	Agent asks for clarification
* User switches languages mid-conversation →	Agent maintains continuity
* SSE disconnect →	Frontend recovers gracefully

## 5. Summary

The evaluation plan ensures that the Pharmacy Agent is:
* Reliable: performs workflows without breaking
* Accurate: uses the correct tools and correct data
* Robust: handles edge cases gracefully
* User-Friendly: streams smoothly with minimal latency
* Aligned with Requirements: meets all project specifications

This evaluation framework can also be reused if the system is extended with more tools or a larger database.
