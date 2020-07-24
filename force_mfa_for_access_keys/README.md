###
It has happened to me where I accidently published my AWS access keys and got picked up by crawlers ending up in account misuse. Enforcing MFA for all everything except reset password and enable MFA seems like a pretty handy setting.

### sample\_iam\_policy.json
A sample policy to deny everything except password reset and MFA activation when MFA is false
### generate\_temporary\_tokens.sh
Collection of bash functions to generate STS tokens and prepare the environment for AWS API use.
