###
This is a collection of utilities I wrote over time to make the AWS administration tasks easier


* force\_mfa\_for\_access\_keys: Enforce MFA for cli access and wrapper functions to generate STS tokens and prepare current shell.
* kinesis: Helper script for Kinesis re-sharding
* recursive_r53_cleanup: Delete orphan records from R53
* cleanup\_iam\_users: Remove an IAM user along with the login profile, Opsworks user profile (if exists), and sns subscriptions (based on email).
* rotate\_iam\_keys: Rotate IAM user keys and update local AWS credentials file
