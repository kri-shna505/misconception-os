# Sprint 4 Rule-Based Diagnosis Test Notes

## Purpose

This document records the controlled backend tests for the first rule-based diagnosis engine in MisconceptionOS.

Sprint 4 validates diagnosis for three seeded DSA misconceptions:

- M1: Binary Search on Unsorted Data
- M2: Missing or Incorrect Recursion Base Case
- M3: Recursive Call Without Reducing Problem Size

The goal is to verify that a saved student attempt can be converted into an evidence-backed diagnosis through the backend API.

## Rule Boundary

An attempt is not a diagnosis.

An attempt stores the student submission:

- final answer
- written reasoning
- source code
- optional speech transcript
- selected language
- response time

A diagnosis is created separately from a saved attempt.

## Backend Flow Tested

```text
POST /api/attempts
↓
attempt saved in attempts table
↓
POST /api/diagnoses/from-attempt/{attempt_id}
↓
evidence extractor runs
↓
rule detector runs
↓
diagnosis row saved
↓
diagnosis evidence rows saved
↓
Swagger returns diagnosis JSON
↓
pgAdmin verifies database rows