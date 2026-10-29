# Product brief: ISA allowance ledger

> **Illustrative.** This is a fictional product written for a walkthrough. The figures and rule wording are illustrative, not the actual ISA rules.

Our customers pay money into their ISAs throughout the year, by card, by bank transfer and by moving cash between accounts. At the moment nothing in one place knows how much each customer has already put in, so the checks happen late, in batch, and sometimes after the money has moved. We want a small ledger service that records every subscription as it arrives and answers, at that moment, whether it can be accepted.

The main rule is the annual allowance. A customer can put in up to £20,000 in each tax year across all their ISAs. A subscription that goes over the allowance must not be accepted. Customers often ask how much room they have left, so whenever a subscription comes in the ledger should tell us what remains for the year.

A new rule is coming in for cash. From a future tax year, customers under 65 will be limited to £12,000 of cash subscriptions a year within the overall allowance; stocks and shares are not affected. The ledger needs to handle years before and after the change, because subscriptions for earlier years are still being reconciled. We use the customer's date of birth to work out whether the cash limit applies to them.

Some of our accounts are flexible, and customers with those accounts sometimes take cash out and want to put it back in the same year. We have had questions about whether that should count against their allowance again.

A second team runs a daily breach report. It flags customers who are close to running out of allowance so that the contact centre can warn them before they pay in more. That team will build its report against the ledger's interface rather than its database, so the interface needs to be agreed early and kept stable.

This affects how much of a customer's money we take, and the rules come from outside engineering, so whatever we build has to be traceable from each rule to the tests that prove it, and someone has to sign it off.
