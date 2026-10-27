

**Effective Date:** October 25, 2026  
**Last Updated:** October 25, 2026  

**tir labs** (“**Company**,” “**tir labs**,” “**we**,” “**us**,” or “**our**”) respects your privacy and is committed to transparency regarding how we collect, process, hash, encrypt, store, and use information across the **try tir** ecosystem. 

This Privacy Policy applies to all unified software-as-a-service (SaaS) applications, research platforms, data mining tools, analytics suites, intelligence feeds, news reporting platforms, source code repositories, communities, and all online and offline properties—whether physical or virtual, digital or earthly (collectively, the “**Ecosystem**” or “**Services**”).

By accessing or interacting with the Ecosystem through any vector—including Graphical User Interfaces (GUIs), APIs, Model Context Protocol (MCP) connectors, bulk downloads, RSS feeds, cURL commands, CLIs, WebSockets/gRPC streams, SDKs, webhooks, GraphQL/SQL endpoints, or browser extensions—you acknowledge that you have read and understood this Privacy Policy and consent to the data practices described herein.

---

## 1. CATEGORIES OF INFORMATION WE COLLECT

We collect information directly from you, automatically through your technical interactions with the Ecosystem, and through analytics and identity resolution frameworks for business, operational, security, and monetization purposes.

### 1.1 Information You Provide Directly
* **Account & Contact Identifiers:** Full name, username/handle, email address, and telephone number when you register an account, subscribe to feeds, join communities, contribute to repositories, or contact us.
* **Billing & Payment Information (Billing Only):** Billing physical address and payment method details (such as credit/debit card numbers or bank routing tokens) when you purchase a subscription, API quota, or paid service. *Note: Payment credentials are collected and processed solely for billing purposes via our payment processor, Stripe.*
* **User-Generated Content & Communications:** Code commits, repository issues, community posts, queries, API payloads, support tickets, and correspondence sent to our `@trytir.com` addresses.

### 1.2 Information Collected Automatically & Inferred Metrics
When you interact with the Ecosystem across any of our 12+ access vectors (GUI, API, MCP, CLI, cURL, RSS, SDKs, etc.), we automatically collect and generate:
* **Network & Device Identifiers:** IP address, Autonomous System Number (ASN), ISP, device type, operating system, browser type/version, cURL/CLI client signatures, MAC address, and cryptographic token metadata.
* **Billing Risk Factor Score (Billing Only):** In connection with billing and checkout workflows, we generate or receive a **Risk Factor Score** evaluating transaction legitimacy, velocity, IP-to-billing proximity, and fraud indicators. This score is used strictly for billing security, fraud prevention, and chargeback mitigation.
* **Platform Behavior Analysis:** Detailed telemetry of how you navigate and utilize the Ecosystem, including API endpoint call frequency, MCP tool invocations, query patterns, feature interaction duration, clickstreams, command latency, bulk download logs, and session recordings/diagnostics.
* **Cross-Site Activity & Advertising Metrics:** Information regarding your interactions across different properties within the **try tir** Ecosystem and across third-party websites, including ad impressions, click-through rates, conversion attribution, cookie identifiers, and mobile advertising IDs.
* **Inferred Identity & Probabilistic Profiles:** Inferences drawn from your network signals, behavioral patterns, and identity graphs to link sessions across devices, resolve anonymous or pseudonymous traffic into probabilistic user segments, and tailor platform intelligence and advertising metrics for business purposes.

---

## 2. HOW WE USE YOUR INFORMATION

We process collected information for the following business and commercial purposes:
1. **Ecosystem Provisioning & Execution:** Operating, maintaining, authenticating, and delivering our SaaS platforms, APIs, MCP connectors, CLIs, bulk data pipelines, news reporting, and community repositories.
2. **Billing, Payment Processing & Fraud Prevention:** Processing subscription and usage payments, verifying billing addresses, calculating and evaluating **Risk Factor Scores**, preventing credit card fraud, and enforcing rate limits and account quotas.
3. **Platform Optimization & Behavioral Analytics:** Analyzing platform behavior, debugging code, monitoring infrastructure load, optimizing query performance, and developing new data mining and intelligence features.
4. **Advertising, Monetization & Identity Resolution:** Measuring ad performance, serving contextual and targeted advertisements, resolving cross-site identity signals, and generating advertising metrics for business purposes.
5. **Security, Abuse Detection & Legal Compliance:** Detecting automated scraping, DDoS attacks, Sybil accounts, or violations of our Terms of Service; protecting the safety and rights of **tir labs** and our users; and complying with applicable laws, subpoenas, or legal processes.
6. **Communications:** Sending transactional notices, API deprecation warnings, security alerts, billing receipts, and (where permitted) promotional or ecosystem updates.

---

## 3. INFRASTRUCTURE, STORAGE & THIRD-PARTY ECOSYSTEM STACK

### 3.1 Storage & Security in the Cloudflare Ecosystem
User data, account records, and platform telemetry are stored and secured within our **Cloudflare** infrastructure ecosystem (including Cloudflare edge networks, workers, and encrypted storage databases). We utilize industry-standard cryptographic hashing (for passwords, tokens, and sensitive identifiers) and encryption in transit (TLS 1.3) and at rest to protect your data against unauthorized access, alteration, or destruction.

### 3.2 No External Sale or Third-Party Data Broker Sharing
**At this moment, your stored user account database is not sold or shared with external third-party data brokers—it is maintained exclusively for use by tir labs.** However, to operate our infrastructure, process payments, analyze traffic, and monetize ad-supported properties, we integrate the following specific technology partners into our stack:

| Partner / Provider | Role in the try tir Ecosystem | Data Processed |
| :--- | :--- | :--- |
| **Cloudflare ( & Cloudflare Analytics)** | Edge security, CDN, bot/DDoS mitigation, database hosting, and traffic analytics. | IP addresses, HTTP/cURL headers, TLS fingerprints, performance telemetry, and encrypted/hashed user data stored in our Cloudflare environment. |
| **Stripe** | Payment processing, subscription billing, and fraud/risk scoring. | Name, email, billing address, payment method details, transaction history, and billing **Risk Factor Scores**. |
| **Google AdSense** | Advertising delivery and monetization on ad-supported web/GUI properties. | Cookies, IP addresses, cross-site browsing signals, ad impression/click metrics, and device identifiers for ad personalization and frequency capping. |
| **LiveRamp** | Identity resolution, pseudonymous RampID mapping, and advertising metrics. | Hashed identifiers (such as cryptographically hashed emails), IP addresses, cookie IDs, cross-site activity, and inferred identity signals for audience measurement and business analytics. |

### 3.3 Legal Disclosures & Business Transfers
Notwithstanding the above, we may disclose information if required to do so by law or in the good-faith belief that such action is necessary to: (a) comply with a subpoena, court order, or lawful government request; (b) protect and defend the rights, property, or security of **tir labs**, our Ecosystem, or the public; or (c) facilitate a merger, acquisition, financing, reorganization, or sale of all or a portion of our assets.

---

## 4. COOKIES, PIXELS & TRACKING TECHNOLOGIES

We and our integrated stack partners (Cloudflare, Google AdSense, and LiveRamp) use cookies, local storage, web beacons, pixels, and cryptographic tokens to:
* Keep you authenticated across GUI and developer sessions;
* Distinguish human users from unauthorized bots and scrapers;
* Analyze platform behavior and cross-site activity; and
* Deliver, measure, and optimize advertisements and inferred identity metrics.

**Managing Cookies & Ad Choices:**
* You can configure your browser to reject cookies, though doing so may break authentication across our GUIs and web dashboards.
* You may opt out of Google AdSense personalized advertising by visiting [Google’s Ads Settings](https://myadcenter.google.com/).
* You may opt out of LiveRamp’s identity resolution and targeted advertising ecosystem via the [LiveRamp Opt-Out Portal](https://liveramp.com/opt_out/).
* You can also manage broader industry ad preferences via the Network Advertising Initiative ([NAI Opt-Out](https://optout.networkadvertising.org/)) or the Digital Advertising Alliance ([DAA Opt-Out](https://optout.aboutads.info/)).

---

## 5. PUBLIC RECORDS & RESEARCH DATA IN OUR SAAS PLATFORMS

As a platform for research, data mining, analytics, intelligence, and news reporting, the **try tir** Ecosystem indexes, processes, and surfaces publicly available information, open-source intelligence (OSINT), public repositories, and news data (“**Platform Intelligence Data**”). 

Where Platform Intelligence Data consists of lawfully obtained public records or publicly available information, such data is generally exempt from deletion and opt-out mandates under applicable U.S. state consumer privacy laws (including the New Jersey Data Privacy Act and CCPA). However, individuals who wish to submit an inquiry or request suppression regarding specific personal identifiers appearing within our research tools may contact us at **privacy@trytir.com**.

---

## 6. YOUR PRIVACY RIGHTS (NEW JERSEY, CALIFORNIA & U.S. STATE LAWS)

Depending on your state of residence—including under the **New Jersey Data Privacy Act (NJDPA)**, the **California Consumer Privacy Act (CCPA/CPRA)**, and similar state comprehensive privacy statutes in Virginia, Colorado, Connecticut, Texas, Oregon, and elsewhere—you may have the following legal rights regarding your Personal Data:

1. **Right to Know & Access:** The right to confirm whether we are processing your personal data and to access a copy of the specific pieces and categories of personal data we have collected about you.
2. **Right to Correction:** The right to request that we correct inaccuracies in your personal data, taking into account the nature of the data and the purposes of processing.
3. **Right to Deletion:** The right to request the deletion of personal data you have provided to us or that we have collected about you (subject to statutory exceptions, such as maintaining billing records, detecting security incidents/fraud via Risk Factor Scores, exercising free speech/news reporting, or retaining publicly available information).
4. **Right to Data Portability:** The right to obtain a copy of your personal data in a portable and, to the extent technically feasible, readily usable format.
5. **Right to Opt Out of Targeted Advertising, Cross-Site Profiling & "Sharing":** While we do not sell your stored database records to third-party brokers, the use of Google AdSense and LiveRamp pixels for cross-site behavioral advertising and inferred identity metrics may be classified as "Targeted Advertising" or "Sharing" under laws like the NJDPA and CCPA. You have the right to opt out of such processing at any time.

### 6.1 How to Exercise Your Rights
To exercise any of the rights described above, please submit a verifiable request to us by:
* **Emailing:** **privacy@trytir.com** (with the subject line `"Privacy Rights Request"`)
* **Writing to:** tir labs – Privacy Team, 2 Route 37 W STE F #1084, Toms River, NJ 08753, United States

**Verification Process:** To protect your account and data from unauthorized requests, we will verify your identity by matching the identifiers you provide (such as your registered email address, account handle, or recent billing/API interaction metadata) against our encrypted Cloudflare records before fulfilling your request. You may designate an authorized agent to make a request on your behalf by providing written, signed permission.

**Right to Appeal:** If we decline to take action on your privacy request, we will inform you of our justification within 45 days. Under the New Jersey Data Privacy Act and similar state laws, you may appeal our decision by replying to our determination email or writing to **legal@trytir.com** with the subject line `"Privacy Appeal"`.

### 6.2 Universal Opt-Out Mechanisms (Global Privacy Control)
Where required by applicable law (including New Jersey and California), our web properties recognize valid browser-based Universal Opt-Out Mechanisms, such as the **Global Privacy Control (GPC)** signal, as a valid request to opt out of cross-site targeted advertising for that browser or device.

---

## 7. DATA RETENTION

We retain your personal data only for as long as reasonably necessary to fulfill the purposes for which it was collected, including:
* Maintaining your active **try tir** account, API keys, and repository access;
* Complying with tax, accounting, audit, and financial reporting obligations (for Stripe billing records);
* Preserving security logs, IP telemetry, and Risk Factor Scores to prevent repeat abuse or fraud; and
* Enforcing our Terms of Service and resolving legal disputes.

When personal data is no longer required for these purposes, we securely delete, anonymize, or de-identify it within our Cloudflare storage environment.

---

## 8. CHILDREN’S PRIVACY

The **try tir** Ecosystem is designed for adult developers, researchers, analysts, and enterprises. We do not knowingly allow individuals under the age of eighteen (18) to register for an account, nor do we knowingly collect personal information from children under thirteen (13) in violation of the Children’s Online Privacy Protection Act (COPPA). If you believe a minor has provided personal data to us, please contact **privacy@trytir.com** or **abuse@trytir.com** immediately so we can purge the data and terminate the associated account.

---

## 9. INTERNATIONAL USERS & DATA TRANSFERS

**tir labs** is headquartered in the State of New Jersey, United States. If you access the Ecosystem from outside the United States, please be aware that your information will be transferred to, processed, hashed, and stored in the United States (and across Cloudflare’s global edge network). By using the Ecosystem, you consent to the transfer and processing of your data in the United States in accordance with this Privacy Policy.

---

## 10. CHANGES TO THIS PRIVACY POLICY

We may update this Privacy Policy periodically to reflect changes in our software architecture, data pipelines, advertising stack, or legal obligations. When we make changes, we will revise the “Last Updated” date at the top of this page. If we make material changes to how we process your personal data, we will provide prominent notice through the Ecosystem or via email prior to the change becoming effective.

---

## 11. CONTACT US

If you have any questions, concerns, or requests regarding this Privacy Policy or our data practices, please contact the appropriate **tir labs** department below:

* **Privacy & Data Subject Requests:** `privacy@trytir.com`
* **Legal Notices & Compliance:** `legal@trytir.com`
* **Security Incidents & Platform Abuse:** `abuse@trytir.com`
* **Commercial Partnerships:** `partnerships@trytir.com`

**Mailing Address:**  
**tir labs**  
2 Route 37 W STE F #1084  
Toms River, NJ 08753  
United States