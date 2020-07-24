iam_user_name=""

# function to reset existing tokens
function aws-reset() {
    unset AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_ACCESS_KEY_ID
}

function wrap_mfa_usage() {
    echo "Missing required parameters"
    echo "${FUNCNAME[0]} profile account-number-without-hyphen mfacode"
}


# wrapper to generate temporary token for a profile
# specified in the ~/.aws/credentials file
function wrap_mfa() {
    if [ -n "$3" ]; then
        aws-reset
        eval $(aws --profile "$1" sts get-session-token --serial-number arn:aws:iam::${2}:mfa/${iam_user_name} --token-code $3 | jq -r '"export AWS_ACCESS_KEY_ID=\(.Credentials.AccessKeyId) && export AWS_SECRET_ACCESS_KEY=\(.Credentials.SecretAccessKey) && export AWS_SESSION_TOKEN=\(.Credentials.SessionToken)"')
    else
        wrap_mfa_usage
    fi
}

# example function using wrapper
function my-development-account() {
    wrap_mfa "development" "12345678901" "$1"
}
