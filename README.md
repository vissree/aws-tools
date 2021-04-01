###

This is a collection of utilities I wrote over time to make the AWS administration tasks easier

- force_mfa_for_access_keys: Enforce MFA for cli access and wrapper functions to generate STS tokens and prepare current shell.
- kinesis: Helper script for Kinesis re-sharding
- recursive_r53_cleanup: Delete orphan records from R53
- cleanup_iam_users: Remove an IAM user along with the login profile, Opsworks user profile (if exists), and sns subscriptions (based on email).
- rotate_iam_keys: Rotate IAM user keys and update local AWS credentials file
- ecs_ami_update: A lambda function that can be triggered on ECS-Optimised AMI update notification to update existing CloudFormation stack with the latest AMI id.
