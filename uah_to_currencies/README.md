# NBU Currency Rates Auto-Fetcher

An Odoo module designed to automate the integration and synchronization of official currency exchange rates from the **National Bank of Ukraine (NBU)** API.

## What this module solves?
This module automates daily exchange rate updates for all corporate entities using UAH as their base currency, while also providing on-demand tools to backfill historical exchange rate data for any specific period.

---

## Key Features

* Automated Daily Synchronization
  * Background cron job that runs daily.
  * Fetches exchange rates from the NBU API for all active currencies.
  * Updates all companies with UAH base currency.

* On-Demand History Fetcher - Wizard
  * Adds a **"Fetch Rate History"** button to the Currency form view.
  * Auto-fills default settings (e.g., last 7 days) for a seamless user experience.

* Performance & Architecture Optimized
  * Built using **Batch Processing** techniques — avoids executing heavy database queries inside loops.
  * Safe UPSERT logic prevents duplicated rate entries for the same date and company.

---

## Technical Overview

* **Odoo Version:** 19.0
* **Dependencies:** `base` (Core Odoo ORM)
* **API Integration:** Public API of the National Bank of Ukraine (JSON response parsing)
* **Key Components:**
  * Custom `res.currency` extension
  * Transient Model Wizard for user-driven data retrieval
  * Automated `ir.cron` action
  * Extended Form View with action buttons

