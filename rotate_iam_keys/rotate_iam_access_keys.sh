set -e

function usage() {
  echo "Missing mandatory parameter[s]"
  echo "Usage ${FUNCNAME[0]} account-alias"
  exit 126
}

function unset_key_vars() {
  unset AWS_ACCESS_KEY_ID \
    AWS_SECRET_ACCESS_KEY \
    AWS_SESSION_TOKEN \
    new_access_key \
    new_secret_key
}

function create_update_delete() {
  if [ -z "$1" ]; then
    usage
  fi

  account_name="$1"

  # reset everything
  unset_key_vars

  # get the existing keys
  # improve and do in one pass
  old_access_key=$(awk '/aws_access_key_id/ {print $3}' <(grep -A 3 "${account_name}" "${CREDENTIALS_FILE}"))
  old_secret_key=$(awk '/aws_secret_access_key/ {print $3}' <(grep -A 3 "${account_name}" "${CREDENTIALS_FILE}"))

  # generate new keys
  eval $(jq -r '"new_access_key=\(.AccessKey.AccessKeyId) && new_secret_key=\(.AccessKey.SecretAccessKey)"' <(env AWS_ACCESS_KEY_ID="${old_access_key}" AWS_SECRET_ACCESS_KEY="${old_secret_key}" aws iam create-access-key --user-name "${IAM_USER_NAME}"))

  # replace the keys in the credentials file
  # ugly - learn sed, possibly can be done in one pass
  sed -i '/'"${account_name}"'/!b;n;c\aws_access_key_id = '"${new_access_key}" "${CREDENTIALS_FILE}"
  sed -i '/'"${account_name}"'/!b;n;n;c\aws_secret_access_key = '"${new_secret_key}" "${CREDENTIALS_FILE}"

  # deactivate the old keys
  unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
  env AWS_ACCESS_KEY_ID="${new_access_key}" AWS_SECRET_ACCESS_KEY="${new_secret_key}" aws iam delete-access-key --user-name "${IAM_USER_NAME}" --access-key-id "${old_access_key}"
}

IAM_USER_NAME=""
CREDENTAILS_FILE="$HOME/.aws/credentials"

# get the list of profiles from credentials file
for account in $(awk '/^\[.*\]$/ {print $0}' "${CREDENTAILS_FILE}" | tr -d '[]'); do
  echo "Rotating keys for account ${account}"
  create_update_delete "${account}"
done
